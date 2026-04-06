import redis
from pymongo import MongoClient

redis_client = None
mongo_client = None
documents_collection = None

def init_db():
    global redis_client, mongo_client, documents_collection
    redis_client = redis.Redis(host="redis", port=6379, db=0, decode_responses=True)
    mongo_client = MongoClient("mongodb://mongo:27017")
    documents_collection = mongo_client.document_insights.documents

    # documents_collection.create_index(
    #     [("document_id", 1)],
    #     unique=True,
    #     partialFilterExpression={"status": {"$in": ["queued", "processing"]}}
    # )

init_db()