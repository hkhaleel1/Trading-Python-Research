import json
import ta
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from websocket import create_connection
from matplotlib.animation import FuncAnimation


def calculate_rsi(data, period=14):
    return ta.momentum.rsi(data, window=period)


def get_initial_data(max_interval, interval=1, pair="SOL/USD"):
    number_of_candles = max(max_interval, interval)
    start_time = datetime.now() - timedelta(hours=0, minutes=(40 * number_of_candles))
    start_timestamp = int(start_time.timestamp())
    resp = requests.get(
        f'https://api.kraken.com/0/public/OHLC?pair={pair}&interval={interval}&since={start_timestamp}')
    resp_json = resp.json()
    result = resp_json['result']
    currency_pair_data = result[pair]
    df = pd.DataFrame(currency_pair_data,
                      columns=['timestamp', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
    df['timestamp'] = [datetime.fromtimestamp(x) for x in df['timestamp']]
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['rsi'] = calculate_rsi(df['close'], period=14)
    return df


def update_plot(frame, interval, currency_pair, line, ax, ws, last_message, display_lim, multi_graph=False):
    curr_data = data[currency_pair][intervals.index(interval)]
    new_data = json.loads(ws.recv())
    print("WebSocket -> Client1: %s" % new_data)
    if isinstance(new_data, list) and new_data[2] == f'ohlc-{interval}':
        # Update the timestamp of the last message received
        new_timestamp = datetime.utcfromtimestamp(float(new_data[1][0])).replace(microsecond=0)
        last_message.set_text(f"{currency_pair} Channel: {new_data[2]}: Last Message Received: {new_timestamp} @ ${new_data[1][5]}")
        new_timestamp = new_timestamp.replace(second=0)
        new_axis_display = new_timestamp - timedelta(hours=display_lim)
        global last_timestamp
        latest_timestamp = last_timestamp[currency_pair]
        if new_timestamp > latest_timestamp:
            latest_timestamp = new_timestamp
        ax.set_xlim(new_axis_display, latest_timestamp + timedelta(minutes=1))
        rounded_timestamp = np.datetime64(new_timestamp - timedelta(minutes=(new_timestamp.minute % interval)))
        new_close_price = float(new_data[1][5])
        if rounded_timestamp in curr_data['timestamp'].values:
            curr_data.loc[curr_data['timestamp'] == rounded_timestamp, 'close'] = new_close_price
        else:
            new_row = pd.DataFrame({'timestamp': [rounded_timestamp], 'close': [new_close_price]})
            curr_data = pd.concat([curr_data, new_row], ignore_index=True)
        curr_data['rsi'] = calculate_rsi(curr_data['close'], period=14)
        data[currency_pair][intervals.index(interval)] = curr_data

        line.set_data(curr_data['timestamp'], curr_data['rsi'])
        last_rsi = curr_data['rsi'][len(curr_data) - 1]
        if multi_graph:
            line.set_label(f'RSI {interval} {currency_pair} @ {round(last_rsi, 2)}')
        else:
            line.set_label(f'RSI {interval} @ {round(last_rsi, 2)}')
        if last_rsi <= 30 or last_rsi >= 70:
            line.set_linewidth(2)
        else:
            line.set_linewidth(1)

        legend_ = ax.legend(loc="lower left")  # Add a legend to the plot
        global legend_lines
        legend_lines[currency_pair] = legend_.get_lines();
        for line_ in legend_lines[currency_pair]:
            line_.set_picker(True)
            line_.set_pickradius(10)

        ax.relim()
        ax.autoscale_view()
        return line, last_message_time


def create_ws(domain, interval, pair):
    ws = create_connection(domain)
    api_data = f'{{"event":"subscribe", "subscription":{{"name":"ohlc", "interval": {interval}}}, "pair":["{pair}"]}}'
    ws.send(api_data)
    return ws


def set_xaxis_display(ax, interval, display_lim):
    if interval == 1 or interval == 5:
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=1, byminute=range(0, 60, 5)))
    elif interval == 15 or interval == 30 or interval == 60 or interval == 240 or interval == 1440:#:
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=1, byminute=range(0, 60, 15)))
    # elif interval == 240 or interval == 1440:
    #     ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=1, byminute=range(0, 60, 30)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    axis_display_limit = datetime.now() - timedelta(hours=display_lim)
    ax.set_xlim(axis_display_limit, datetime.now())


def on_pick(event, figure, lines, currency_pair):
    legend = event.artist
    is_visible = legend.get_visible()
    print(f'Setting {legend}: {not is_visible}')
    lines[legend_lines[currency_pair].index(legend)].set_visible(not is_visible)
    figure.canvas.draw()


