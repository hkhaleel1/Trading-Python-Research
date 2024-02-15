import numpy as np
from pymongo import MongoClient
from datetime import datetime
import pandas as pd

from Solana.Analysis.Analysis import get_rsi_and_historical_data_for_interval

client = MongoClient('localhost')
database = client['crypto_data']

currency_pair = 'SOL/USD'
interval = '1m'
percentage_threshold = 1.32
minutes_between_buy = 10
start_date = datetime(2024, 2, 6)
end_date = datetime(2024, 2, 7)
split = 2

bought_matrix = np.full(split, False)
order_count = 0
orders = pd.DataFrame(columns=['rsi', 'buy-timestamp', 'buy-open', 'buy-close',
                               'sell-timestamp', 'sell-open', 'sell-close', 'P/L %'])

df = get_rsi_and_historical_data_for_interval(database, currency_pair, interval, start_date, end_date)
for i in range(len(df) - 1):
    if df['rsi'][i] < 30:
        for j in range(split):
            if bought_matrix[j]:
                continue

            order_pos = order_count + j
            if order_pos <= len(orders) - 1 and df['timestamp'][i] - orders.at[order_pos - 1, 'buy-timestamp'] \
                    <= pd.Timedelta(minutes=minutes_between_buy):
                continue
            bought_matrix[j] = True
            orders.loc[order_pos] = {
                'buy-timestamp': df['timestamp'][i],
                'rsi': df['rsi'][i],
                'buy-open': df['open'][i],
                'buy-close': df['close'][i]
            }
            break
    else:
        for j in range(split):
            if not bought_matrix[j]:
                continue
            if order_count <= len(orders) - 1:
                # new order not created yet
                order_pos = order_count
            else:
                order_pos = order_count + j
            if order_pos in orders.index:
                percentage_increase = (df['open'][i] - orders.loc[order_pos]['buy-open']) / orders.loc[order_pos][
                    'buy-open'] * 100
                if percentage_increase >= percentage_threshold: # or percentage_increase <= -1:
                    bought_matrix[j] = False
                    orders.at[order_pos, 'sell-timestamp'] = df['timestamp'][i]
                    orders.at[order_pos, 'sell-open'] = df['open'][i]
                    orders.at[order_pos, 'sell-close'] = df['close'][i]
                    orders.at[order_pos, 'P/L %'] = percentage_increase
                    order_count += 1
                    break
            # else:
            #     print("No buy in!")

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
print(orders)
print(order_count)

val = 300
for i in range(len(orders) - 1):
    pi = orders.at[i, 'P/L %']
    val = val * (100 + pi)/100
    print(f'£{val}')
