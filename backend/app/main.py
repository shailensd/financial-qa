from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.agent.pipeline import PlannerExecutorCriticPipeline


app = FastAPI(title="FinDoc Intelligence API")
pipeline = PlannerExecutorCriticPipeline()


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    company: str = Field(min_length=1, max_length=10)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "findoc-backend"}


@app.post("/query")
def run_query(payload: QueryRequest) -> dict:
    # Initial checkpoint implementation: orchestration stub.
    result = pipeline.run(question=payload.question, company=payload.company)
    return {
        "question": payload.question,
        "company": payload.company,
        "result": result,
        "note": "Initial checkpoint stub. Retrieval and model providers will be added incrementally.",
    }