def on_pick_multi(event, figure, lines, currency_pairs):
    legend = event.artist
    is_visible = legend.get_visible()
    print(f'Setting {legend}: {not is_visible}')
    for currency_pair in currency_pairs:
        if currency_pair in str(legend):
            # Convert the lines to strings and split at the '@' symbol
            line_strings = [str(line).split('@')[0] for line in legend_lines[currency_pair] if currency_pair in str(line)]
            legend_string = str(legend).split('@')[0]

            # Find the index of the matching line
            index = line_strings.index(legend_string)
            lines[currency_pair][index].set_visible(not is_visible)
    figure.canvas.draw()


def create_plot_for_pair(figure, ax, intervals, currency_pair):
    data[currency_pair] = [get_initial_data(max(intervals), interval, currency_pair) for interval in intervals]
    ws_connections[currency_pair] = [create_ws(api_domain_public, interval, currency_pair) for interval in intervals]

    set_xaxis_display(ax, max(intervals), display_limit)
    ax.set_xlabel('Time')
    ax.set_ylabel(f'RSI {currency_pair}')
    ax.axhline(y=30, linestyle='--', color='g')
    ax.axhline(y=70, linestyle='--', color='r')
    ax.axhline(y=50, linestyle='--', color='b')
    plt.xticks(rotation=25)

    for df in data[currency_pair]:
        if last_timestamp.get(currency_pair) is None:
            last_timestamp[currency_pair] = df['timestamp'].max()
        else:
            last_timestamp[currency_pair] = max(last_timestamp[currency_pair], df['timestamp'].max())
    last_message_time[currency_pair] = ax.text(0.02, 1.1, '', transform=ax.transAxes)
    lines = [ax.plot([], [], label=f'RSI {interval}')[0] for interval in intervals]
    plt.connect('pick_event', lambda event: on_pick(event, figure, lines, currency_pair))

    tasks = []
    for i in range(len(intervals)):
        animation = FuncAnimation(figure, update_plot, fargs=(
            intervals[i], currency_pair, lines[i], ax, ws_connections[currency_pair][i],
            last_message_time[currency_pair], display_limit),
                                  interval=200)
        tasks.append(animation)

    return tasks


def create_plot_for_multi_pair(figure, ax, intervals, currency_pairs):
    y_label = 'RSI '
    last_message_height = 1.1
    lines = {}
    for currency_pair in currency_pairs:
        data[currency_pair] = [get_initial_data(max(intervals), interval, currency_pair) for interval in intervals]
        ws_connections[currency_pair] = [create_ws(api_domain_public, interval, currency_pair) for interval in intervals]
        y_label = f'{y_label} {currency_pair}'
        for df in data[currency_pair]:
            if last_timestamp.get(currency_pair) is None:
                last_timestamp[currency_pair] = df['timestamp'].max()
            else:
                last_timestamp[currency_pair] = max(last_timestamp[currency_pair], df['timestamp'].max())

        last_message_time[currency_pair] = ax.text(0.02, last_message_height, '', transform=ax.transAxes)
        last_message_height = last_message_height + 0.2
        lines[currency_pair] = [ax.plot([], [], label=f'RSI {interval}')[0] for interval in intervals]
    plt.connect('pick_event', lambda event: on_pick_multi(event, figure, lines, currency_pairs))

    set_xaxis_display(ax, max(intervals), display_limit)
    ax.set_xlabel('Time')
    ax.set_ylabel(y_label)
    ax.axhline(y=30, linestyle='--', color='g')
    ax.axhline(y=70, linestyle='--', color='r')
    ax.axhline(y=50, linestyle='--', color='b')
    # plt.connect('pick_event', lambda event: on_pick_multi(event, figure, lines, currency_pairs))

    tasks = []
    for i in range(len(intervals)):
        for currency_pair in currency_pairs:
            animation = FuncAnimation(figure, update_plot, fargs=(
                intervals[i], currency_pair, lines[currency_pair][i], ax, ws_connections[currency_pair][i],
                last_message_time[currency_pair], display_limit, True),
                                      interval=50)
            tasks.append(animation)

    return tasks


api_domain_public = "wss://ws.kraken.com/"
intervals = [1, 5, 15, 30, 60, 240, 1440]
data = {}
ws_connections = {}
legend_lines = {}
last_timestamp = {}
last_message_time = {}
display_limit = 3

fig, axis = plt.subplots(figsize=(10, 10), nrows=2, ncols=1)
tasks_for_all_pairs = [create_plot_for_pair(fig, axis[0], intervals, "SOL/USD"),
                       create_plot_for_pair(fig, axis[1], intervals, "BTC/USD")]
#
# fig, axis = plt.subplots(figsize=(10, 10))
# tasks_for_all_pairs = [create_plot_for_multi_pair(fig, axis, intervals, currency_pairs=["SOL/USD", "BTC/USD"])]

plt.subplots_adjust(left=0.1,
                    bottom=0.1,
                    right=0.9,
                    top=0.9,
                    wspace=0.4,
                    hspace=0.4)

# Execute tasks in parallel
with ThreadPoolExecutor() as executor:
    executor.map(lambda task: task(), tasks_for_all_pairs)

plt.show()
