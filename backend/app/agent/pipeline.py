from app.ml.hybrid_retrieval import HybridRetriever


# RefusalGuard keyword lists
INVESTMENT_KEYWORDS = ["buy", "sell", "invest", "recommend", "portfolio", "stock pick"]
PREDICTION_KEYWORDS = ["will", "predict", "forecast", "next quarter", "next year", "price target"]


def refusal_guard_node(state: dict) -> dict:
    """
    RefusalGuard node: checks query against prohibited keyword lists.
    
    Blocks investment advice queries and future prediction queries before
    they reach the Planner node.
    
    Args:
        state: Agent state dict containing at minimum:
            - query: str - The user's query text
    
    Returns:
        dict with refusal status:
            - refusal: bool - True if query should be refused
            - refusal_reason: str | None - Reason for refusal
    """
    query = state.get("query", "").lower()
    
    # Check for investment advice keywords
    for keyword in INVESTMENT_KEYWORDS:
        if keyword in query:
            return {
                "refusal": True,
                "refusal_reason": "investment_advice_prohibited"
            }
    
    # Check for future prediction keywords
    for keyword in PREDICTION_KEYWORDS:
        if keyword in query:
            return {
                "refusal": True,
                "refusal_reason": "future_prediction_prohibited"
            }
    
    # Query is allowed
    return {
        "refusal": False,
        "refusal_reason": None
    }


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
