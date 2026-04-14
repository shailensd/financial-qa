# FinDoc Intelligence - Multi-Model Financial Q&A with Citation Verification

## Checkpoint Submission Info
- Team ID: TEAM_ID_HERE
- Project Title: FinDoc Intelligence - Multi-Model Financial Q&A with Citation Verification
- Repository: REPO_LINK_HERE

## Team Members
- Member 1: NAME (Role: Backend + Agent)
- Member 2: NAME (Role: Retrieval + Evaluation)
- Member 3: NAME (Role: Frontend + Integration)

## Problem Statement
Financial analysts spend significant time reading long SEC filings (10-K, 10-Q). Generic LLM systems can hallucinate numbers and unsupported claims. This project builds a domain-specific, evaluation-first AI assistant that answers financial questions with citations and refusal guardrails for out-of-scope prompts.

## Dataset
### Primary Corpus
- Source: SEC EDGAR public filings
- Target companies: AAPL, MSFT, GOOGL, AMZN, TSLA
- Document types: 10-K and 10-Q
- Time range: 2022-2024

### Evaluation Data
- Seed file: `backend/eval/evaluation_set_seed.json`
- Final goal: 100+ test cases
- Categories:
  - factual lookup
  - multi-hop comparison
  - calculation
  - refusal (future prediction)
  - refusal (investment advice)

## Technical Approach
### Core Pipeline
1. Input validation and refusal policy check
2. Hybrid retrieval (dense + sparse)
3. Context assembly
4. LLM generation (multi-model)
5. Citation verification
6. Return answer or refusal

### Models (planned)
- Open-source primary: Llama 3.1 8B Instruct (or Mistral 7B)
- Open-source comparator: Gemma 2 9B (or Mistral)
- Commercial comparator: Gemini

### Required Agent Capability
- Planner-Executor-Critic architecture
- Tool usage (calculator + retrieval utility)
- Structured logging of tool calls and outputs
- Stateful memory (write/summarize/retrieve)

## Current Implementation Progress (Checkpoint)
- [x] Repository initialized
- [x] Backend app skeleton created
- [x] Health endpoint implemented
- [x] Query endpoint stub implemented
- [x] Hybrid retrieval module stub created
- [x] Agent pipeline (Planner-Executor-Critic) stub created
- [x] Evaluation seed dataset added
- [ ] Full ingestion of SEC filings
- [ ] Full retrieval + model integration
- [ ] UI integration
- [ ] End-to-end evaluation run

## Next Steps (1-2 Weeks)
1. Implement document ingestion and chunking pipeline
2. Build dense + sparse retrieval and fusion
3. Add first runnable open-source model integration
4. Expand evaluation set from seed to 50+, then 100+
5. Add citation verification and refusal evaluation

## Repository Structure
```
backend/
  app/
    main.py
    ml/
      hybrid_retrieval.py
    agent/
      pipeline.py
  eval/
    evaluation_set_seed.json
  requirements.txt
README.md
```

## How to Run (Current Starter)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open API docs:
- http://127.0.0.1:8000/docs

## Checkpoint Notes
This repository includes initial implementation code (not README-only), along with a seeded evaluation artifact and modular project structure to support full implementation in upcoming milestones.
