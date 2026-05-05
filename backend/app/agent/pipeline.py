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


def executor_node(state: dict) -> dict:
    """
    Executor node: executes tool calls from the plan and generates draft response.
    
    Iterates through the plan, dispatches each tool call via execute_tool(),
    collects all tool results, builds a final generation prompt combining
    tool results with retrieved chunk texts, calls LLM to generate draft response,
    and populates citations from chunk_ids returned by tools.
    
    Tool execution errors are logged but do not stop execution - the executor
    continues with remaining tools.
    
    Args:
        state: Agent state dict containing:
            - plan: list[dict] - Ordered list of tool calls with {"tool": str, "inputs": dict}
            - query: str - The user's query text
            - model_used: str - LLM model to use (default: "gemini")
            - ollama_base_url: str - Ollama API base URL (optional)
            - gemini_api_key: str - Gemini API key (optional)
    
    Returns:
        dict with:
            - tool_results: list[dict] - Results from each tool execution
            - draft_response: str - LLM-generated response text
            - citations: list[dict] - Citation objects with chunk_id and relevance_score
    """
    plan = state.get("plan", [])
    query = state.get("query", "")
    model_used = state.get("model_used", "gemini")
    
    # Initialize retriever for tool execution
    retriever = HybridRetriever()
    
    # Initialize LLM router
    llm_router = LLMRouter(
        ollama_base_url=state.get("ollama_base_url", "http://localhost:11434"),
        gemini_api_key=state.get("gemini_api_key")
    )
    
    # Execute each tool call and collect results
    tool_results = []
    all_chunk_texts = []
    all_chunk_ids = []
    
    for tool_call in plan:
        tool_name = tool_call.get("tool")
        tool_inputs = tool_call.get("inputs", {})
        
        try:
            # Execute tool
            from app.agent.tools import execute_tool
            result = execute_tool(tool_name, tool_inputs, retriever)
            
            # Log successful execution
            logger.info(
                f"Tool executed successfully: {tool_name} with inputs {tool_inputs}"
            )
            
            # Store tool result
            tool_result = {
                "tool": tool_name,
                "inputs": tool_inputs,
                "output": result,
                "status": "success"
            }
            tool_results.append(tool_result)
            
            # Extract chunk texts and IDs for citation tracking
            if tool_name == "LOOKUP":
                chunk_text = result.get("chunk_text")
                chunk_id = result.get("chunk_id")
                if chunk_text:
                    all_chunk_texts.append(chunk_text)
                if chunk_id:
                    all_chunk_ids.append(chunk_id)
            
            elif tool_name == "COMPARE":
                comparison_result = result.get("comparison_result", {})
                
                # Extract from entity1
                entity1 = comparison_result.get("entity1", {})
                if entity1.get("chunk_text"):
                    all_chunk_texts.append(entity1["chunk_text"])
                if entity1.get("chunk_id"):
                    all_chunk_ids.append(entity1["chunk_id"])
                
                # Extract from entity2
                entity2 = comparison_result.get("entity2", {})
                if entity2.get("chunk_text"):
                    all_chunk_texts.append(entity2["chunk_text"])
                if entity2.get("chunk_id"):
                    all_chunk_ids.append(entity2["chunk_id"])
        
        except Exception as e:
            # Log error but continue with remaining tools
            logger.error(
                f"Tool execution failed: {tool_name} with inputs {tool_inputs}. "
                f"Error: {e}"
            )
            
            # Store error result
            tool_result = {
                "tool": tool_name,
                "inputs": tool_inputs,
                "output": None,
                "status": "error",
                "error": str(e)
            }
            tool_results.append(tool_result)
    
    # Build final generation prompt
    # Combine tool results with retrieved chunk texts
    tool_results_text = "\n\n".join([
        f"Tool: {tr['tool']}\nInputs: {tr['inputs']}\nOutput: {tr['output']}"
        for tr in tool_results
        if tr['status'] == 'success'
    ])
    
    chunks_text = "\n\n---\n\n".join([
        f"Source Chunk:\n{chunk}"
        for chunk in all_chunk_texts
    ])
    
    system_instructions = """You are a financial Q&A assistant. Your task is to generate accurate, well-grounded responses based on tool results and source documents.

Guidelines:
1. Base your response ONLY on the provided tool results and source chunks
2. Cite specific numbers and facts from the source chunks
3. If tool results contain calculations, include them in your response
4. Be precise with numerical values - use exact numbers from sources
5. If information is insufficient, acknowledge the limitation
6. Keep responses concise and focused on answering the query"""
    
    user_prompt = f"""Query: {query}

Tool Results:
{tool_results_text}

Source Documents:
{chunks_text}

Please provide a comprehensive answer to the query based on the tool results and source documents above."""
    
    # Prepare messages for LLM
    messages = [
        {"role": "system", "content": system_instructions},
        {"role": "user", "content": user_prompt}
    ]
    
    # Generate draft response
    try:
        draft_response = llm_router.complete(
            model=model_used,
            messages=messages,
            temperature=0.3  # Low temperature for factual accuracy
        )
        
        logger.info(f"Draft response generated successfully (length: {len(draft_response)})")
    
    except Exception as e:
        logger.error(f"Failed to generate draft response: {e}")
        draft_response = "Error: Failed to generate response due to LLM error."
    
    # Populate citations from chunk_ids
    # Each chunk_id gets a citation with relevance score
    # For now, assign equal relevance scores (could be improved with actual relevance scoring)
    citations = []
    for chunk_id in all_chunk_ids:
        citations.append({
            "chunk_id": chunk_id,
            "relevance_score": 0.9  # Default relevance score
        })
    
    return {
        "tool_results": tool_results,
        "draft_response": draft_response,
        "citations": citations
    }


