import pandas as pd
import mplfinance as mpf
from matplotlib import pyplot as plt
import plotly.graph_objects as go


def plot_trend(database=None, interval='1d', currency_pair='SOL/USD', start_date=None, end_date=None, threshold_percentage=float(5)):
    if database is None:
        raise ValueError("Database is required.")
    # Retrieve data between two dates
    query = {"timestamp": {"$gte": start_date, "$lte": end_date}} \
        if start_date is not None and end_date is not None else {}

    historical_price_collection = database[f'historical_price_{interval}_{currency_pair}']

    hp_data = list(historical_price_collection.find(query))  # Retrieve all documents from the collection

    print(len(hp_data))
    # Create a DataFrame from the retrieved data
    df = pd.DataFrame(hp_data)

    # Convert the timestamp to datetime and set it as the index
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)

    opens = df['open']
    closes = df['close']
    # Calculate the total number of data points
    total_points = len(opens)

    # Check for lower highs and lower lows in at least 70% of the data points
    bullish = 0
    bearish = 0
    for i in range(total_points - 1):
        body = closes.iloc[i] - opens.iloc[i]
        if body < 0:
            bearish += abs(body)
        else:
            bullish += abs(body)

    print(f'Bullish: {bullish}')
    print(f'Bearish: {bearish}')
    trend = None
    if abs(bullish - bearish) / (bullish + bearish) < threshold_percentage / 100:
        trend = "no"
    elif bullish > bearish:
        trend = "an upward"
    elif bearish > bullish:
        trend = "a downward"

    print(f"There is {trend} trend")
    # Plot the candlestick chart
    mpf.plot(df, type='candle', style='yahoo', title=f'Candlestick Chart, {trend} trend', ylabel='Price')


def plot_rsi_data(database=None, interval='1d', currency_pair='SOL/USD', start_date=None, end_date=None):
    if database is None:
        raise ValueError("Database is required.")
    query = {"timestamp": {"$gte": start_date, "$lte": end_date}} \
        if start_date is not None and end_date is not None else {}

    rsi_collection = database[f'rsi_data_{interval}_{currency_pair}']

    rsi_data = list(rsi_collection.find(query))  # Retrieve all documents from the collection

    print(len(rsi_data))
    # Create a DataFrame from the retrieved data
    df = pd.DataFrame(rsi_data)
    # Plot the RSI data
    plt.figure(figsize=(10, 6))
    plt.plot(df['timestamp'], df['rsi'], label='RSI')

    # Add horizontal lines at 30 and 70
    plt.axhline(y=30, color='r', linestyle='--', label='Oversold (30)')
    plt.axhline(y=70, color='g', linestyle='--', label='Overbought (70)')

    # Add labels and title
    plt.xlabel('Timestamp')
    plt.ylabel('RSI')
    plt.title('Relative Strength Index (RSI)')
    plt.legend()
    plt.show()


def calculate_max_percentage_increase_from_negative_rsi(database=None, interval='1d', currency_pair="SOL/USD", start_date=None, end_date=None,
                                                        percentage_threshold=1.5):
    df = get_rsi_and_historical_data_for_interval(database, currency_pair, interval, start_date, end_date)
    buy_index = None
    sell_index = None
    max_increase = 0.0
    selected_data = pd.DataFrame(
        columns=['buy-timestamp', 'rsi', 'buy-open', 'buy-close', 'sell-timestamp', 'sell-open', 'sell-close',
                 'increase-open-open'])

    selected_data = selected_data.astype({'sell-timestamp': 'datetime64[ns]'})
    order_count = 0

    for i in range(len(df) - 1):
        # for initial buy if no buy index set rsi is below 30 then set it to buy index
        if buy_index is None and df['rsi'][i] < 30:
            buy_index = i
            # Add the timestamp, RSI, open, and close price to a DataFrame

            selected_data.loc[order_count] = {
                'buy-timestamp': df['timestamp'][buy_index],
                'rsi': df['rsi'][buy_index],
                'buy-open': df['open'][buy_index],
                'buy-close': df['close'][buy_index]
            }
        # For all new buy orders, if we get to the next below 30 then only reset if max increase is above 1.5%
        elif buy_index is not None and df['rsi'][i] < 30 and \
                selected_data.at[order_count, 'increase-open-open'] > percentage_threshold:
            # set new buy index
            buy_index = i
            order_count += 1
            max_increase = 0
            # Add the timestamp, RSI, open, and close price to a DataFrame
            selected_data.loc[order_count] = {
                'buy-timestamp': df['timestamp'][buy_index],
                'rsi': df['rsi'][buy_index],
                'buy-open': df['open'][buy_index],
                'buy-close': df['close'][buy_index]
            }
        # loop through until rsi is greater than 30 to find the max increase
        elif buy_index is not None and df['rsi'][i] >= 30:
            sell_index = i
            percentage_increase = (df['open'][sell_index] - df['open'][buy_index]) / df['open'][buy_index] * 100
            if percentage_increase >= percentage_threshold and percentage_increase > max_increase:
                max_increase = percentage_increase
                selected_data.at[order_count, 'sell-timestamp'] = df['timestamp'][sell_index]
                selected_data.at[order_count, 'sell-open'] = df['open'][sell_index]
                selected_data.at[order_count, 'sell-close'] = df['close'][sell_index]
                selected_data.at[order_count, 'increase-open-open'] = max_increase

    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_rows', None)
    print(selected_data)
    return order_count


