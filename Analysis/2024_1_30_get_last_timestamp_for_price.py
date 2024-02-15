from Solana.Seed.seed_database_binance import seed_database
from pymongo import MongoClient

client = MongoClient('localhost')
database = client['crypto_data']

currency_pair = 'SOL/USD'
skip_seed = False
while True:
    if not skip_seed:
        seed = input("Do you want to seed: ")
        if seed == "y":
            seed_database(database=database, interval="1m", currency_pair="SOL/USD", limit=int((24*360 / 4) * 2), update=True)
            skip_seed = True

    val = input("What price do you want to check: ")

    pipeline = [
        {'$project': {
            '_id': 0,
            'timestamp': '$timestamp',
            'closeString': {'$toString': '$close'}
        }},
        {'$match': {
            'closeString': {'$regex': '^' + str(val)}
        }}
    ]

    historical_price_collection = database[f'historical_price_1m_{currency_pair}']
    hp_data = list(historical_price_collection.aggregate(pipeline))
    if not hp_data:
        print(f'No data found for {val}')
    else:
        max_entry = max(hp_data, key=lambda x: x['timestamp'])
        print(f"{max_entry['closeString']} @ {max_entry['timestamp']}")
