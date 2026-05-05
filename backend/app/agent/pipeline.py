import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from app.ml.hybrid_retrieval import HybridRetriever
from app.ml.llm_router import LLMRouter
from app.agent.tools import get_available_tools


logger = logging.getLogger(__name__)


# RefusalGuard keyword lists
INVESTMENT_KEYWORDS = ["buy", "sell", "invest", "recommend", "portfolio", "stock pick"]
PREDICTION_KEYWORDS = ["will", "predict", "forecast", "next quarter", "next year", "price target"]


# Load few-shot examples at module level
FEW_SHOT_EXAMPLES_PATH = Path(__file__).parent.parent.parent / "eval" / "few_shot_examples.json"
_few_shot_examples_cache = None


def _load_few_shot_examples() -> List[Dict[str, Any]]:
    """
    Load few-shot examples from JSON file, filtering for planner injection target.
    
    Returns:
        List of few-shot examples with injection_target="planner"
    """
    global _few_shot_examples_cache
    
    if _few_shot_examples_cache is not None:
        return _few_shot_examples_cache
    
    try:
        with open(FEW_SHOT_EXAMPLES_PATH, 'r') as f:
            all_examples = json.load(f)
        
        # Filter for planner examples only
        planner_examples = [
            ex for ex in all_examples 
            if ex.get("injection_target") == "planner"
        ]
        
        _few_shot_examples_cache = planner_examples
        logger.info(f"Loaded {len(planner_examples)} planner few-shot examples")
        return planner_examples
    
    except Exception as e:
        logger.error(f"Failed to load few-shot examples: {e}")
        return []


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


def planner_node(state: dict) -> dict:
    """
    Planner node: decomposes queries into ordered tool calls.
    
    Builds a prompt with system instructions, memory context, few-shot examples,
    and the user query. Calls LLM to generate a plan as a JSON list of tool calls.
    Filters tool calls against firing restrictions and handles repair feedback.
    
    Args:
        state: Agent state dict containing:
            - query: str - The user's query text
            - memory_context: str - Session memory context (optional)
            - critic_feedback: str - Feedback from Critic for repair (optional)
            - repair_count: int - Number of repair iterations (optional)
            - model_used: str - LLM model to use (default: "gemini")
    
    Returns:
        dict with:
            - plan: list[dict] - Ordered list of tool calls with {"tool": str, "inputs": dict}
    """
    query = state.get("query", "")
    memory_context = state.get("memory_context", "")
    critic_feedback = state.get("critic_feedback", "")
    repair_count = state.get("repair_count", 0)
    model_used = state.get("model_used", "gemini")
    
    # Load few-shot examples
    few_shot_examples = _load_few_shot_examples()
    
    # Build system instructions
    system_instructions = """You are a financial query planner. Your task is to decompose user queries into ordered tool calls.

Available tools:
1. LOOKUP - Retrieve information about an entity's attribute
   Input: {"entity": str, "attribute": str}
   Use when: Always available for any factual lookup

2. CALCULATE - Evaluate a mathematical expression
   Input: {"expression": str}
   Use when: Query contains numeric keywords (revenue, margin, ratio, growth, percent, dollar, million, billion, eps, ebitda)

3. COMPARE - Compare two entities or time periods
   Input: {"entity1": str, "period1": str, "entity2": str, "period2": str}
   Use when: Query references 2 companies OR 2 fiscal periods

Your response must be a valid JSON array of tool calls in execution order.
Each tool call must have: {"tool": "TOOL_NAME", "inputs": {...}}

Example format:
[
  {"tool": "LOOKUP", "inputs": {"entity": "Apple", "attribute": "revenue FY2023"}},
  {"tool": "CALCULATE", "inputs": {"expression": "revenue_2023 - revenue_2022"}}
]"""
    
    # Build few-shot examples section
    few_shot_section = "\n\nExamples of query decomposition:\n"
    for example in few_shot_examples[:8]:  # Use first 8 examples to avoid context bloat
        few_shot_section += f"\nQuery: {example['query']}\n"
        few_shot_section += f"Plan: {json.dumps(example['expected_plan'])}\n"
    
    # Build memory context section
    memory_section = ""
    if memory_context:
        memory_section = f"\n\nSession Context:\n{memory_context}\n"
    
    # Build repair feedback section
    repair_section = ""
    if critic_feedback and repair_count > 0:
        repair_section = f"\n\nCritic Feedback (Repair Iteration {repair_count}):\n{critic_feedback}\n"
        repair_section += "Please rewrite the search sub-queries to address the feedback above.\n"
    
    # Build user prompt
    user_prompt = f"{memory_section}{few_shot_section}{repair_section}\nQuery: {query}\n\nPlan:"
    
    # Prepare messages for LLM
    messages = [
        {"role": "system", "content": system_instructions},
        {"role": "user", "content": user_prompt}
    ]
    
    # Call LLM
    try:
        llm_router = LLMRouter(
            ollama_base_url=state.get("ollama_base_url", "http://localhost:11434"),
            gemini_api_key=state.get("gemini_api_key")
        )
        
        response_text = llm_router.complete(
            model=model_used,
            messages=messages,
            temperature=0.0  # Deterministic planning
        )
        
        # Parse JSON response
        # Handle cases where LLM wraps JSON in markdown code blocks
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        plan = json.loads(response_text)
        
        # Validate plan is a list
        if not isinstance(plan, list):
            logger.error(f"LLM returned non-list plan: {plan}")
            plan = []
        
        # Filter tool calls against firing restrictions
        available_tools = get_available_tools(query)
        filtered_plan = []
        
        for tool_call in plan:
            if not isinstance(tool_call, dict):
                logger.warning(f"Skipping invalid tool call (not a dict): {tool_call}")
                continue
            
            tool_name = tool_call.get("tool")
            if tool_name not in available_tools:
                logger.warning(
                    f"Skipping tool {tool_name} - not available for query. "
                    f"Available tools: {available_tools}"
                )
                continue
            
            # Validate tool call has inputs
            if "inputs" not in tool_call:
                logger.warning(f"Skipping tool call without inputs: {tool_call}")
                continue
            
            filtered_plan.append(tool_call)
        
        logger.info(
            f"Planner generated {len(plan)} tool calls, "
            f"{len(filtered_plan)} passed firing restrictions"
        )
        
        return {"plan": filtered_plan}
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}\nResponse: {response_text}")
        return {"plan": []}
    
    except Exception as e:
        logger.error(f"Planner node failed: {e}")
        return {"plan": []}


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
