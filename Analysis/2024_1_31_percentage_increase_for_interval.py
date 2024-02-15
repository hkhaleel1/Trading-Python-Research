from datetime import datetime

import pandas as pd
from pymongo import MongoClient

from Solana.Analysis.Analysis import calculate_max_percentage_increase_from_negative_rsi

client = MongoClient('localhost')
database = client['crypto_data']

currency_pair = "SOL/USD"
start_date = datetime(2024, 2, 3)
end_date = datetime(2024, 2, 4)

intervals = {'1m'}#, '5m', '15m', '30m', '1h', '4h'}
percentage_increases = {1.32}

results = pd.DataFrame(columns=['Interval', 'Percentage', 'Profits'])

for interval in intervals:
    for percentage in percentage_increases:
        profits = \
            calculate_max_percentage_increase_from_negative_rsi(database, interval, currency_pair, start_date, end_date, percentage)
        new_data = pd.DataFrame({'Interval': [interval], 'Percentage': [percentage], 'Profits': [profits]})
        results = pd.concat([results, new_data], ignore_index=True)
        # print(f'Interval:{interval} percentage:{percentage} : num of increases: {profits}')

print(results)