def plot_xh_rsi(database=None, currency_pair='SOL/USD', start_date=None, end_date=None):
    if database is None:
        raise ValueError("Database is required.")
    query = {"timestamp": {"$gte": start_date, "$lte": end_date}} \
        if start_date is not None and end_date is not None else {}
    interval_line_width = {'1m': 0.5, '5m': 0.7, '15m': 0.9, '30m': 1.1, '1h': 1.3, '4h': 1.5}

    # Create an empty list to store the plotted lines
    plotted_lines = []
    fig = go.Figure()

    for interval, line_width in interval_line_width.items():
        rsi_collection = database[f'rsi_data_{interval}_{currency_pair}']
        rsi_data = list(rsi_collection.find(query))  # Retrieve all documents from the collection
        # Create a DataFrame from the retrieved data
        rsi_df = pd.DataFrame(rsi_data)
        # Plot the RSI data for each interval and store the line object in plotted_lines
        fig.add_trace(go.Scatter(x=rsi_df['timestamp'], y=rsi_df['rsi'], mode='lines', name=interval,
                                 line=dict(width=line_width)))
        # line, = plt.plot(rsi_df['timestamp'], rsi_df['rsi'], label=interval, linewidth=line_width)
        # plotted_lines.append(line)

    # plt.axhline(y=30, color='r', linestyle='--', label='RSI 30')
    # plt.axhline(y=50, color='b', linestyle='--', label='RSI 50')
    # plt.axhline(y=70, color='g', linestyle='--', label='RSI 70')
    # # Set labels and title
    # plt.xlabel('Timestamp')
    # plt.ylabel('RSI Value')
    # plt.title('RSI Data for Different Time Intervals')
    # plt.legend(handles=plotted_lines, loc='best')

    # # Show the plot
    # plt.show()
    # Add horizontal lines at y-values 30, 50, and 70
    fig.add_shape(type="line", x0=rsi_df['timestamp'].min(), x1=rsi_df['timestamp'].max(), y0=30, y1=30,
                  line=dict(color="red", width=1, dash="dash"), xref='x', yref='y')
    fig.add_shape(type="line", x0=rsi_df['timestamp'].min(), x1=rsi_df['timestamp'].max(), y0=50, y1=50,
                  line=dict(color="blue", width=1, dash="dash"), xref='x', yref='y')
    fig.add_shape(type="line", x0=rsi_df['timestamp'].min(), x1=rsi_df['timestamp'].max(), y0=70, y1=70,
                  line=dict(color="green", width=1, dash="dash"), xref='x', yref='y')
    # Set layout and options for the interactive graph
    fig.update_layout(
        title='RSI Data for Different Time Intervals',
        xaxis_title='Timestamp',
        yaxis_title='RSI Value',
        updatemenus=[dict(
            active=0,
            buttons=list([
                dict(label='Show All',
                     method='update',
                     args=[{'visible': [True] * len(interval_line_width)}]),
                dict(label='Hide All',
                     method='update',
                     args=[{'visible': [False] * len(interval_line_width)}])
            ]),
        )]
    )

    # Show the interactive plot
    fig.show()


def get_rsi_and_historical_data_for_interval(database=None, currency_pair='SOL/USD', interval="1m", start_date=None, end_date=None):
    if database is None:
        raise ValueError("Database is required.")
    query = {"timestamp": {"$gte": start_date, "$lte": end_date}} \
        if start_date is not None and end_date is not None else {}

    rsi_collection = database[f'rsi_data_{interval}_{currency_pair}']
    rsi_data = list(rsi_collection.find(query))
    rsi_df = pd.DataFrame(rsi_data)

    historical_price_collection = database[f'historical_price_{interval}_{currency_pair}']
    price_data = list(historical_price_collection.find(query))
    price_df = pd.DataFrame(price_data)
    if not rsi_df.empty and not price_df.empty:
        return pd.merge(rsi_df, price_df, on='timestamp')
    else:
        print("No data found")
        exit()
