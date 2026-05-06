# FinDoc Intelligence - Quick Start Guide

## 🚀 Start the Backend in 3 Steps

### Step 1: Navigate to Backend Directory
```bash
cd backend
```

### Step 2: Check Your Setup (Optional but Recommended)
```bash
./test_setup.sh
```

This will verify:
- ✅ Python and virtual environment
- ✅ Environment variables (.env file)
- ✅ Database connection
- ✅ Data ingestion status
- ✅ Required dependencies

### Step 3: Start the Server
```bash
./start_server.sh
```

Or manually:
```bash
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## ✅ Verify It's Working

### 1. Check Health
```bash
curl http://localhost:8000/health
```

Expected output:
```json
{
  "status": "ok",
  "db": "connected",
  "chroma": "connected",
  "bm25": "ready"
}
```

### 2. Open API Documentation
Visit in your browser:
- **Interactive Docs**: http://localhost:8000/docs
- **API Info**: http://localhost:8000/

### 3. Test a Query (if you have data ingested)
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-123",
    "query_text": "What was Apple revenue in FY2023?",
    "models": ["gemini"],
    "company": "Apple"
  }'
```

## 📊 Current Status

Based on your setup check:
- ✅ **Database**: PostgreSQL connected with 7 tables
- ✅ **Data**: 3,760 chunks from 56 SEC filings ingested
- ✅ **ChromaDB**: Ready
- ⚠️  **API Key**: Using temp key (update GEMINI_API_KEY in .env for real queries)

## 🤖 Using Local Models (Llama & Gemma)

The system supports 3 models:
- **Gemini 2.0 Flash** - Cloud (requires API key) ☁️
- **Llama 3.2 3B** - Local (requires Ollama) 🏠
- **Gemma 2 9B** - Local (requires Ollama) 🏠

### Quick Ollama Setup

```bash
cd backend
./setup_ollama.sh
```

This will:
1. Check if Ollama is installed
2. Start Ollama service
3. Download Llama 3.2 3B (~2GB) and Gemma 2 9B (~5.5GB)
4. Test both models

**Or manually:**
```bash
# Install Ollama (macOS)
brew install ollama

# Start Ollama
ollama serve

# Download models
ollama pull llama3.2:3b
ollama pull gemma2:9b
```

**For detailed instructions, see:** `OLLAMA_SETUP.md`

## 🔧 Configuration

Your `.env` file should have:
```bash
DATABASE_URL=postgresql://shailensutradhar@localhost:5432/findoc_intelligence
CHROMA_PERSIST_DIR=./chroma_db
GEMINI_API_KEY=your_actual_key_here  # Get from https://aistudio.google.com/apikey
```

## 📝 Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | System health check |
| `/docs` | GET | Interactive API documentation |
| `/query` | POST | Process financial queries |
| `/history` | GET | Get session history |
| `/logs` | GET | Get execution logs |
| `/evaluate` | POST | Run evaluation metrics |

## 🎯 Next Steps

1. ✅ Backend is running
2. Update `GEMINI_API_KEY` in `.env` for real queries
3. Test queries via `/docs` interface
4. Build the frontend (Tasks 16-17)
5. Deploy to production (Tasks 21-22)

## 🐛 Troubleshooting

### Server won't start?
```bash
# Check if port 8000 is in use
lsof -i :8000

# Use a different port
uvicorn app.main:app --reload --port 8001
```

### Database connection error?
```bash
# Check PostgreSQL is running
pg_isready

# Or use SQLite for testing
export DATABASE_URL="sqlite+aiosqlite:///./test.db"
```

### Need more help?
See the detailed guide: `RUNNING_BACKEND.md`

## 📚 Documentation

- **Full Backend Guide**: `RUNNING_BACKEND.md`
- **API Docs**: http://localhost:8000/docs (when server is running)
- **Requirements**: `.kiro/specs/findoc-intelligence/requirements.md`
- **Design**: `.kiro/specs/findoc-intelligence/design.md`
- **Tasks**: `.kiro/specs/findoc-intelligence/tasks.md`