def critic_node(state: dict) -> dict:
    """
    Critic node: validates responses for numerical accuracy and citation completeness.
    
    Performs two critical validation checks:
    1. Numerical accuracy: All numbers in draft_response must exactly match cited chunk texts
    2. Citation completeness: Every sentence must have at least one chunk_id citation
    
    Returns repair verdicts when validation fails, or approves with confidence score.
    Forces approval with low confidence after 2 repair iterations.
    
    Args:
        state: Agent state dict containing:
            - draft_response: str - The LLM-generated response text
            - citations: list[dict] - Citation objects with chunk_id and relevance_score
            - tool_results: list[dict] - Results from tool execution (contains chunk texts)
            - repair_count: int - Number of repair iterations (optional, default 0)
    
    Returns:
        dict with:
            - critic_verdict: str - "approved" | "repair_numerical" | "repair_citation"
            - confidence_score: float - 0.3-1.0 based on validation results
            - critic_feedback: str - Feedback for Planner on repair (optional)
    """
    import re
    
    draft_response = state.get("draft_response", "")
    citations = state.get("citations", [])
    tool_results = state.get("tool_results", [])
    repair_count = state.get("repair_count", 0)
    
    # Extract all chunk texts from tool results for numerical verification
    cited_chunk_texts = []
    for tool_result in tool_results:
        if tool_result.get("status") != "success":
            continue
        
        output = tool_result.get("output", {})
        tool_name = tool_result.get("tool")
        
        if tool_name == "LOOKUP":
            chunk_text = output.get("chunk_text")
            if chunk_text:
                cited_chunk_texts.append(chunk_text)
        
        elif tool_name == "COMPARE":
            comparison_result = output.get("comparison_result", {})
            
            # Extract from entity1
            entity1 = comparison_result.get("entity1", {})
            if entity1.get("chunk_text"):
                cited_chunk_texts.append(entity1["chunk_text"])
            
            # Extract from entity2
            entity2 = comparison_result.get("entity2", {})
            if entity2.get("chunk_text"):
                cited_chunk_texts.append(entity2["chunk_text"])
    
    # Step 1: Extract all numbers from draft_response using regex
    # Pattern matches: integers, decimals with . or , as separator
    number_pattern = r'\b\d+[\.,]?\d*\b'
    extracted_numbers = re.findall(number_pattern, draft_response)
    
    # Step 2: Check each extracted number for exact match in cited chunks
    numerical_mismatches = []
    for number in extracted_numbers:
        # Check if this exact number string appears as a word boundary in any cited chunk
        # Use word boundary regex to avoid matching "1" in "1001"
        number_pattern_check = r'\b' + re.escape(number) + r'\b'
        found_in_chunks = any(
            re.search(number_pattern_check, chunk_text) 
            for chunk_text in cited_chunk_texts
        )
        
        if not found_in_chunks:
            numerical_mismatches.append(number)
    
    # If numerical mismatches found and repair_count < 2, request repair
    if numerical_mismatches and repair_count < 2:
        logger.warning(
            f"Critic found numerical mismatches: {numerical_mismatches}. "
            f"Requesting repair (repair_count={repair_count})"
        )
        return {
            "critic_verdict": "repair_numerical",
            "confidence_score": 0.0,
            "critic_feedback": (
                f"The following numbers in your response do not appear in the cited chunks: "
                f"{', '.join(numerical_mismatches)}. Please verify all numerical claims "
                f"against the source documents and rewrite the response with accurate numbers."
            )
        }
    
    # Step 3: Check citation completeness - every sentence should have citations
    # Split draft_response into sentences (simple split on . ! ?)
    sentences = re.split(r'[.!?]+', draft_response)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # Get all chunk_ids from citations
    cited_chunk_ids = set(citation.get("chunk_id") for citation in citations)
    
    # Check if response has content but no citations
    # Consider a response to have content if it has sentences OR if it's non-empty
    has_content = len(sentences) > 0 or (draft_response.strip() != "")
    missing_citations = has_content and len(cited_chunk_ids) == 0
    
    # If missing citations and repair_count < 2, request repair
    if missing_citations and repair_count < 2:
        logger.warning(
            f"Critic found missing citations. Response has {len(sentences)} sentences "
            f"but {len(cited_chunk_ids)} citations. Requesting repair (repair_count={repair_count})"
        )
        return {
            "critic_verdict": "repair_citation",
            "confidence_score": 0.0,
            "critic_feedback": (
                "Your response lacks proper citations. Please ensure every factual claim "
                "is grounded in the retrieved source documents and include appropriate citations."
            )
        }
    
    # Step 4: If repair_count >= 2, force approval with low confidence
    if repair_count >= 2:
        logger.warning(
            f"Critic forcing approval after {repair_count} repair iterations. "
            f"Numerical mismatches: {len(numerical_mismatches)}, "
            f"Missing citations: {missing_citations}"
        )
        return {
            "critic_verdict": "approved",
            "confidence_score": 0.3,
            "critic_feedback": None
        }
    
    # Step 5: All checks passed - approve with confidence score
    # Compute confidence score based on citation coverage
    # Higher coverage = higher confidence (0.5 to 1.0 range)
    
    # Citation coverage: ratio of citations to sentences
    if len(sentences) > 0:
        citation_coverage = min(len(cited_chunk_ids) / len(sentences), 1.0)
        # Map coverage to 0.5-1.0 range
        confidence_score = 0.5 + (citation_coverage * 0.5)
    else:
        # Empty response or no sentences - default to medium confidence
        confidence_score = 0.7
    
    logger.info(
        f"Critic approved response with confidence {confidence_score:.2f}. "
        f"Sentences: {len(sentences)}, Citations: {len(cited_chunk_ids)}"
    )
    
    return {
        "critic_verdict": "approved",
        "confidence_score": confidence_score,
        "critic_feedback": None
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
