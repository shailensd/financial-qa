# FinDoc Intelligence - Architecture Overview

## System Architecture with Model Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                             │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  QueryInput Component                                       │    │
│  │                                                             │    │
│  │  Question: "What was Apple's revenue in FY2023?"          │    │
│  │                                                             │    │
│  │  Select Models:                                            │    │
│  │  ☑ Llama 3.2 3B (Local)                                   │    │
│  │  ☑ Gemma 2 9B (Local)                                     │    │
│  │  ☑ Gemini 2.0 Flash (Cloud)                               │    │
│  │                                                             │    │
│  │  [Submit Query]                                            │    │
│  └────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│                              │ HTTP POST /query                      │
│                              │ {"models": ["llama","gemma","gemini"]}│
│                              ▼                                       │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                      BACKEND (FastAPI)                               │
│                                                                      │
│  POST /query endpoint receives request                              │
│  Validates: session_id, query_text, models[]                        │
│                                                                      │
│  Sequential Processing (one model at a time):                       │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │ 1. Process with Llama 3.2 3B                            │       │
│  │    ├─> Agent Pipeline (Planner→Executor→Critic)        │       │
│  │    ├─> Retrieval (Hybrid: BM25 + ChromaDB)             │       │
│  │    └─> LLM Call via LiteLLM                             │       │
│  │         └─> Ollama (localhost:11434)                    │       │
│  │              └─> llama3.2:3b model                      │       │
│  │    Result: {response, confidence: 0.85, latency: 8.5s} │       │
│  └─────────────────────────────────────────────────────────┘       │
│                              │                                       │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │ 2. Process with Gemma 2 9B                              │       │
│  │    ├─> Agent Pipeline (Planner→Executor→Critic)        │       │
│  │    ├─> Retrieval (Hybrid: BM25 + ChromaDB)             │       │
│  │    └─> LLM Call via LiteLLM                             │       │
│  │         └─> Ollama (localhost:11434)                    │       │
│  │              └─> gemma2:9b model                        │       │
│  │    Result: {response, confidence: 0.92, latency: 25s}  │       │
│  └─────────────────────────────────────────────────────────┘       │
│                              │                                       │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │ 3. Process with Gemini 2.0 Flash                        │       │
│  │    ├─> Agent Pipeline (Planner→Executor→Critic)        │       │
│  │    ├─> Retrieval (Hybrid: BM25 + ChromaDB)             │       │
│  │    └─> LLM Call via LiteLLM                             │       │
│  │         └─> Google AI Studio API                        │       │
│  │              └─> gemini-2.5-flash model                 │       │
│  │    Result: {response, confidence: 0.98, latency: 2s}   │       │
│  └─────────────────────────────────────────────────────────┘       │
│                              │                                       │
│  Return combined results:                                            │
│  {                                                                   │
│    "results": [                                                      │
│      {model: "llama", response: "...", confidence: 0.85, ...},      │
│      {model: "gemma", response: "...", confidence: 0.92, ...},      │
│      {model: "gemini", response: "...", confidence: 0.98, ...}      │
│    ]                                                                 │
│  }                                                                   │
│                              │                                       │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
                               │ HTTP Response
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                             │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  AnswerDisplay Component (Tabbed)                          │    │
│  │                                                             │    │
│  │  [Llama 3.2] [Gemma 2] [Gemini 2.0] ← Tabs                │    │
│  │  ─────────────────────────────────────────────────────     │    │
│  │                                                             │    │
│  │  Response: Apple's total revenue in FY2023 was...         │    │
│  │  Confidence: 85%                                           │    │
│  │  Latency: 8.5s                                             │    │
│  │  Citations: 3 chunks                                       │    │
│  │                                                             │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Model Routing Details

### Local Models (Llama & Gemma)

```
Frontend Request
    │
    ▼
FastAPI Backend
    │
    ▼
LiteLLM Router
    │
    ├─> Model: "llama" → "ollama/llama3.2:3b"
    │   │
    │   ▼
    │   Ollama Service (localhost:11434)
    │   │
    │   ▼
    │   Llama 3.2 3B Model (2GB, loaded in RAM)
    │   │
    │   ▼
    │   Response
    │
    └─> Model: "gemma" → "ollama/gemma2:9b"
        │
        ▼
        Ollama Service (localhost:11434)
        │
        ▼
        Gemma 2 9B Model (5.5GB, loaded in RAM)
        │
        ▼
        Response
```

### Cloud Model (Gemini)

```
Frontend Request
    │
    ▼
FastAPI Backend
    │
    ▼
LiteLLM Router
    │
    └─> Model: "gemini" → "gemini/gemini-2.5-flash"
        │
        ▼
        Google AI Studio API (HTTPS)
        │
        ▼
        Gemini 2.0 Flash (Cloud)
        │
        ▼
        Response
```

## Data Flow for a Single Query

