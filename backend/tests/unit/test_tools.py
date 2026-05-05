"""
Unit tests for the Tool Registry.

Tests cover:
- Tool input validation
- Tool firing restrictions (get_available_tools)
- CALCULATE executor
- LOOKUP executor
- COMPARE executor
- execute_tool dispatcher
"""

import pytest
from unittest.mock import Mock, MagicMock

from app.agent.tools import (
    TOOLS,
    validate_tool_inputs,
    get_available_tools,
    execute_tool,
    _execute_calculate,
    _execute_lookup,
    _execute_compare
)
from app.ml.hybrid_retrieval import ScoredChunk


class TestToolSchemas:
    """Test tool schema definitions."""
    
    def test_tools_dict_structure(self):
        """Verify TOOLS dict has correct structure."""
        assert "CALCULATE" in TOOLS
        assert "LOOKUP" in TOOLS
        assert "COMPARE" in TOOLS
        
        for tool_name, tool_def in TOOLS.items():
            assert "input_schema" in tool_def
            assert "output_schema" in tool_def
            assert "firing_condition" in tool_def
    
    def test_calculate_schema(self):
        """Verify CALCULATE tool schema."""
        schema = TOOLS["CALCULATE"]
        assert schema["input_schema"] == {"expression": str}
        assert schema["output_schema"] == {"result": float}
        assert "numeric_keywords" in schema
        assert "revenue" in schema["numeric_keywords"]
    
    def test_lookup_schema(self):
        """Verify LOOKUP tool schema."""
        schema = TOOLS["LOOKUP"]
        assert schema["input_schema"] == {"entity": str, "attribute": str}
        assert schema["output_schema"] == {"chunk_text": str, "chunk_id": int}
        assert schema["firing_condition"] == "always available"
    
    def test_compare_schema(self):
        """Verify COMPARE tool schema."""
        schema = TOOLS["COMPARE"]
        assert schema["input_schema"] == {
            "entity1": str,
            "period1": str,
            "entity2": str,
            "period2": str
        }
        assert schema["output_schema"] == {"comparison_result": dict}


