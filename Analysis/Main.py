from datetime import datetime
from pymongo import MongoClient

from Solana.Analysis.Analysis import calculate_max_percentage_increase_from_negative_rsi, plot_xh_rsi

client = MongoClient('localhost')
database = client['crypto_data']

interval = "1m"
start_date = datetime(2024, 1, 25, 13)
end_date = datetime(2024, 1, 26, 16)

# plot_xh_rsi(database, start_date, end_date)
#
calculate_max_percentage_increase_from_negative_rsi(database, interval, percentage_threshold=4.5)
# plot_rsi_data(database, interval)
# plot_trend(database, interval, threshold_percentage=4.5)

# calculate_max_percentage_increase_from_negative_rsi(database, interval, start_date, end_date, 2.5)
# plot_rsi_data(database, interval, start_date, end_date)
# plot_trend(database, interval, start_date, end_date, threshold_percentage=4.5)

# plot_trend(database, "4h", datetime(2023, 11, 10), datetime(2024, 1, 23), 4.5)
# plot_trend(database, "4h", datetime(2023, 12, 21), datetime(2024, 1, 23), 4.5)
# plot_trend(database, "4h", datetime(2023, 12, 25), datetime(2024, 1, 23), 4.5)
# plot_trend(database, "1d", threshold_percentage=4.5)
# plot_trend(database, "1d", datetime(2023, 11, 10), datetime(2024, 1, 23), 4.5)
# plot_trend(database, "1d", datetime(2023, 12, 21), datetime(2024, 1, 23), 4.5)
# plot_trend(database, "1d", datetime(2023, 12, 25), datetime(2024, 1, 23), 4.5)
# plot_trend(database, "30m", datetime(2024, 1, 3, 13), datetime(2024, 1, 5, 23), 4.5)
# plot_trend(database, "30m", datetime(2024, 1, 3, 1), datetime(2024, 1, 4, 22), 4.5)
# plot_trend(database, "30m", datetime(2024, 1, 6, 18), datetime(2024, 1, 8, 15), 4.5)
# plot_trend(database, "30m", datetime(2024, 1, 15, 10), datetime(2024, 1, 18, 14), 4.5)
# plot_trend(database, "30m", datetime(2024, 1, 18, 10), datetime(2024, 1, 23, 14), 4.5)