```
1. User Input
   ├─ Question: "What was Apple's revenue in FY2023?"
   ├─ Company: "Apple"
   └─ Models: ["llama", "gemma", "gemini"]

2. Frontend → Backend
   POST /query
   {
     "session_id": "uuid",
     "query_text": "What was Apple's revenue in FY2023?",
     "models": ["llama", "gemma", "gemini"],
     "company": "Apple"
   }

3. Backend Processing (Sequential)
   
   For each model in ["llama", "gemma", "gemini"]:
   
   a) RefusalGuard
      ├─ Check for prohibited keywords
      └─ Pass ✓
   
   b) Memory Retrieve
      ├─ Fetch session context
      └─ Return memory_context
   
   c) Planner
      ├─ Decompose query into tool calls
      ├─ Use model (llama/gemma/gemini)
      └─ Return plan: [LOOKUP(Apple, revenue)]
   
   d) Executor
      ├─ Execute LOOKUP tool
      ├─ Hybrid Retrieval (BM25 + ChromaDB)
      ├─ Find relevant chunks
      ├─ Generate response with model
      └─ Return draft_response + citations
   
   e) Critic
      ├─ Verify numerical accuracy
      ├─ Check citation completeness
      └─ Return verdict: "approved"
   
   f) Memory Write
      └─ Store turn in database
   
   g) Return result for this model

4. Backend → Frontend
   {
     "results": [
       {
         "model": "llama",
         "response_text": "Apple's total revenue...",
         "confidence_score": 0.85,
         "latency_ms": 8500,
         "citations": [...]
       },
       {
         "model": "gemma",
         "response_text": "Apple's total revenue...",
         "confidence_score": 0.92,
         "latency_ms": 25000,
         "citations": [...]
       },
       {
         "model": "gemini",
         "response_text": "Apple's total revenue...",
         "confidence_score": 0.98,
         "latency_ms": 2000,
         "citations": [...]
       }
     ]
   }

5. Frontend Display
   ├─ Tab 1: Llama results
   ├─ Tab 2: Gemma results
   └─ Tab 3: Gemini results
```

## Component Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│                    User's Machine                            │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Browser    │  │   Backend    │  │   Ollama     │     │
│  │  (Frontend)  │  │   (FastAPI)  │  │  (Local LLM) │     │
│  │              │  │              │  │              │     │
│  │  React App   │  │  Python      │  │  Llama 3.2   │     │
│  │  Port 3000   │  │  Port 8000   │  │  Gemma 2     │     │
│  │              │  │              │  │  Port 11434  │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                 │              │
│         └────────┬────────┴────────┬────────┘              │
│                  │                 │                        │
│         ┌────────▼─────────────────▼────────┐              │
│         │      PostgreSQL Database          │              │
│         │      (Chunks, Queries, etc.)      │              │
│         └───────────────────────────────────┘              │
│                                                              │
│         ┌───────────────────────────────────┐              │
│         │      ChromaDB Vector Store        │              │
│         │      (Embeddings)                 │              │
│         └───────────────────────────────────┘              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ HTTPS (Gemini only)
                          ▼
              ┌───────────────────────┐
              │  Google AI Studio     │
              │  (Gemini 2.0 Flash)   │
              └───────────────────────┘
```

## Key Points

✅ **Frontend has full control**: User selects which models to use via checkboxes

✅ **Backend handles routing**: LiteLLM routes to Ollama (local) or Google API (cloud)

✅ **Sequential processing**: Models run one at a time to avoid RAM pressure

✅ **Unified interface**: Same agent pipeline for all models

✅ **Flexible deployment**: 
   - Local dev: All 3 models work
   - Cloud deploy: Gemini only (Ollama requires GPU)

✅ **User choice**: Can use 1, 2, or all 3 models per query

## Example User Workflows

### Workflow 1: Quick Answer (Gemini Only)
```
User checks: ☑ Gemini
Backend calls: Gemini API
Response time: ~2 seconds
Use case: Fast, accurate answers
```

### Workflow 2: Privacy Mode (Local Only)
```
User checks: ☑ Llama ☑ Gemma
Backend calls: Ollama → Llama, then Ollama → Gemma
Response time: ~33 seconds (8.5s + 25s)
Use case: Sensitive data, no cloud
```

### Workflow 3: Full Comparison (All Three)
```
User checks: ☑ Llama ☑ Gemma ☑ Gemini
Backend calls: All three sequentially
Response time: ~35 seconds total
Use case: Research, quality comparison
```

## Summary

**Yes, you can absolutely run both local models (Llama & Gemma) and cloud model (Gemini) from the frontend!**

The frontend provides:
- ✅ Checkboxes to select models
- ✅ Ability to select 1, 2, or all 3
- ✅ Tabbed or side-by-side results
- ✅ Comparison of quality, speed, confidence

The backend handles:
- ✅ Routing to Ollama (local) or Google API (cloud)
- ✅ Sequential processing (one at a time)
- ✅ Unified agent pipeline for all models
- ✅ Returning combined results

It's all designed and ready to implement! 🎉
