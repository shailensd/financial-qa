# FinDoc Intelligence - Project Specification v2.0

## 1. Project Overview & Goal
**FinDoc Intelligence** is a production-ready, full-stack financial Q&A application that allows users to ask questions about SEC financial filings (10-K/10-Q). The system utilizes a Retrieval-Augmented Generation (RAG) architecture and features a Planner-Executor-Critic agent pipeline to ensure accuracy, citation grounding, and safety/refusal guardrails.

---

## 2. Technology Stack & Architecture

### 2.1. Backend / Data Layer
- **Language:** Python 3.11+
- **Web Framework:** FastAPI (RESTful API orchestration)
- **Relational Database:** PostgreSQL (stores document metadata, queries, responses, citations, memory summaries)
- **ORM:** SQLAlchemy (async/eager loading patterns to prevent N+1 issues)
- **Vector Database:** ChromaDB (local semantic search)
- **Retrieval:** Hybrid — Dense embeddings via `sentence-transformers` + Sparse keyword via `BM25Okapi`

### 2.2. Frontend Layer
- **Framework:** React (functional components, ES6+, hooks)
- **State Management:** `useState`, `useEffect`, custom hooks (`useQuery`, `useSession`)
- **API Client:** Axios (with interceptors for error handling)
- **Styling:** Tailwind CSS

### 2.3. ML & LLM Integration
- **Primary (open-source):** Llama 3.3 70B Versatile via Groq API
- **Comparator 2 (commercial):** Gemini 2.5 Flash via Google AI Studio API
- **LLM Router:** LiteLLM (unified calling format across all models)
- **Agent Framework:** LangGraph `StateGraph` — Planner-Executor-Critic pipeline with stateful memory

### 2.4. Infrastructure / Deployment
- **Development:** PostgreSQL and ChromaDB run natively (no Docker) to conserve RAM. Models are accessed via cloud APIs (Groq and Google AI Studio) to reduce local compute requirements.
- **Production:** Docker + Docker Compose for final submission.
- **Hosting:** Railway or Render

---

## 3. Current Project State

- **Backend skeleton** (`backend/app`): FastAPI `main.py` with `/health` and `/query` endpoints.
- **Agent stub** (`backend/app/agent/pipeline.py`): Skeletal `PlannerExecutorCriticPipeline` mocking all three stages.
- **Retrieval stub** (`backend/app/ml/hybrid_retrieval.py`): `HybridRetriever` returning mock data.
- **Evaluation seed** (`backend/eval/evaluation_set_seed.json`): 10 initial test cases (factual_lookup, refusal_investment_advice).

---

## 4. Implementation Phases

### Phase 1: Database & Persistence Layer

1. **PostgreSQL Setup** — connection engine and `SessionLocal` dependency in `backend/app/database.py`.
2. **Schema Definition** (`backend/app/models.py`):
   - `documents` — SEC filings (company, type, year, metadata)
   - `chunks` — text splits with `document_id` FK, section label, chunk index
   - `queries` — user questions, timestamp, session_id, model_used
   - `responses` — generated answers linked to queries; stores model, confidence, refusal flag, repair_count, latency_ms
   - `citations` — junction table linking responses to chunks with relevance scores
   - `memory_summaries` — compressed session summaries (session_id, turn_range, summary_text, created_at)
   - `logs` — structured JSON log entries per request (session_id, query_id, log_json, created_at)
3. **CRUD Operations** (`backend/app/crud.py`) — use `joinedload` throughout to prevent N+1 queries.

> **Why `memory_summaries`?** LangGraph checkpointing alone replays raw chat history. The rubric requires memory to be "written, summarized, and retrieved." This table stores LLM-compressed summaries for long-horizon retrieval without ballooning the context window.

---

### Phase 2: Document Processing & RAG Pipeline

1. **Document Processor** (`backend/app/ml/document_processor.py`):
   - Parse SEC 10-K/10-Q plain-text files
   - Chunk at 800 words with 200-word overlap, retaining section label and page metadata
