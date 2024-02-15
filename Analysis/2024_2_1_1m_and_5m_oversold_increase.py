from pymongo import MongoClient
from datetime import datetime
import pandas as pd

client = MongoClient('localhost')
database = client['crypto_data']

currency_pair = 'SOL/USD'
intervals = ['1m', '5m']
start_date = datetime(2024, 2, 1)
end_date = datetime(2024, 2, 3)
percentage_threshold = 1.5

query = {"timestamp": {"$gte": start_date, "$lte": end_date}} \
    if start_date is not None and end_date is not None else {}

result = pd.DataFrame()
for interval in intervals:
    rsi_collection = database[f'rsi_data_{interval}_{currency_pair}']
    rsi_data = list(rsi_collection.find(query))
    rsi_df = pd.DataFrame(rsi_data)

    historical_price_collection = database[f'historical_price_{interval}_{currency_pair}']
    price_data = list(historical_price_collection.find(query))
    price_df = pd.DataFrame(price_data)

    # data[interval] = pd.DataFrame(pd.merge(rsi_df, price_df, on='timestamp'))
    if not rsi_df.empty and not price_df.empty:
        merged_df = pd.merge(rsi_df, price_df, on='timestamp', how='outer', suffixes=('_rsi', '_price'))
        merged_df.columns = [f'{col}_{interval}' if col != 'timestamp' else col for col in merged_df.columns]

        if result.empty:
            result = merged_df
        else:
            result = pd.merge(result, merged_df, on='timestamp', how='outer')

if not result.empty:
    result = result.sort_values('timestamp').reset_index(drop=True)

# Continue with the rest of your processing
selected_data = pd.DataFrame(columns=['timestamp_5m', 'rsi_5m', 'buy-timestamp', 'rsi_1m', 'buy-open', 'buy-close',
                                      'sell-timestamp', 'sell-open', 'sell-close', 'increase-open-open'])

buy_index = None
max_increase = 0.0
order_count = 0

#
# def is_valid_buy_index(result, index):
#     rsi_5m = result['rsi_5m'][index]
#     if rsi_5m < 30:
#         for index_1m in range(index, index + 5):
#             if result['rsi_1m'][index_1m] < 30:
#                 return index_1m
#     return None

for i in range(len(result) - 6):
    if buy_index is None:
        rsi_5m = result['rsi_5m'][i]
        if rsi_5m < 30:
            rsi_1m_30_index = None
            for j in range(i, i + 5):
                if result['rsi_1m'][j] < 30:
                    rsi_1m_30_index = j
                    break

            if rsi_1m_30_index is None:
                continue
            else:
                rsi_1m = result['rsi_1m'][rsi_1m_30_index]
                next_index = rsi_1m_30_index + 1
                next_rsi_1m = result['rsi_1m'][next_index]
                while next_rsi_1m < rsi_1m:
                    rsi_1m = next_rsi_1m
                    next_index += 1
                    next_rsi_1m = result['rsi_1m'][next_index]

                buy_index = next_index
                selected_data.loc[order_count] = {
                    'timestamp_5m': result['timestamp'][i],
                    'rsi_5m': result['rsi_5m'][i],
                    'buy-timestamp': result['timestamp'][buy_index],
                    'rsi_1m': result['rsi_1m'][buy_index],
                    'buy-open': result['open_1m'][buy_index],
                    'buy-close': result['close_1m'][buy_index]
                }
    elif buy_index is not None:
        if i < buy_index:
            continue
        rsi_5m = result['rsi_5m'][i]
        if rsi_5m < 30:
            rsi_1m_30_index = None
            for j in range(i, i + 5):
                if result['rsi_1m'][j] < 30:
                    rsi_1m_30_index = j
                    break

            if rsi_1m_30_index is None:
                continue
            else:
                rsi_1m = result['rsi_1m'][rsi_1m_30_index]
                next_index = rsi_1m_30_index + 1
                next_rsi_1m = result['rsi_1m'][next_index]
                while next_rsi_1m < rsi_1m:
                    rsi_1m = next_rsi_1m
                    next_index += 1
                    next_rsi_1m = result['rsi_1m'][next_index]

                if selected_data.at[order_count, 'increase-open-open'] > percentage_threshold:
                    # reset counts
                    buy_index = next_index
                    order_count += 1
                    max_increase = 0
                    selected_data.loc[order_count] = {
                        'timestamp_5m': result['timestamp'][i],
                        'rsi_5m': result['rsi_5m'][i],
                        'buy-timestamp': result['timestamp'][buy_index],
                        'rsi_1m': result['rsi_1m'][buy_index],
                        'buy-open': result['open_1m'][buy_index],
                        'buy-close': result['close_1m'][buy_index]
                    }
        else:
            percentage_increase = (result[f'open_1m'][i] - result[f'open_1m'][buy_index]) \
                                  / result[f'open_1m'][buy_index] * 100
            if percentage_increase >= percentage_threshold and percentage_increase > max_increase:
                max_increase = percentage_increase
                selected_data.at[order_count, 'sell-timestamp'] = result['timestamp'][i]
                selected_data.at[order_count, 'sell-open'] = result[f'open_1m'][i]
                selected_data.at[order_count, 'sell-close'] = result[f'close_1m'][i]
                selected_data.at[order_count, 'increase-open-open'] = max_increase

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
print(selected_data)
