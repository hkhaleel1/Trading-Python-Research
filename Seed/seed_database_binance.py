import math
from datetime import datetime, timedelta

import ccxt
import pandas as pd
import ta
import requests
from pymongo.errors import BulkWriteError


def seed_last_x_hours(database=None, currency_pair=None, hours=24, update=False):
    intervals = {
        '1m': (int(hours * 60), 1),
        '5m': (int((hours * 60 / 5) * 1.2), 5),
        '15m': (int((hours * 60 / 15) * 1.4), 15),
        '30m': (int((hours * 60 / 30) * 1.6), 30),
        '1h': (int(hours * 1.8), 60),
        '4h': (int((hours / 4) * 2), 240)
    }

    for interval, (limit, interval_minutes) in intervals.items():
        seed_database(database, interval, interval_minutes, currency_pair, limit, update)
        print("SEED COMPLETE FOR: " + interval)


def seed_database(database=None, interval="1h", interval_minutes=60, currency_pair=None, limit=1000, update=False):
    if database is None:
        raise ValueError("Database is required.")
    if interval != "1h" and interval_minutes == 60:
        raise ValueError("interval_minutes is required.")
    if interval_minutes != 60 and interval == "1h":
        raise ValueError("interval is required.")

    # Connect to MongoDB
    historical_price_collection = database[f'historical_price_{interval}_{currency_pair}']
    rsi_collection = database[f'rsi_data_{interval}_{currency_pair}']

    historical_price_collection.create_index([('timestamp', 1)], unique=True, sparse=True)
    rsi_collection.create_index([('timestamp', 1)], unique=True, sparse=True)
    # Initialize the ccxt exchange object for fetching historical price data
    exchange = ccxt.binance()
    if currency_pair is None:
        raise ValueError("Currency pair is required.")

    limit_threshold = 200 if interval == '4h' else 1000
    no_of_fetches = math.ceil(limit / limit_threshold) if limit > 1000 else 1
    for i in range(no_of_fetches):
        if no_of_fetches == 1:
            ohlcv = exchange.fetch_ohlcv(currency_pair, interval, limit=limit + 14)
        else:
            start_time = datetime.now() - timedelta(hours=0, minutes=((i + 1) * interval_minutes * limit_threshold) + 14)
            start_timestamp = int(start_time.timestamp() * 1000)
            # Fetch historical price data
            ohlcv = exchange.fetch_ohlcv(currency_pair, interval, limit=limit, since=start_timestamp)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # Calculate RSI using the ta library
        df['rsi'] = ta.momentum.rsi(df['close'], window=14)

        # Convert dataframe to dictionary for insertion into MongoDB
        historical_price_data = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].to_dict(orient='records')[14:]
        rsi_data = df[['timestamp', 'rsi']].to_dict(orient='records')[14:]

        # Insert historical price data into MongoDB
        if historical_price_data:
            if update:
                timestamps = [entry["timestamp"] for entry in historical_price_data]
                # Calculate the maximum and minimum timestamps
                max_timestamp = max(timestamps)
                min_timestamp = min(timestamps)
                historical_price_collection.delete_many(
                    {"timestamp": {"$gte": min_timestamp, "$lte": max_timestamp}})  # Delete all existing data
            try:
                historical_price_collection.insert_many(historical_price_data, ordered=False)
            except BulkWriteError as e:
                print_duplicate_keys(e, "historical price")

        # Insert RSI data into MongoDB
        if rsi_data:
            if update:
                timestamps = [entry["timestamp"] for entry in rsi_data if not math.isnan(entry.get("rsi"))]
                # Calculate the maximum and minimum timestamps
                if timestamps:
                    max_timestamp = max(timestamps)
                    min_timestamp = min(timestamps)
                    rsi_collection.delete_many(
                        {"timestamp": {"$gte": min_timestamp, "$lte": max_timestamp}})  # Delete all existing data
            try:
                rsi_collection.insert_many(rsi_data, ordered=False)
            except BulkWriteError as e:
                print_duplicate_keys(e, "rsi")


def print_duplicate_keys(e, collection):
    for error in e.details.get('writeErrors', []):
        if error.get('code') == 11000:
            # Print the formatted error message
            print(f"Duplicate {collection} key occurred:", format_duplicate_key_error(error.get('errmsg')))


def format_duplicate_key_error(error_message):
    # Extract the timestamp from the error message
    timestamp_start = error_message.find("new Date(") + len("new Date(")
    timestamp_end = error_message.find(")", timestamp_start)
    timestamp = int(error_message[timestamp_start:timestamp_end])

    # Convert the timestamp to a human-readable date format
    formatted_date = datetime.utcfromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')

    # Replace the original timestamp with the formatted date in the error message
    return error_message.replace(f"new Date({timestamp})", formatted_date)
