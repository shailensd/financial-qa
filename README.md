# FinDoc Intelligence

A multi-model financial Q&A system that answers questions about SEC filings using a Planner-Executor-Critic agent pipeline backed by hybrid retrieval (ChromaDB + BM25).

## Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18 + Vite, Vanilla CSS (dark mode) |
| **Backend** | FastAPI + SQLAlchemy (async) + PostgreSQL |
| **LLMs** | Gemini 2.5 Flash (Google AI) · Llama 3.2 3B · Gemma 2 9B (both via Ollama) |
| **Retrieval** | ChromaDB (dense) + BM25Okapi (sparse) fused via Reciprocal Rank Fusion |
| **Agent** | LangGraph — Planner → Executor → Critic loop (max 2 repair iterations) |
| **Embeddings** | `all-MiniLM-L6-v2` via `sentence-transformers` |

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL running locally
- [Ollama](https://ollama.com) (if using local models)
- Google AI Studio API key (for Gemini)

## Setup

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy and fill in the environment file:
```bash
cp ../.env.example backend/.env
# Edit backend/.env — set DATABASE_URL and GEMINI_API_KEY
```

Create the database and run migrations:
```bash
createdb findoc_intelligence
alembic upgrade head
```

Start the server:
```bash
./start_server.sh
# or: uvicorn app.main:app --reload --port 8000
```

### 2. Ingest SEC Filings

```bash
# Download filings (edit company list in script as needed)
python scripts/download_filings.py

# Ingest into PostgreSQL + ChromaDB
python scripts/ingest_filings.py

# Verify ingestion
python scripts/verify_ingestion.py
```

### 3. Local Models (optional)

```bash
ollama serve
ollama pull llama3.2:3b   # ~2 GB
ollama pull gemma2:9b     # ~5.5 GB
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

## API

| Method | Route | Description |
|---|---|---|
| `POST` | `/query` | Submit a question to one or more models |
| `GET` | `/history?session_id=<id>` | Fetch session turn history |
| `GET` | `/logs?session_id=<id>` | Fetch structured execution logs |
| `GET` | `/health` | Check DB / ChromaDB / BM25 status |
| `POST` | `/evaluate` | Run Ragas evaluation over the test set |

### Query Request

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "query_text": "What was Apple's revenue in FY2023?",
  "models": ["gemini"],
  "company": "Apple"
}
```

`models` accepts any combination of `"llama"`, `"gemma"`, `"gemini"`. Models run **sequentially** to avoid RAM pressure.

## Agent Pipeline

```
User Query
  └─► RefusalGuard        blocks investment advice / future predictions
        └─► MemoryRetrieve fetch session context for Planner
              └─► Planner  LLM decomposes query into tool calls (JSON)
                    └─► Executor  runs LOOKUP / CALCULATE / COMPARE tools
                          └─► Critic  validates numbers + citations
                                ├─ repair_numerical → back to Planner (max 2×)
                                ├─ repair_citation  → back to Planner (max 2×)
                                └─ approved → MemoryWrite → DB commit
```

## Project Structure

```
financial-qa/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI routes and request/response models
│   │   ├── config.py         # Pydantic settings (env vars)
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   ├── crud.py           # Async DB operations
│   │   ├── database.py       # Engine and session factory
│   │   ├── logging.py        # StructuredLogger (sanitises API keys)
│   │   ├── agent/
│   │   │   ├── pipeline.py   # LangGraph graph definition and all nodes
│   │   │   ├── tools.py      # LOOKUP / CALCULATE / COMPARE tool registry
│   │   │   └── memory.py     # MemorySystem (write / retrieve / summarise)
│   │   └── ml/
│   │       ├── llm_router.py         # LiteLLM wrapper with retry logic
│   │       ├── hybrid_retrieval.py   # Dense + sparse + RRF fusion
│   │       └── document_processor.py # HTML parsing → chunking → embedding
│   ├── scripts/
│   │   ├── download_filings.py  # SEC EDGAR filing downloader
│   │   ├── ingest_filings.py    # Chunk + embed + index filings
│   │   └── verify_ingestion.py  # Sanity check after ingestion
│   ├── eval/
│   │   ├── few_shot_examples.json    # Planner few-shot examples
│   │   └── evaluation_set_seed.json  # Ragas test questions
│   ├── tests/
│   │   ├── unit/             # pytest unit tests (mocked LLMs)
│   │   └── integration/      # pytest integration tests (live DB)
│   └── alembic/              # DB migrations
└── frontend/
    └── src/
        ├── App.jsx                    # Root layout and ResultCard components
        ├── components/
        │   ├── QueryInput.jsx         # Company dropdown, model pills, submit
        │   ├── CitationList.jsx       # Expandable citation accordion
        │   ├── AgentTrace.jsx         # Timeline view of plan + tool results
        │   └── SessionContext.jsx     # Sidebar with session history
        ├── hooks/
        │   ├── useQuery.js            # Query submission + result state
        │   └── useSession.js          # Session ID persistence + history fetch
        └── services/
            └── api.js                 # Axios instance with error normalisation
```

## Running Tests

```bash
# Backend unit tests
cd backend
pytest tests/unit/ -v

# Backend integration tests (requires running DB + Ollama)
pytest tests/integration/ -v

# Frontend tests
cd frontend
npm test
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | ✅ | — | PostgreSQL connection string |
| `GEMINI_API_KEY` | ✅ | — | Google AI Studio API key |
| `OLLAMA_BASE_URL` | | `http://localhost:11434` | Ollama API endpoint |
| `CHROMA_PERSIST_DIR` | | `./chroma_db` | ChromaDB storage path |
| `CHUNK_SIZE` | | `800` | Token size per chunk |
| `CHUNK_OVERLAP` | | `200` | Token overlap between chunks |
| `RETRIEVAL_TOP_K` | | `10` | Chunks returned per retrieval |
