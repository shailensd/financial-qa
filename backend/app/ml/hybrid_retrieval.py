from typing import Any


class HybridRetriever:
    """Checkpoint stub for dense+sparse retrieval fusion."""

    def retrieve(self, question: str, company: str, top_k: int = 5) -> list[dict[str, Any]]:
        # Placeholder results to validate API and pipeline wiring.
        return [
            {
                "chunk_id": "stub-1",
                "company": company,
                "score": 0.0,
                "text": f"Stub retrieval result for question: {question}",
            }
        ]
