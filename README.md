Document Insights API
Overview

Document Insights is a FastAPI-based service that allows users to submit documents for asynchronous processing. The system supports:

Document submission with content-based caching
Background processing with worker threads
Per-user rate limiting (max 3 active documents)
Document status tracking
Health checks for MongoDB and Redis

This project uses MongoDB as the persistent store and Redis for caching and queueing.

**Design Decisions**

**1. Project Structure**
app/db.py – Database and Redis initialization, indexes creation.
app/main.py – FastAPI application and endpoints. Uses a lifespan context to initialize DB and start background workers.
app/worker.py – Background consumer threads that process documents asynchronously.
app/schemas.py – Pydantic models for request and response validation.
tests/ – Test cases with mocked MongoDB and Redis.

Decision: Split into multiple files for modularity, maintainability, and testability.

**2. Asynchronous Processing**
Background workers pick tasks from Redis using blpop.
Status changes: queued → processing → completed | failed.
10% of tasks randomly fail to test error handling.

Decision: Used threads for simplicity. In production, Celery or RQ could replace it for scalability.

**3. Content-Based Caching**
Document content is hashed using SHA256.
If a user submits identical content, the API returns the previously computed summary immediately.

Decision: Reduces repeated processing and improves response times. TTL can be added to the cache for automatic expiration.

**4. Rate Limiting**
Each user is allowed at most 3 active documents (queued or processing).
Exceeding the limit returns HTTP 429 (Too Many Requests).

Decision: Redis can also be used for faster rate-limiting in high-traffic scenarios.

**5. Indexing**
MongoDB index on document_id (unique).
Partial index for active documents (queued or processing) to enforce uniqueness when needed.

Trade-off: Partial indexes avoid duplicate tasks but require careful management to avoid index conflicts.

**6. Health Checks**
/health endpoint checks both Redis and MongoDB connectivity.
Returns HTTP 503 if any service is down.

Decision: Improves observability and readiness for deployment.

**Assumptions**
Users are uniquely identified by user_id.
Content hash is sufficient to detect duplicates.
Simulated processing time is 10–30 seconds; shortened in tests.
Redis and MongoDB are locally available for testing.

**Edge Cases Considered**
Duplicate document submissions (queued, processing, completed).
Random processing failures handled and status updated to failed.
Invalid or missing documents result in HTTP 404.
Rate-limiting enforced per user.
Index creation conflicts handled during DB initialization.