2. **Embedding Generation & ChromaDB Ingestion:**
   - `all-MiniLM-L6-v2` → 384-dim embeddings ingested into ChromaDB with chunk metadata
   - *Note: this is a general-purpose model. Document the domain-gap tradeoff vs. FinBERT in the final report.*
3. **Hybrid Retrieval** (`backend/app/ml/hybrid_retrieval.py`):
   - Dense retrieval via ChromaDB cosine similarity
   - Sparse retrieval via `BM25Okapi`
   - Score fusion via Reciprocal Rank Fusion (RRF)

---

### Phase 3: LLM Integration & Tool Registry

1. **LiteLLM Integration** — unify calling format for Groq (Llama 3.3 70B) and Google API (Gemini 2.5 Flash).
2. **Tool Registry** (`backend/app/agent/tools.py`) — define 3 callable tools with explicit input/output schemas and firing restrictions:
   - `CALCULATE` — input: expression string; output: numeric result. *Fires only when query contains numeric keywords (revenue, margin, ratio, growth, etc.)*
   - `LOOKUP` — input: entity + attribute; output: retrieved chunk text. *Always available.*
   - `COMPARE` — input: two entity/period pairs; output: side-by-side numeric delta. *Fires only when query references two companies or two fiscal periods.*
3. **Few-Shot Examples** (`backend/eval/few_shot_examples.json`):
   - 20+ examples; injection targets must be explicit: Planner prompt gets query decomposition examples, Critic prompt gets grounding verification examples.
   - Run cosine similarity deduplication against `evaluation_set.json` (threshold < 0.85) before submission to prevent leakage.

---

### Phase 4: Planner-Executor-Critic Agent Pipeline

1. **LangGraph StateGraph** (`backend/app/agent/pipeline.py`) with the following nodes:
   - **RefusalGuard** — pre-flight check blocking investment advice, price targets, and future predictions. Returns structured refusal with reason.
   - **Planner** — LLM decomposes query into an ordered list of tool calls. On Critic failure, rewrites search sub-queries and re-enters Executor.
   - **Executor** — executes tool calls in plan order; collects results and draft context.
   - **Critic** — evaluates draft response:
     - *Numerical Guardrail:* every number in the draft must exactly match the cited chunk. Mismatch → repair loop.
     - *Citation Completeness:* every factual claim must map to a `chunk_id`. Missing citation → repair.
     - Max 2 repair iterations before returning a low-confidence flagged response.
2. **Repair Cycle:** Critic → Planner (rewrites queries) → Executor → Critic.

**Agent State fields:** `query`, `plan`, `tool_results`, `draft_response`, `citations`, `critic_verdict`, `repair_count`, `refusal`, `memory_context`, `session_id`, `model_used`, `latency_ms`

---

### Phase 5: Memory System & Structured Logging

1. **Memory Architecture** (`backend/app/agent/memory.py`):
   - **Write** — after every turn, write query + response + key entities to `memory_summaries`.
   - **Summarize** — `MemorySummarizer` node triggers every 5 turns; calls LLM to compress into a 150-word summary written back to `memory_summaries`.
   - **Retrieve** — at the start of each Planner call, fetch the most recent summary + last 2 raw turns and inject as `memory_context` into the Planner prompt.
2. **LangGraph Checkpointing** — use `SqliteSaver` or `PostgresSaver` for in-session state continuity. This is separate from the summarizer: checkpointing handles within-session reconnects; the summarizer handles long-horizon cross-session context.
3. **Structured Logging** (`backend/app/logging.py`) — emit a JSON log entry per request containing: `session_id`, `query`, `model_used`, plan steps, tool names + inputs/outputs, `chunk_ids` retrieved, refusal decision, `critic_verdict`, `repair_count`, `total_latency_ms`. Persist to Postgres as the system of record.

---

### Phase 6: Frontend Web Application

