from dotenv import load_dotenv
import os

load_dotenv()  # loads .env from root

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
DB_NAME = os.getenv("DB_NAME", "document_insights")
CACHE_TTL = int(os.getenv("CACHE_TTL", 3600))