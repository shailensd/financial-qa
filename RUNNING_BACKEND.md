# Running the FinDoc Intelligence Backend

This guide will help you start the backend server and verify everything works correctly.

## Prerequisites

1. **Python Virtual Environment**: Already set up at `backend/.venv`
2. **PostgreSQL Database**: Running locally (or use SQLite for testing)
3. **Environment Variables**: Configured in `backend/.env`
4. **Data Ingestion**: SEC filings should be downloaded and ingested (optional for basic testing)

## Quick Start

### 1. Activate Virtual Environment

```bash
cd backend
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate  # On Windows
```

### 2. Verify Environment Variables

Check your `backend/.env` file has the required variables:

```bash
cat .env
```

Required variables:
- `DATABASE_URL` - PostgreSQL connection string (or use SQLite for testing)
- `GEMINI_API_KEY` - Your Google AI Studio API key
- `CHROMA_PERSIST_DIR` - Path to ChromaDB storage (default: ./chroma_db)

**For Quick Testing with SQLite** (no PostgreSQL needed):
```bash
# Temporarily override DATABASE_URL
export DATABASE_URL="sqlite+aiosqlite:///./test.db"
```

### 3. Run Database Migrations (if using PostgreSQL)

```bash
# Initialize database schema
alembic upgrade head
```

### 4. Start the Backend Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

You should see output like:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Starting FinDoc Intelligence API...
INFO:     Database tables initialized
INFO:     Hybrid retriever initialized with BM25 index
INFO:     FinDoc Intelligence API started successfully
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Verify Everything Works

### 1. Check Health Endpoint

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "db": "connected",
  "chroma": "connected",
  "bm25": "ready"
}
```

### 2. Access API Documentation

Open your browser and visit:
- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### 3. Test Root Endpoint

```bash
curl http://localhost:8000/
```

Expected response:
```json
{
  "name": "FinDoc Intelligence API",
  "version": "1.0.0",
  "description": "Financial Q&A system with RAG and Planner-Executor-Critic agent pipeline",
  "docs": "/docs",
  "health": "/health"
}
```

### 4. Test Query Endpoint (Basic)

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session-123",
    "query_text": "What is Apple revenue?",
    "models": ["gemini"],
    "company": "Apple"
  }'
```

**Note**: This will fail if:
- No data has been ingested (expected - see Data Ingestion below)
- GEMINI_API_KEY is not valid
- Retrieval system is not initialized

### 5. Test History Endpoint

```bash
curl "http://localhost:8000/history?session_id=test-session-123"
```

### 6. Test Logs Endpoint

```bash
curl "http://localhost:8000/logs?limit=10"
```

## Data Ingestion (Required for Full Functionality)

The backend needs SEC filing data to answer queries. Follow these steps:

### 1. Download SEC Filings

```bash
cd backend
python scripts/download_filings.py
```

This will download ~50-60 filings to `backend/data/raw/`

### 2. Ingest Filings into Database

```bash
python scripts/ingest_filings.py
```

This will:
- Parse and chunk all downloaded filings
- Store chunks in PostgreSQL
- Generate embeddings and store in ChromaDB
- Take 10-30 minutes depending on your machine

### 3. Verify Ingestion

```bash
# Check chunk count in database
psql $DATABASE_URL -c "SELECT COUNT(*) FROM chunks;"

# Should show ~15,000-25,000 chunks
```

## Running Tests

### Run All Integration Tests

```bash
cd backend
pytest tests/integration/test_api.py -v
```

### Run Specific Test

```bash
pytest tests/integration/test_api.py::test_health_endpoint -v
```

### Run with Coverage

```bash
pytest tests/integration/test_api.py --cov=app --cov-report=html
```

## Troubleshooting

### Issue: "Database connection failed"

**Solution 1**: Use SQLite for testing
```bash
export DATABASE_URL="sqlite+aiosqlite:///./test.db"
uvicorn app.main:app --reload
```

**Solution 2**: Start PostgreSQL
```bash
# macOS with Homebrew
brew services start postgresql@15

# Check if running
pg_isready
```

### Issue: "ChromaDB unavailable"

This is OK for basic testing. The system will fall back to BM25-only retrieval.

To fix:
- Ensure `CHROMA_PERSIST_DIR` exists: `mkdir -p backend/chroma_db`
- Check ChromaDB is installed: `pip list | grep chromadb`

### Issue: "BM25 index not available"

This means no data has been ingested. Either:
1. Run the ingestion scripts (see Data Ingestion above)
2. Or test with endpoints that don't require data (health, logs, history)

### Issue: "GEMINI_API_KEY not set"

Get an API key from Google AI Studio:
1. Visit https://aistudio.google.com/apikey
2. Create a new API key
3. Add to `backend/.env`:
   ```
   GEMINI_API_KEY=your_actual_key_here
   ```

### Issue: "Module not found" errors

Reinstall dependencies:
```bash
cd backend
pip install -r requirements.txt
```

### Issue: Port 8000 already in use

Use a different port:
```bash
uvicorn app.main:app --reload --port 8001
```

## Development Workflow

### 1. Make Code Changes

Edit files in `backend/app/`

### 2. Auto-Reload

If running with `--reload`, the server will automatically restart on file changes.

### 3. Check Logs

The server logs all requests and errors to stdout. Watch for:
- `INFO` - Normal operations
- `WARNING` - Degraded functionality
- `ERROR` - Failed operations

### 4. Test Changes

```bash
# Run specific test
pytest tests/integration/test_api.py::test_query_endpoint_validation -v

# Or use curl
curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -d '...'
```

## API Endpoints Summary

| Endpoint | Method | Purpose | Requires Data |
|----------|--------|---------|---------------|
| `/` | GET | API information | No |
| `/health` | GET | System status | No |
| `/docs` | GET | Interactive API docs | No |
| `/query` | POST | Process queries | Yes |
| `/history` | GET | Session history | No |
| `/logs` | GET | Execution logs | No |
| `/evaluate` | POST | Run evaluation | Yes |

## Next Steps

1. ✅ Start the backend server
2. ✅ Verify health endpoint works
3. ✅ Access API documentation at `/docs`
4. ⏳ Download and ingest SEC filings (optional but recommended)
5. ⏳ Test query endpoint with real data
6. ⏳ Build the frontend (Task 16-17)

## Monitoring

### View Real-Time Logs

```bash
# In the terminal where uvicorn is running
# Logs appear automatically

# Or use tail if logging to file
tail -f logs/app.log
```

### Check Database

```bash
# Connect to PostgreSQL
psql $DATABASE_URL

# View tables
\dt

# Check data
SELECT COUNT(*) FROM documents;
SELECT COUNT(*) FROM chunks;
SELECT COUNT(*) FROM queries;
```

### Monitor ChromaDB

```bash
# Check ChromaDB directory
ls -lh backend/chroma_db/

# Should contain:
# - chroma.sqlite3 (metadata)
# - Collection directories with .bin files (vectors)
```

## Production Deployment

For production deployment, see:
- Task 21: Dockerization
- Task 22: Cloud Deployment (Railway/Render)

The current setup is optimized for local development with auto-reload and detailed logging.
