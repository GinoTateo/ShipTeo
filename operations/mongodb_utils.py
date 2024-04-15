from pymongo import MongoClient


def get_mongodb_client():
    try:
        # Replace 'your_connection_string' with your MongoDB connection string
        uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        return client

    except Exception as e:
        print(f"An error occurred while connecting to MongoDB: {e}")
        return None


def get_orders_from_mongodb(db_name='mydatabase', collection_name='orders'):
    client = get_mongodb_client()
    db = client[db_name]
    collection = db[collection_name]
    orders = list(collection.find())

    # Renaming '_id' field to 'order_id' for each order
    for order in orders:
        order['order_id'] = str(order['_id'])  # Convert ObjectId to string
        del order['_id']

    client.close()
    return orders


def get_inventory_items():
    uri = "mongodb+srv://gjtat901:koxbi2-kijbas-qoQzad@cluster0.abxr6po.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['mydatabase']
    collection = db['inventory']

    items = collection.find({})
    return list(items)