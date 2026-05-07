"""
Tool Registry for FinDoc Intelligence Agent.

This module defines the tool registry with input/output schemas, firing conditions,
and execution logic for CALCULATE, LOOKUP, and COMPARE tools.
"""

import re
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.hybrid_retrieval import HybridRetriever


logger = logging.getLogger(__name__)


# Tool Registry with schemas and firing conditions
TOOLS = {
    "CALCULATE": {
        "input_schema": {
            "expression": str
        },
        "output_schema": {
            "result": float
        },
        "firing_condition": "query contains numeric keywords",
        "numeric_keywords": [
            "revenue", "margin", "ratio", "growth", "percent",
            "dollar", "million", "billion", "eps", "ebitda"
        ]
    },
    "LOOKUP": {
        "input_schema": {
            "entity": str,
            "attribute": str
        },
        "output_schema": {
            "chunk_text": str,
            "chunk_id": int
        },
        "firing_condition": "always available"
    },
    "COMPARE": {
        "input_schema": {
            "entity1": str,
            "period1": str,
            "entity2": str,
            "period2": str
        },
        "output_schema": {
            "comparison_result": dict
        },
        "firing_condition": "query references 2 companies OR 2 fiscal periods"
    }
}


def validate_tool_inputs(tool_name: str, inputs: Dict[str, Any]) -> None:
    """
    Validate tool inputs against the tool's input schema.
    
    Args:
        tool_name: Name of the tool (CALCULATE, LOOKUP, COMPARE)
        inputs: Dictionary of input parameters
    
    Raises:
        ValueError: If inputs don't match the schema
    """
    if tool_name not in TOOLS:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    schema = TOOLS[tool_name]["input_schema"]
    
    # Check all required fields are present
    for field_name, field_type in schema.items():
        if field_name not in inputs:
            raise ValueError(
                f"Missing required field '{field_name}' for tool {tool_name}"
            )
        
        # Validate type
        if not isinstance(inputs[field_name], field_type):
            raise ValueError(
                f"Field '{field_name}' for tool {tool_name} must be of type {field_type.__name__}, "
                f"got {type(inputs[field_name]).__name__}"
            )
    
    # Check for unexpected fields
    unexpected_fields = set(inputs.keys()) - set(schema.keys())
    if unexpected_fields:
        raise ValueError(
            f"Unexpected fields for tool {tool_name}: {unexpected_fields}"
        )


def get_available_tools(query: str) -> List[str]:
    """
    Determine which tools are available based on query content and firing restrictions.
    
    Firing conditions:
    - CALCULATE: fires when query contains numeric keywords
    - LOOKUP: always available
    - COMPARE: fires when query references 2 companies OR 2 fiscal periods
    
    Args:
        query: User query text
    
    Returns:
        List of available tool names
    """
    available_tools = []
    query_lower = query.lower()
    
    # LOOKUP is always available
    available_tools.append("LOOKUP")
    
    # CALCULATE: check for numeric keywords
    numeric_keywords = TOOLS["CALCULATE"]["numeric_keywords"]
    if any(keyword in query_lower for keyword in numeric_keywords):
        available_tools.append("CALCULATE")
    
    # COMPARE: check for two companies or two fiscal periods
    # Pattern for fiscal years: FY followed by 2 or 4 digits, or just 4-digit years
    fiscal_year_pattern = r'\b(?:FY\s*)?(?:20\d{2}|19\d{2}|\d{2})\b'
    fiscal_years = re.findall(fiscal_year_pattern, query, re.IGNORECASE)
    
    # Pattern for company names (simplified - looks for capitalized words or common company indicators)
    # This is a heuristic; in production, you'd use NER or a company name database
    company_indicators = ['inc', 'corp', 'corporation', 'company', 'ltd', 'llc']
    
    # Count potential company mentions (capitalized words that might be companies)
    # or explicit company indicators
    words = query.split()
    potential_companies = []
    for i, word in enumerate(words):
        # Check if word starts with capital letter (potential company name)
        if word and word[0].isupper() and len(word) > 1:
            potential_companies.append(word)
        # Check for company indicators
        if word.lower() in company_indicators:
            potential_companies.append(word)
    
    # Also check for common comparison words that suggest comparison
    comparison_words = ['compare', 'versus', 'vs', 'vs.', 'compared to', 'difference between']
    has_comparison_intent = any(comp_word in query_lower for comp_word in comparison_words)
    
    # Fire COMPARE if we detect 2+ fiscal years OR 2+ companies OR comparison intent with entities
    if len(fiscal_years) >= 2 or len(set(potential_companies)) >= 2 or (has_comparison_intent and len(potential_companies) >= 1):
        available_tools.append("COMPARE")
    
    return available_tools


