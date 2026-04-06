import pytest
from unittest.mock import MagicMock, patch # Add patch
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_redis, get_mongo

@pytest.fixture(autouse=True)
def mock_worker():
    """
    Prevents background worker threads from starting during tests.
    Adjust 'app.worker.start_workers' to the actual path where 
    thread-starting logic lives.
    """
    with patch("app.main.start_workers") as mock: 
        yield mock

@pytest.fixture
def redis_mock():
    mock = MagicMock()
    # Mock 'ping' so health check thinks Redis is up
    mock.ping.return_value = True
    mock.get.return_value = None
    return mock

@pytest.fixture
def mongo_mock():
    mock = MagicMock()
    # Mock 'command' so health check (db.command("ping")) passes
    mock.command.return_value = {"ok": 1.0}
    mock.documents = MagicMock()
    return mock

@pytest.fixture
def test_client(redis_mock, mongo_mock):
    # Dependency Overrides
    app.dependency_overrides[get_redis] = lambda: redis_mock
    app.dependency_overrides[get_mongo] = lambda: mongo_mock
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides = {}