import uuid
import json
import pytest

def test_health_check(test_client, redis_mock, mongo_mock):
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "services" in data
    assert "redis" in data["services"]
    assert "mongo" in data["services"]

def test_enqueue_document_success(test_client, redis_mock, mongo_mock):
    doc_id = str(uuid.uuid4())
    payload = {
        "document_id": doc_id,
        "user_id": "user1",
        "title": "Test Doc",
        "content": "Hello World"
    }

    response = test_client.post("/documents", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == doc_id
    assert data["status"] == "queued"
    redis_mock.rpush.assert_called_once()

def test_duplicate_document_return_cached(test_client, redis_mock, mongo_mock):
    doc_id = str(uuid.uuid4())
    payload = {
        "document_id": doc_id,
        "user_id": "user1",
        "title": "Duplicate",
        "content": "Same content"
    }

    # Simulate Redis cache hit
    redis_mock.get.return_value = json.dumps({"summary": "Cached summary"})
    response = test_client.post("/documents", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == "Cached summary"

def test_poll_document_status(test_client, mongo_mock):
    doc_id = str(uuid.uuid4())
    # Note how we access the nested mock we defined in conftest
    mongo_mock.documents.find_one.return_value = {
        "document_id": doc_id,
        "status": "processing",
        "summary": None
    }

    response = test_client.get(f"/documents/{doc_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == doc_id
    assert data["status"] == "processing"

def test_list_user_documents(test_client, mongo_mock):
    user_id = "user1"
    mongo_mock.documents.find.return_value = [
        {"document_id": "1", "status": "completed"},
        {"document_id": "2", "status": "queued"}
    ]

    response = test_client.get(f"/users/{user_id}/documents?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["documents"]) == 2