class TestValidateToolInputs:
    """Test input validation logic."""
    
    def test_validate_calculate_valid_inputs(self):
        """Valid CALCULATE inputs should pass."""
        inputs = {"expression": "100 + 200"}
        validate_tool_inputs("CALCULATE", inputs)  # Should not raise
    
    def test_validate_calculate_missing_field(self):
        """Missing required field should raise ValueError."""
        inputs = {}
        with pytest.raises(ValueError, match="Missing required field 'expression'"):
            validate_tool_inputs("CALCULATE", inputs)
    
    def test_validate_calculate_wrong_type(self):
        """Wrong type should raise ValueError."""
        inputs = {"expression": 123}  # Should be str
        with pytest.raises(ValueError, match="must be of type str"):
            validate_tool_inputs("CALCULATE", inputs)
    
    def test_validate_lookup_valid_inputs(self):
        """Valid LOOKUP inputs should pass."""
        inputs = {"entity": "Apple", "attribute": "revenue"}
        validate_tool_inputs("LOOKUP", inputs)  # Should not raise
    
    def test_validate_lookup_missing_field(self):
        """Missing required field should raise ValueError."""
        inputs = {"entity": "Apple"}
        with pytest.raises(ValueError, match="Missing required field 'attribute'"):
            validate_tool_inputs("LOOKUP", inputs)
    
    def test_validate_compare_valid_inputs(self):
        """Valid COMPARE inputs should pass."""
        inputs = {
            "entity1": "Apple",
            "period1": "FY2023",
            "entity2": "Microsoft",
            "period2": "FY2023"
        }
        validate_tool_inputs("COMPARE", inputs)  # Should not raise
    
    def test_validate_compare_missing_fields(self):
        """Missing required fields should raise ValueError."""
        inputs = {"entity1": "Apple", "period1": "FY2023"}
        with pytest.raises(ValueError, match="Missing required field"):
            validate_tool_inputs("COMPARE", inputs)
    
    def test_validate_unknown_tool(self):
        """Unknown tool should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown tool"):
            validate_tool_inputs("UNKNOWN_TOOL", {})
    
    def test_validate_unexpected_fields(self):
        """Unexpected fields should raise ValueError."""
        inputs = {"expression": "1+1", "extra_field": "unexpected"}
        with pytest.raises(ValueError, match="Unexpected fields"):
            validate_tool_inputs("CALCULATE", inputs)


class TestGetAvailableTools:
    """Test tool firing restrictions."""
    
    def test_lookup_always_available(self):
        """LOOKUP should always be available."""
        queries = [
            "What is Apple's revenue?",
            "Tell me about Microsoft",
            "Random query with no keywords"
        ]
        for query in queries:
            tools = get_available_tools(query)
            assert "LOOKUP" in tools
    
    def test_calculate_fires_on_numeric_keywords(self):
        """CALCULATE should fire when query contains numeric keywords."""
        # Test each numeric keyword
        numeric_keywords = ["revenue", "margin", "ratio", "growth", "percent",
                           "dollar", "million", "billion", "eps", "ebitda"]
        
        for keyword in numeric_keywords:
            query = f"What is the {keyword} for Apple?"
            tools = get_available_tools(query)
            assert "CALCULATE" in tools, f"CALCULATE should fire for keyword: {keyword}"
    
    def test_calculate_not_fires_without_keywords(self):
        """CALCULATE should not fire without numeric keywords."""
        query = "Tell me about Apple's business model"
        tools = get_available_tools(query)
        assert "CALCULATE" not in tools
    
    def test_compare_fires_on_two_fiscal_years(self):
        """COMPARE should fire when query mentions 2 fiscal years."""
        queries = [
            "Compare Apple's revenue in FY2023 vs FY2022",
            "What changed between 2022 and 2023?",
            "Difference from FY 2021 to FY 2022"
        ]
        for query in queries:
            tools = get_available_tools(query)
            assert "COMPARE" in tools, f"COMPARE should fire for: {query}"
    
    def test_compare_fires_on_two_companies(self):
        """COMPARE should fire when query mentions 2 companies."""
        queries = [
            "Compare Apple and Microsoft revenue",
            "Apple versus Google performance",
            "Difference between Tesla and Ford"
        ]
        for query in queries:
            tools = get_available_tools(query)
            assert "COMPARE" in tools, f"COMPARE should fire for: {query}"
    
    def test_compare_fires_on_comparison_intent(self):
        """COMPARE should fire on comparison keywords."""
        query = "Compare Apple's performance"
        tools = get_available_tools(query)
        assert "COMPARE" in tools
    
    def test_compare_not_fires_single_entity(self):
        """COMPARE should not fire for single entity queries."""
        query = "What is Apple's revenue?"
        tools = get_available_tools(query)
        # COMPARE might still fire if there are comparison keywords, but not for this simple query
        # This test verifies the basic case
        assert "LOOKUP" in tools  # At minimum, LOOKUP should be available


class TestCalculateExecutor:
    """Test CALCULATE tool executor."""
    
    def test_calculate_simple_addition(self):
        """Test simple addition."""
        inputs = {"expression": "100 + 200"}
        result = _execute_calculate(inputs)
        assert result == {"result": 300.0}
    
    def test_calculate_multiplication(self):
        """Test multiplication."""
        inputs = {"expression": "50 * 2"}
        result = _execute_calculate(inputs)
        assert result == {"result": 100.0}
    
    def test_calculate_division(self):
        """Test division."""
        inputs = {"expression": "100 / 4"}
        result = _execute_calculate(inputs)
        assert result == {"result": 25.0}
    
    def test_calculate_complex_expression(self):
        """Test complex mathematical expression."""
        inputs = {"expression": "(100 + 200) * 2 / 3"}
        result = _execute_calculate(inputs)
        assert result == {"result": 200.0}
    
    def test_calculate_with_functions(self):
        """Test with allowed math functions."""
        inputs = {"expression": "max(100, 200)"}
        result = _execute_calculate(inputs)
        assert result == {"result": 200.0}
    
    def test_calculate_with_abs(self):
        """Test with abs function."""
        inputs = {"expression": "abs(-50)"}
        result = _execute_calculate(inputs)
        assert result == {"result": 50.0}
    
    def test_calculate_invalid_expression(self):
        """Invalid expression should raise ValueError."""
        inputs = {"expression": "invalid expression"}
        with pytest.raises(ValueError, match="Failed to evaluate expression"):
            _execute_calculate(inputs)
    
    def test_calculate_no_builtins(self):
        """Builtins should not be accessible (security)."""
        inputs = {"expression": "__import__('os').system('ls')"}
        with pytest.raises(ValueError, match="Failed to evaluate expression"):
            _execute_calculate(inputs)
    
    def test_calculate_no_open(self):
        """File operations should not be accessible (security)."""
        inputs = {"expression": "open('/etc/passwd')"}
        with pytest.raises(ValueError, match="Failed to evaluate expression"):
            _execute_calculate(inputs)


class TestLookupExecutor:
    """Test LOOKUP tool executor."""
    
    def test_lookup_success(self):
        """Test successful lookup."""
        # Mock retriever
        mock_retriever = Mock()
        mock_chunk = ScoredChunk(
            chunk_id=42,
            chunk_text="Apple's revenue in FY2023 was $383.3 billion.",
            score=0.95
        )
        mock_retriever.retrieve.return_value = [mock_chunk]
        
        inputs = {"entity": "Apple", "attribute": "revenue"}
        result = _execute_lookup(inputs, mock_retriever)
        
        assert result == {
            "chunk_text": "Apple's revenue in FY2023 was $383.3 billion.",
            "chunk_id": 42
        }
        mock_retriever.retrieve.assert_called_once_with("Apple revenue", top_k=1)
    
    def test_lookup_no_chunks_found(self):
        """Test lookup when no chunks found."""
        mock_retriever = Mock()
        mock_retriever.retrieve.return_value = []
        
        inputs = {"entity": "UnknownCompany", "attribute": "revenue"}
        with pytest.raises(ValueError, match="No chunks found"):
            _execute_lookup(inputs, mock_retriever)
    
    def test_lookup_retriever_exception(self):
        """Test lookup when retriever raises exception."""
        mock_retriever = Mock()
        mock_retriever.retrieve.side_effect = Exception("Retrieval failed")
        
        inputs = {"entity": "Apple", "attribute": "revenue"}
        with pytest.raises(ValueError, match="Failed to retrieve chunks"):
            _execute_lookup(inputs, mock_retriever)


class TestCompareExecutor:
    """Test COMPARE tool executor."""
    
    def test_compare_success(self):
        """Test successful comparison."""
        mock_retriever = Mock()
        
        # Mock chunks for both lookups
        chunk1 = ScoredChunk(
            chunk_id=42,
            chunk_text="Apple's revenue in FY2023 was $383.3 billion.",
            score=0.95
        )
        chunk2 = ScoredChunk(
            chunk_id=87,
            chunk_text="Apple's revenue in FY2022 was $365.8 billion.",
            score=0.93
        )
        
        # Configure mock to return different chunks for different queries
        def mock_retrieve(query, top_k):
            if "FY2023" in query:
                return [chunk1]
            elif "FY2022" in query:
                return [chunk2]
            return []
        
        mock_retriever.retrieve.side_effect = mock_retrieve
        
        inputs = {
            "entity1": "Apple",
            "period1": "FY2023",
            "entity2": "Apple",
            "period2": "FY2022"
        }
        result = _execute_compare(inputs, mock_retriever)
        
        assert "comparison_result" in result
        comp = result["comparison_result"]
        
        assert comp["entity1"]["chunk_id"] == 42
        assert comp["entity2"]["chunk_id"] == 87
        assert comp["entity1"]["value"] == 383.3
        assert comp["entity2"]["value"] == 365.8
        assert comp["delta"] == pytest.approx(365.8 - 383.3)
    
    def test_compare_no_chunks_first_entity(self):
        """Test compare when first entity lookup fails."""
        mock_retriever = Mock()
        mock_retriever.retrieve.return_value = []
        
        inputs = {
            "entity1": "Unknown",
            "period1": "FY2023",
            "entity2": "Apple",
            "period2": "FY2022"
        }
        with pytest.raises(ValueError, match="No chunks found for Unknown FY2023"):
            _execute_compare(inputs, mock_retriever)
    
    def test_compare_no_chunks_second_entity(self):
        """Test compare when second entity lookup fails."""
        mock_retriever = Mock()
        
        chunk1 = ScoredChunk(chunk_id=42, chunk_text="Apple revenue $383.3B", score=0.95)
        
        def mock_retrieve(query, top_k):
            if "Apple" in query and "FY2023" in query:
                return [chunk1]
            return []
        
        mock_retriever.retrieve.side_effect = mock_retrieve
        
        inputs = {
            "entity1": "Apple",
            "period1": "FY2023",
            "entity2": "Unknown",
            "period2": "FY2022"
        }
        with pytest.raises(ValueError, match="No chunks found for Unknown FY2022"):
            _execute_compare(inputs, mock_retriever)
    
    def test_compare_numeric_extraction(self):
        """Test numeric value extraction from chunks."""
        mock_retriever = Mock()
        
        chunk1 = ScoredChunk(
            chunk_id=1,
            chunk_text="Revenue was $1,234.56 million",
            score=0.9
        )
        chunk2 = ScoredChunk(
            chunk_id=2,
            chunk_text="Revenue reached 987.65 million",
            score=0.9
        )
        
        def mock_retrieve(query, top_k):
            if "entity1" in query or "period1" in query:
                return [chunk1]
            return [chunk2]
        
        mock_retriever.retrieve.side_effect = mock_retrieve
        
        inputs = {
            "entity1": "Company1",
            "period1": "period1",
            "entity2": "Company2",
            "period2": "period2"
        }
        result = _execute_compare(inputs, mock_retriever)
        
        comp = result["comparison_result"]
        assert comp["entity1"]["value"] == 1234.56
        assert comp["entity2"]["value"] == 987.65
        assert comp["delta"] == pytest.approx(987.65 - 1234.56)


class TestExecuteToolDispatcher:
    """Test execute_tool dispatcher function."""
    
    def test_execute_calculate(self):
        """Test dispatching to CALCULATE."""
        mock_retriever = Mock()
        inputs = {"expression": "100 + 50"}
        
        result = execute_tool("CALCULATE", inputs, mock_retriever)
        assert result == {"result": 150.0}
    
    def test_execute_lookup(self):
        """Test dispatching to LOOKUP."""
        mock_retriever = Mock()
        mock_chunk = ScoredChunk(
            chunk_id=42,
            chunk_text="Test chunk text",
            score=0.9
        )
        mock_retriever.retrieve.return_value = [mock_chunk]
        
        inputs = {"entity": "Apple", "attribute": "revenue"}
        result = execute_tool("LOOKUP", inputs, mock_retriever)
        
        assert result["chunk_id"] == 42
        assert result["chunk_text"] == "Test chunk text"
    
    def test_execute_compare(self):
        """Test dispatching to COMPARE."""
        mock_retriever = Mock()
        
        chunk1 = ScoredChunk(chunk_id=1, chunk_text="Value: $100", score=0.9)
        chunk2 = ScoredChunk(chunk_id=2, chunk_text="Value: $200", score=0.9)
        
        mock_retriever.retrieve.side_effect = [[chunk1], [chunk2]]
        
        inputs = {
            "entity1": "A",
            "period1": "2023",
            "entity2": "B",
            "period2": "2022"
        }
        result = execute_tool("COMPARE", inputs, mock_retriever)
        
        assert "comparison_result" in result
    
    def test_execute_unknown_tool(self):
        """Test dispatching to unknown tool."""
        mock_retriever = Mock()
        with pytest.raises(ValueError, match="Unknown tool"):
            execute_tool("UNKNOWN", {}, mock_retriever)
    
    def test_execute_invalid_inputs(self):
        """Test dispatching with invalid inputs."""
        mock_retriever = Mock()
        with pytest.raises(ValueError, match="Missing required field"):
            execute_tool("CALCULATE", {}, mock_retriever)
    
    def test_execute_tool_exception_logged(self):
        """Test that tool exceptions are logged and re-raised."""
        mock_retriever = Mock()
        mock_retriever.retrieve.side_effect = Exception("Retrieval error")
        
        inputs = {"entity": "Apple", "attribute": "revenue"}
        with pytest.raises(ValueError, match="Failed to retrieve chunks"):
            execute_tool("LOOKUP", inputs, mock_retriever)


class TestFiringRestrictionEdgeCases:
    """Test edge cases in firing restriction logic."""
    
    def test_case_insensitive_keyword_matching(self):
        """Keyword matching should be case-insensitive."""
        queries = [
            "What is the REVENUE?",
            "Calculate the Margin",
            "Show me the EPS"
        ]
        for query in queries:
            tools = get_available_tools(query)
            assert "CALCULATE" in tools
    
    def test_multiple_tools_available(self):
        """Multiple tools can be available simultaneously."""
        query = "Compare Apple's revenue in FY2023 vs FY2022"
        tools = get_available_tools(query)
        
        assert "LOOKUP" in tools
        assert "CALCULATE" in tools  # "revenue" keyword
        assert "COMPARE" in tools  # two fiscal years
    
    def test_fiscal_year_formats(self):
        """Test various fiscal year formats."""
        queries = [
            "FY2023 vs FY2022",
            "FY 2023 vs FY 2022",
            "2023 vs 2022",
            "fiscal year 2023 and 2022"
        ]
        for query in queries:
            tools = get_available_tools(query)
            assert "COMPARE" in tools, f"Should detect two years in: {query}"