def _execute_calculate(inputs: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute CALCULATE tool: evaluate mathematical expression safely.
    
    Uses Python eval() with a restricted namespace containing only math operations.
    No builtins are available to prevent code injection.
    
    Can optionally accept a context dictionary containing variables extracted from
    previous tool results (e.g., numbers from LOOKUP results).
    
    Args:
        inputs: Dictionary with 'expression' key
        context: Optional dictionary of variables to make available in the expression
    
    Returns:
        Dictionary with 'result' key containing float result
    
    Raises:
        ValueError: If expression is invalid or evaluation fails
    """
    expression = inputs["expression"]
    
    # Create safe namespace with only math operations
    # No builtins, no imports, only basic math
    safe_namespace = {
        "__builtins__": {},
        # Math operations
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
        # Allow basic arithmetic operators (handled by Python syntax)
    }
    
    # Create local namespace with context variables (if provided)
    local_namespace = {}
    if context:
        # Only allow numeric values in context to prevent code injection
        for key, value in context.items():
            if isinstance(value, (int, float)):
                local_namespace[key] = value
            else:
                logger.warning(f"Skipping non-numeric context variable: {key}={value}")
    
    try:
        # Evaluate expression in safe namespace with context variables
        result = eval(expression, safe_namespace, local_namespace)
        
        # Convert result to float
        result_float = float(result)
        
        return {"result": result_float}
    
    except Exception as e:
        logger.error(f"CALCULATE tool failed for expression '{expression}': {e}")
        raise ValueError(f"Failed to evaluate expression: {e}")


def _execute_lookup(
    inputs: Dict[str, Any],
    retriever: HybridRetriever,
    db: Optional[AsyncSession] = None
) -> Dict[str, Any]:
    """
    Execute LOOKUP tool: retrieve relevant chunk for entity/attribute query.
    
    Calls HybridRetriever.retrieve() and returns the top chunk.
    
    Args:
        inputs: Dictionary with 'entity' and 'attribute' keys
        retriever: HybridRetriever instance
        db: Database session (optional, not used currently)
    
    Returns:
        Dictionary with 'chunk_text' and 'chunk_id' keys
    
    Raises:
        ValueError: If retrieval fails or no chunks found
    """
    entity = inputs["entity"]
    attribute = inputs["attribute"]
    
    # Build query from entity and attribute
    query = f"{entity} {attribute}"
    
    try:
        # Retrieve chunks using hybrid retrieval
        chunks = retriever.retrieve(query, top_k=1)
        
        if not chunks:
            raise ValueError(f"No chunks found for query: {query}")
        
        # Return top chunk
        top_chunk = chunks[0]
        return {
            "chunk_text": top_chunk.chunk_text,
            "chunk_id": top_chunk.chunk_id
        }
    
    except Exception as e:
        logger.error(f"LOOKUP tool failed for entity='{entity}', attribute='{attribute}': {e}")
        raise ValueError(f"Failed to retrieve chunks: {e}")


def _execute_compare(
    inputs: Dict[str, Any],
    retriever: HybridRetriever,
    db: Optional[AsyncSession] = None
) -> Dict[str, Any]:
    """
    Execute COMPARE tool: compare two entities/periods.
    
    Calls LOOKUP for both entity/period pairs, extracts numeric values,
    and computes delta.
    
    Args:
        inputs: Dictionary with 'entity1', 'period1', 'entity2', 'period2' keys
        retriever: HybridRetriever instance
        db: Database session (optional, not used currently)
    
    Returns:
        Dictionary with 'comparison_result' containing both lookups and delta
    
    Raises:
        ValueError: If lookup or comparison fails
    """
    entity1 = inputs["entity1"]
    period1 = inputs["period1"]
    entity2 = inputs["entity2"]
    period2 = inputs["period2"]
    
    try:
        # Lookup first entity/period
        query1 = f"{entity1} {period1}"
        chunks1 = retriever.retrieve(query1, top_k=1)
        
        if not chunks1:
            raise ValueError(f"No chunks found for {entity1} {period1}")
        
        # Lookup second entity/period
        query2 = f"{entity2} {period2}"
        chunks2 = retriever.retrieve(query2, top_k=1)
        
        if not chunks2:
            raise ValueError(f"No chunks found for {entity2} {period2}")
        
        # Extract numeric values from chunk texts
        # Look for numbers in the format: $123.45, 123.45, 123,456.78, etc.
        # Pattern captures numbers with optional $ prefix, commas, and decimals
        number_pattern = r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)'
        
        numbers1 = re.findall(number_pattern, chunks1[0].chunk_text)
        numbers2 = re.findall(number_pattern, chunks2[0].chunk_text)
        
        # Convert largest found number to float (remove commas)
        # Use largest to prefer main financial figures over years/dates
        value1 = None
        if numbers1:
            # Convert all numbers and pick the largest
            parsed_numbers = [float(n.replace(',', '')) for n in numbers1]
            value1 = max(parsed_numbers)
        
        value2 = None
        if numbers2:
            # Convert all numbers and pick the largest
            parsed_numbers = [float(n.replace(',', '')) for n in numbers2]
            value2 = max(parsed_numbers)
        
        # Compute delta if both values found
        delta = None
        if value1 is not None and value2 is not None:
            delta = value2 - value1
        
        # Build comparison result
        comparison_result = {
            "entity1": {
                "entity": entity1,
                "period": period1,
                "chunk_text": chunks1[0].chunk_text,
                "chunk_id": chunks1[0].chunk_id,
                "value": value1
            },
            "entity2": {
                "entity": entity2,
                "period": period2,
                "chunk_text": chunks2[0].chunk_text,
                "chunk_id": chunks2[0].chunk_id,
                "value": value2
            },
            "delta": delta
        }
        
        return {"comparison_result": comparison_result}
    
    except Exception as e:
        logger.error(
            f"COMPARE tool failed for {entity1}/{period1} vs {entity2}/{period2}: {e}"
        )
        raise ValueError(f"Failed to compare entities: {e}")


def execute_tool(
    tool_name: str,
    inputs: Dict[str, Any],
    retriever: HybridRetriever,
    db: Optional[AsyncSession] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Dispatcher function to execute a tool by name.
    
    Validates inputs, executes the appropriate tool function, and returns results.
    Tool execution errors are logged and re-raised.
    
    Args:
        tool_name: Name of the tool to execute (CALCULATE, LOOKUP, COMPARE)
        inputs: Dictionary of input parameters
        retriever: HybridRetriever instance for LOOKUP and COMPARE
        db: Database session (optional)
        context: Optional context dictionary for CALCULATE (variables from previous tools)
    
    Returns:
        Dictionary containing tool execution results
    
    Raises:
        ValueError: If tool is unknown, inputs are invalid, or execution fails
    """
    # Validate tool name
    if tool_name not in TOOLS:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    # Validate inputs against schema
    validate_tool_inputs(tool_name, inputs)
    
    # Execute appropriate tool
    try:
        if tool_name == "CALCULATE":
            return _execute_calculate(inputs, context)
        
        elif tool_name == "LOOKUP":
            return _execute_lookup(inputs, retriever, db)
        
        elif tool_name == "COMPARE":
            return _execute_compare(inputs, retriever, db)
        
        else:
            # Should never reach here due to validation above
            raise ValueError(f"Tool {tool_name} not implemented")
    
    except Exception as e:
        logger.error(f"Tool execution failed for {tool_name}: {e}")
        # Re-raise to allow caller to handle
        raise
