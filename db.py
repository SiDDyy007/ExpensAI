import redis
import json

# Connect to Redis
import os

redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = int(os.getenv('REDIS_PORT', 6379))

client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

# Example JSON data
data = {
    "charge_id": "1",
    "charge_name": "Amazon Purchase",
    "date": "2024-12-15",
    "amount": 100.5,
    "category": "Shopping",
    "vector": [0.12, 0.45, 0.78],  # Placeholder for embeddings
    "anomaly_flag": False,
    "metadata": {}
}


# data = {
#   "model": "Jigger",
#   "brand": "Velorim",
#   "price": 270,
#   "type": "Kids bikes",
#   "specs": {
#     "material": "aluminium",
#     "weight": "10"
#   },
#   "description": "Small and powerful, the Jigger is the best ride for the smallest of tikes! ..."
# }
pipeline = client.pipeline()

print("Pipeline ", pipeline)
pipeline.json().set("redis_key", "$", data)
print("We set the data")
pipeline.execute()
print("We executed the pipeline")

# Retrieve
res = client.hget("sample", "charge_name")
# result = client.json().get("charge:1")
print(res)
