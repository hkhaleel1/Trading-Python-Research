from datetime import datetime

from Solana.Analysis.Analysis import plot_xh_rsi
from seed_database_binance import seed_database, seed_last_x_hours
from pymongo import MongoClient

client = MongoClient('localhost')
database = client['crypto_data']

seed_database(database=database, interval="1m", interval_minutes=1, currency_pair="SOL/USD", limit=int(5*24*60), update=True)

# seed_last_x_hours(database=database, currency_pair="SOL/USD", hours=48, update=True)

start_date = datetime(2024, 1, 25, 13)
end_date = datetime(2024, 1, 26, 17)
#
# plot_xh_rsi(database, start_date, end_date)
