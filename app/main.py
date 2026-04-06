from fastapi import FastAPI, HTTPException, Query, Depends
from contextlib import asynccontextmanager
from uuid import uuid4
import hashlib
import json
import redis

from app.schemas import Document, DocumentResponse
from app.db import redis_client, mongo_client, documents_collection, init_db
from app.worker import start_consumers, TASK_QUEUE

# ----------------------------
# Helpers
# ----------------------------
def get_documents_collection():
    if documents_collection is None:
        raise RuntimeError("DB not initialized")
    return documents_collection

def user_active_jobs(user_id: str, collection=Depends(get_documents_collection)) -> int:
    return collection.count_documents({
        "user_id": user_id,
        "status": {"$in": ["queued", "processing"]}
    })

def get_cached_summary(user_id: str, content: str):
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    return redis_client.get(f"cache:{user_id}:{content_hash}")

# ----------------------------
# Lifespan
# ----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    #init_db()
    start_consumers(5)
    yield
    print("App shutting down... consumers will stop")

# ----------------------------
# FastAPI app
# ----------------------------
app = FastAPI(title="Document Insights", lifespan=lifespan)

# ----------------------------
# Endpoints
# ----------------------------
@app.post("/documents", response_model=DocumentResponse)
async def submit_document(
    doc: Document, 
    collection=Depends(get_documents_collection)
):
    # Rate limit
    if collection.count_documents({
        "user_id": doc.user_id,
        "status": {"$in": ["queued", "processing"]}
    }) >= 3:
        raise HTTPException(status_code=429, detail="Max 3 active documents per user exceeded")

    # Check for duplicates
    existing_doc = collection.find_one({
        "user_id": doc.user_id,
        "content": doc.content,
        "status": {"$in": ["queued", "processing", "completed"]}
    })

    # Return completed summary if exists
    if existing_doc and existing_doc["status"] == "completed":
        return DocumentResponse(
            document_id=existing_doc["document_id"],
            status="completed",
            summary=existing_doc.get("summary")
        )

    # If queued/processing, reject
    if existing_doc and existing_doc["status"] in ["queued", "processing"]:
        raise HTTPException(
            status_code=409,
            detail=f"Document already submitted and {existing_doc['status']}"
        )

    # Insert new document
    document_id = str(uuid4())
    collection.insert_one({
        "document_id": document_id,
        "user_id": doc.user_id,
        "title": doc.title,
        "content": doc.content,
        "status": "queued",
        "summary": None
    })

    # Enqueue task
    redis_client.rpush(TASK_QUEUE, json.dumps({
        "document_id": document_id,
        "user_id": doc.user_id,
        "title": doc.title,
        "content": doc.content
    }))

    return DocumentResponse(document_id=document_id, status="queued")

@app.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document_status(
    document_id: str,
    collection=Depends(get_documents_collection)
):
    doc = collection.find_one({"document_id": document_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse(
        document_id=document_id,
        status=doc["status"],
        summary=doc.get("summary")
    )

@app.get("/users/{user_id}/documents", response_model=list[DocumentResponse])
async def list_user_documents(
    user_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: str = None,
    collection=Depends(get_documents_collection)
):
    query = {"user_id": user_id}
    if status:
        query["status"] = status

    docs = collection.find(query)\
        .skip((page - 1) * page_size)\
        .limit(page_size)

    return [
        DocumentResponse(
            document_id=d["document_id"],
            status=d["status"],
            summary=d.get("summary")
        ) for d in docs
    ]

@app.get("/health")
async def health_check():
    health_status = {"redis": False, "mongodb": False}

    # Check Redis
    try:
        if redis_client.ping():
            health_status["redis"] = True
    except redis.RedisError:
        health_status["redis"] = False

    # Check MongoDB
    try:
        mongo_client.admin.command("ping")
        health_status["mongodb"] = True
    except Exception:
        health_status["mongodb"] = False

    if all(health_status.values()):
        return {"status": "ok", "services": health_status}
    else:
        raise HTTPException(status_code=503, detail={"status": "fail", "services": health_status})