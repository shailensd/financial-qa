from app.ml.hybrid_retrieval import HybridRetriever


class PlannerExecutorCriticPipeline:
    """Checkpoint skeleton of Planner-Executor-Critic architecture."""

    def __init__(self) -> None:
        self.retriever = HybridRetriever()

    def plan(self, question: str) -> list[str]:
        return [
            "Check refusal policy",
            "Retrieve evidence chunks",
            "Generate draft answer",
            "Critic verifies grounding",
        ]

    def execute(self, question: str, company: str) -> dict:
        chunks = self.retriever.retrieve(question=question, company=company, top_k=5)
        return {
            "tool_calls": [
                {"tool": "hybrid_retrieval", "status": "ok", "result_count": len(chunks)}
            ],
            "chunks": chunks,
        }

    def critic(self, execution_output: dict) -> dict:
        return {
            "grounding_check": "pending-full-implementation",
            "passed": True,
            "comments": "Checkpoint stub only; citation verification will be added next.",
            "tool_calls_logged": execution_output.get("tool_calls", []),
        }

    def run(self, question: str, company: str) -> dict:
        plan_steps = self.plan(question)
        execution_output = self.execute(question=question, company=company)
        critic_output = self.critic(execution_output)
        return {
            "plan": plan_steps,
            "execution": execution_output,
            "critic": critic_output,
        }
