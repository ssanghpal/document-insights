import json
import time
import random
import hashlib
from threading import Thread
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.db import redis_client, documents_collection

TASK_QUEUE = "document_queue"

import random

MAX_RETRIES = 3
BACKOFF_SECONDS = [2, 5, 10]  # Example backoff times

def consumer_worker():
    while True:
        task_json = redis_client.blpop(TASK_QUEUE, timeout=1)
        if task_json is None:
            continue
        _, payload = task_json
        task = json.loads(payload)
        document_id = task["document_id"]

        # Fetch the document
        doc = documents_collection.find_one({"document_id": document_id})
        if not doc:
            continue

        # Mark as processing
        documents_collection.update_one({"document_id": document_id}, {"$set": {"status": "processing"}})

        # Retry loop
        for attempt in range(MAX_RETRIES):
            try:
                # Simulate processing
                time.sleep(random.randint(10, 30))  # simulate work
                if random.random() < 0.1:  # 10% failure
                    raise Exception("Random simulated failure")

                # Save summary
                summary = f"Summary of '{doc['title']}' with {len(doc['content'])} chars"
                documents_collection.update_one(
                    {"document_id": document_id},
                    {"$set": {"status": "completed", "summary": summary}}
                )
                print(f"Document {document_id} completed")
                break  # Success, exit retry loop

            except Exception as e:
                print(f"Document {document_id} failed attempt {attempt + 1}: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(BACKOFF_SECONDS[attempt])  # Exponential backoff
                else:
                    # Mark as failed
                    documents_collection.update_one(
                        {"document_id": document_id},
                        {"$set": {"status": "failed", "summary": None}}
                    )
                    print(f"Document {document_id} marked as failed after {MAX_RETRIES} attempts")

def start_consumers(n: int = 5):
    threads = []
    for _ in range(n):
        t = Thread(target=consumer_worker, daemon=True)
        t.start()
        threads.append(t)
    print(f"{n} consumer threads started")