1. **React App Setup** (`frontend/`) with Tailwind CSS.
2. **API Integration** (`frontend/src/services/api.js`) — Axios client for `/query`, `/history`, `/evaluate`.
3. **Core Components:**
   - `QueryInput` — company selector, question textarea. Validation uses inline messages instead of window alerts.
   - `AnswerDisplay` — tabbed/grid view showing model responses side-by-side with confidence scores, refusal badges, and repair count
   - `CitationList` — expandable source text cards showing grounding chunk text
   - `SessionContext` — sidebar showing current memory summary and recent turn list (satisfies "session state in UI" requirement)
   - `AgentTrace` — collapsible panel showing Planner steps, tool calls, Critic verdict, and repair iterations
4. **Custom Hooks:** `useQuery` (loading/error/history), `useSession` (session_id + memory context display with `turns` array).

---

### Phase 7: Evaluation, Dockerization & Deployment

1. **Evaluation Framework** (`backend/eval/`):
   - Expand to 100+ test cases across categories: factual_lookup (40), numerical_calculation (20), multi_hop_reasoning (15), cross_document (10), refusal_investment_advice (10), refusal_future_prediction (5)
   - `few_shot_examples.json` (20+) — deduplicated against eval set; injection targets specified
   - Ragas integration: compute **Faithfulness** and **Answer Relevancy** per model per test case; log to Postgres
2. **`/evaluate` Endpoint** — runs the full eval set on demand and returns Ragas scores; surfaced in the React UI for live demo.
3. **Dockerization:**
   - `Dockerfile` for backend (Python 3.11 slim)
   - `Dockerfile` for frontend (Node build + Nginx)
   - `docker-compose.yml` wiring Postgres, ChromaDB, Backend, Frontend with health checks
4. **Cloud Deployment** — Railway or Render; environment variables documented in `.env.example`.

---

## 5. Non-Negotiable Compliance Checklist

- [ ] Multi-model evaluation across 2 models (Llama 3.3 70B Versatile and Gemini 2.5 Flash)
- [ ] Planner-Executor-Critic agent loop implemented in LangGraph and demonstrable via `AgentTrace` UI
- [ ] Hybrid retrieval (Dense + Sparse + RRF fusion) implemented
- [ ] Refusal logic for investment advice and future predictions implemented
- [ ] Citation grounding verification (Critic numerical guardrail) with repair loop implemented
- [ ] 3 distinct tools (`CALCULATE`, `LOOKUP`, `COMPARE`) with schemas and firing restrictions
- [ ] Memory: write (every turn) + summarize (every 5 turns via LLM) + retrieve (injected into Planner)
- [ ] `MemorySummarizer` node distinct from LangGraph checkpointing
- [ ] Structured logging persisted to Postgres per request
- [ ] `SessionContext` component in UI displays live memory summary
- [ ] `memory_summaries` table in schema alongside documents, chunks, queries, responses, citations
- [ ] Evaluation set expanded to 100+ test cases across 6 categories
- [ ] `few_shot_examples.json` deduplicated against eval set; injection targets specified
- [ ] Ragas Faithfulness and Answer Relevancy computed per model
- [ ] `/evaluate` endpoint returning live scores
- [ ] Full-stack application containerized via Docker + docker-compose
- [ ] Deployed to Railway/Render with `.env.example` documented

---

## 6. Known Risks & Mitigations

| Risk | Mitigation |
|---|---|
| RAM pressure | Move to cloud APIs (Groq and Gemini) instead of running local models |
| LangGraph repair loop latency | Cap iterations at 2; return low-confidence flagged response if exceeded |
| Gemini 2.5 Flash API quota during eval runs | Cache Gemini responses by query hash in Postgres |
| `all-MiniLM-L6-v2` domain gap on financial text | Acknowledge in report; compare retrieval hit-rate vs. FinBERT as an evaluation data point |
| Few-shot / eval set leakage | Cosine similarity check (threshold < 0.85) before submission |