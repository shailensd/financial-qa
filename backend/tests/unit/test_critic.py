"""
Unit tests and property-based tests for Critic node.

Tests cover:
- Numerical accuracy validation (exact match in cited chunks)
- Citation completeness validation (every sentence has citations)
- Confidence score computation based on citation coverage
- Forced approval after 2 repair iterations
- Property-based test: any response with number not in chunks must not be approved
"""

import pytest
from hypothesis import given, strategies as st

from app.agent.pipeline import critic_node


class TestCriticNodeUnit:
    """Unit tests for Critic node."""
    
    def test_critic_approves_valid_response(self):
        """Test that Critic approves response with all numbers in cited chunks."""
        state = {
            "draft_response": "Apple's revenue in FY2023 was $383.3 billion.",
            "citations": [
                {"chunk_id": 42, "relevance_score": 0.9}
            ],
            "tool_results": [
                {
                    "tool": "LOOKUP",
                    "status": "success",
                    "output": {
                        "chunk_text": "Apple's total revenue in FY2023 was $383.3 billion.",
                        "chunk_id": 42
                    }
                }
            ],
            "repair_count": 0
        }
        
        result = critic_node(state)
        
        assert result["critic_verdict"] == "approved"
        assert result["confidence_score"] >= 0.5
        assert result["confidence_score"] <= 1.0
        assert result["critic_feedback"] is None
    
    def test_critic_detects_numerical_mismatch(self):
        """Test that Critic detects numbers not in cited chunks."""
        state = {
            "draft_response": "Apple's revenue in FY2023 was $999.9 billion.",
            "citations": [
                {"chunk_id": 42, "relevance_score": 0.9}
            ],
            "tool_results": [
                {
                    "tool": "LOOKUP",
                    "status": "success",
                    "output": {
                        "chunk_text": "Apple's total revenue in FY2023 was $383.3 billion.",
                        "chunk_id": 42
                    }
                }
            ],
            "repair_count": 0
        }
        
        result = critic_node(state)
        
        assert result["critic_verdict"] == "repair_numerical"
        assert result["confidence_score"] == 0.0
        assert "999.9" in result["critic_feedback"]
    
    def test_critic_detects_missing_citations(self):
        """Test that Critic detects responses without citations."""
        state = {
            "draft_response": "Apple is a technology company.",
            "citations": [],  # No citations
            "tool_results": [],
            "repair_count": 0
        }
        
        result = critic_node(state)
        
        assert result["critic_verdict"] == "repair_citation"
        assert result["confidence_score"] == 0.0
        assert "citations" in result["critic_feedback"].lower()
    
    def test_critic_forces_approval_after_two_repairs(self):
        """Test that Critic forces approval with low confidence after 2 repairs."""
        state = {
            "draft_response": "Apple's revenue was $999.9 billion.",
            "citations": [],
            "tool_results": [
                {
                    "tool": "LOOKUP",
                    "status": "success",
                    "output": {
                        "chunk_text": "Apple's revenue was $383.3 billion.",
                        "chunk_id": 42
                    }
                }
            ],
            "repair_count": 2
        }
        
        result = critic_node(state)
        
        assert result["critic_verdict"] == "approved"
        assert result["confidence_score"] == 0.3
    
    def test_critic_handles_multiple_numbers(self):
        """Test that Critic validates multiple numbers in response."""
        state = {
            "draft_response": "Apple's revenue was $383.3 billion and net income was $96.995 billion.",
            "citations": [
                {"chunk_id": 42, "relevance_score": 0.9},
                {"chunk_id": 87, "relevance_score": 0.85}
            ],
            "tool_results": [
                {
                    "tool": "LOOKUP",
                    "status": "success",
                    "output": {
                        "chunk_text": "Apple's revenue was $383.3 billion.",
                        "chunk_id": 42
                    }
                },
                {
                    "tool": "LOOKUP",
                    "status": "success",
                    "output": {
                        "chunk_text": "Net income was $96.995 billion.",
                        "chunk_id": 87
                    }
                }
            ],
            "repair_count": 0
        }
        
        result = critic_node(state)
        
        assert result["critic_verdict"] == "approved"
        assert result["confidence_score"] >= 0.5
    
    def test_critic_handles_compare_tool_results(self):
        """Test that Critic extracts chunk texts from COMPARE tool results."""
        state = {
            "draft_response": "Apple's revenue grew from $365.8 billion to $383.3 billion.",
            "citations": [
                {"chunk_id": 42, "relevance_score": 0.9},
                {"chunk_id": 87, "relevance_score": 0.85}
            ],
            "tool_results": [
                {
                    "tool": "COMPARE",
                    "status": "success",
                    "output": {
                        "comparison_result": {
                            "entity1": {
                                "chunk_text": "Apple FY2023 revenue $383.3 billion",
                                "chunk_id": 42,
                                "value": 383.3
                            },
                            "entity2": {
                                "chunk_text": "Apple FY2022 revenue $365.8 billion",
                                "chunk_id": 87,
                                "value": 365.8
                            },
                            "delta": 17.5
                        }
                    }
                }
            ],
            "repair_count": 0
        }
        
        result = critic_node(state)
        
        assert result["critic_verdict"] == "approved"
        assert result["confidence_score"] >= 0.5
    
    def test_critic_ignores_failed_tool_results(self):
        """Test that Critic ignores tool results with error status."""
        state = {
            "draft_response": "Apple's revenue was $383.3 billion.",
            "citations": [
                {"chunk_id": 42, "relevance_score": 0.9}
            ],
            "tool_results": [
                {
                    "tool": "LOOKUP",
                    "status": "error",
                    "error": "Tool failed"
                },
                {
                    "tool": "LOOKUP",
                    "status": "success",
                    "output": {
                        "chunk_text": "Apple's revenue was $383.3 billion.",
                        "chunk_id": 42
                    }
                }
            ],
            "repair_count": 0
        }
        
        result = critic_node(state)
        
        assert result["critic_verdict"] == "approved"
    
    def test_critic_handles_numbers_with_comma_separator(self):
        """Test that Critic handles numbers with comma as decimal separator."""
        state = {
            "draft_response": "The value was 1,234 million.",
            "citations": [
                {"chunk_id": 42, "relevance_score": 0.9}
            ],
            "tool_results": [
                {
                    "tool": "LOOKUP",
                    "status": "success",
                    "output": {
                        "chunk_text": "The value was 1,234 million.",
                        "chunk_id": 42
                    }
                }
            ],
            "repair_count": 0
        }
        
        result = critic_node(state)
        
        assert result["critic_verdict"] == "approved"
    
    def test_critic_computes_confidence_based_on_citation_coverage(self):
        """Test that confidence score increases with citation coverage."""
        # Test with low coverage (1 citation for 3 sentences)
        state_low = {
            "draft_response": "Apple is a company. It makes products. Revenue was high.",
            "citations": [
                {"chunk_id": 42, "relevance_score": 0.9}
            ],
            "tool_results": [
                {
                    "tool": "LOOKUP",
                    "status": "success",
                    "output": {
                        "chunk_text": "Apple is a company that makes products.",
                        "chunk_id": 42
                    }
                }
            ],
            "repair_count": 0
        }
        
        result_low = critic_node(state_low)
        
        # Test with high coverage (3 citations for 3 sentences)
        state_high = {
            "draft_response": "Apple is a company. It makes products. Revenue was high.",
            "citations": [
                {"chunk_id": 42, "relevance_score": 0.9},
                {"chunk_id": 43, "relevance_score": 0.85},
                {"chunk_id": 44, "relevance_score": 0.8}
            ],
            "tool_results": [
                {
                    "tool": "LOOKUP",
                    "status": "success",
                    "output": {
                        "chunk_text": "Apple is a company that makes products with high revenue.",
                        "chunk_id": 42
                    }
                }
            ],
            "repair_count": 0
        }
        
        result_high = critic_node(state_high)
        
        # High coverage should have higher confidence
        assert result_high["confidence_score"] > result_low["confidence_score"]
    
    def test_critic_handles_empty_response(self):
        """Test that Critic handles empty draft response."""
        state = {
            "draft_response": "",
            "citations": [],
            "tool_results": [],
            "repair_count": 0
        }
        
        result = critic_node(state)
        
        # Empty response with no citations and no content is approved
        # (no factual claims to verify)
        assert result["critic_verdict"] == "approved"
        assert result["confidence_score"] >= 0.5
    
    def test_critic_handles_response_with_no_numbers(self):
        """Test that Critic approves response with no numbers if citations present."""
        state = {
            "draft_response": "Apple is a technology company based in California.",
            "citations": [
                {"chunk_id": 42, "relevance_score": 0.9}
            ],
            "tool_results": [
                {
                    "tool": "LOOKUP",
                    "status": "success",
                    "output": {
                        "chunk_text": "Apple is a technology company based in California.",
                        "chunk_id": 42
                    }
                }
            ],
            "repair_count": 0
        }
        
        result = critic_node(state)
        
        assert result["critic_verdict"] == "approved"
    
    def test_critic_extracts_integers_and_decimals(self):
        """Test that Critic extracts both integers and decimal numbers."""
        state = {
            "draft_response": "Revenue was 383 billion and margin was 25.5 percent.",
            "citations": [
                {"chunk_id": 42, "relevance_score": 0.9}
            ],
            "tool_results": [
                {
                    "tool": "LOOKUP",
                    "status": "success",
                    "output": {
                        "chunk_text": "Revenue was 383 billion and margin was 25.5 percent.",
                        "chunk_id": 42
                    }
                }
            ],
            "repair_count": 0
        }
        
        result = critic_node(state)
        
        assert result["critic_verdict"] == "approved"
    
    def test_critic_provides_feedback_on_numerical_repair(self):
        """Test that Critic provides specific feedback for numerical repairs."""
        state = {
            "draft_response": "Revenue was $999.9 billion.",
            "citations": [
                {"chunk_id": 42, "relevance_score": 0.9}
            ],
            "tool_results": [
                {
                    "tool": "LOOKUP",
                    "status": "success",
                    "output": {
                        "chunk_text": "Revenue was $383.3 billion.",
                        "chunk_id": 42
                    }
                }
            ],
            "repair_count": 0
        }
        
        result = critic_node(state)
        
        assert result["critic_verdict"] == "repair_numerical"
        assert result["critic_feedback"] is not None
        assert "999.9" in result["critic_feedback"]
        assert "verify" in result["critic_feedback"].lower()
    
    def test_critic_provides_feedback_on_citation_repair(self):
        """Test that Critic provides specific feedback for citation repairs."""
        state = {
            "draft_response": "Apple is a company.",
            "citations": [],
            "tool_results": [],
            "repair_count": 0
        }
        
        result = critic_node(state)
        
        assert result["critic_verdict"] == "repair_citation"
        assert result["critic_feedback"] is not None
        assert "citation" in result["critic_feedback"].lower()


class TestCriticNodePropertyBased:
    """Property-based tests for Critic node."""
    
    @given(
        number=st.integers(min_value=1, max_value=999999),
        prefix=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Zs")),
            max_size=30
        ),
        suffix=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Zs")),
            max_size=30
        )
    )
    def test_property_number_not_in_chunks_never_approved(self, number, prefix, suffix):
        """
        **Validates: Requirement 9.2, 9.3**
        
        Property: For any response containing a number that does not appear
        in cited chunks, the Critic must never return "approved" verdict
        (unless repair_count >= 2, which forces approval).
        
        This property ensures numerical accuracy guardrails are enforced.
        """
        # Construct response with a number
        draft_response = f"{prefix} {number} {suffix}"
        
        # Create cited chunks that do NOT contain this number
        # Use a different number to ensure mismatch
        different_number = number + 1000
        
        state = {
            "draft_response": draft_response,
            "citations": [
                {"chunk_id": 42, "relevance_score": 0.9}
            ],
            "tool_results": [
                {
                    "tool": "LOOKUP",
                    "status": "success",
                    "output": {
                        "chunk_text": f"The value was {different_number} units.",
                        "chunk_id": 42
                    }
                }
            ],
            "repair_count": 0  # Not forced approval
        }
        
        result = critic_node(state)
        
        # Property assertion: verdict must NOT be "approved"
        assert result["critic_verdict"] != "approved", (
            f"Critic incorrectly approved response with number {number} "
            f"not found in cited chunks (chunk contains {different_number})"
        )
        assert result["critic_verdict"] == "repair_numerical"
    
    @given(
        repair_count=st.integers(min_value=2, max_value=10)
    )
    def test_property_forced_approval_after_max_repairs(self, repair_count):
        """
        **Validates: Requirement 9.7**
        
        Property: For any state with repair_count >= 2, the Critic must
        always return "approved" verdict with confidence_score = 0.3,
        regardless of validation failures.
        
        This property ensures the repair loop terminates after max iterations.
        """
        # Create a state with obvious validation failures
        state = {
            "draft_response": "The value was 999999 which is wrong.",
            "citations": [],  # Missing citations
            "tool_results": [
                {
                    "tool": "LOOKUP",
                    "status": "success",
                    "output": {
                        "chunk_text": "The value was 12345.",
                        "chunk_id": 42
                    }
                }
            ],
            "repair_count": repair_count
        }
        
        result = critic_node(state)
        
        # Property assertion: must force approval
        assert result["critic_verdict"] == "approved", (
            f"Critic failed to force approval at repair_count={repair_count}"
        )
        assert result["confidence_score"] == 0.3, (
            f"Critic did not set confidence_score=0.3 for forced approval "
            f"(got {result['confidence_score']})"
        )
    
    @given(
        sentence_count=st.integers(min_value=1, max_value=10),
        citation_count=st.integers(min_value=0, max_value=10)
    )
    def test_property_confidence_score_range(self, sentence_count, citation_count):
        """
        **Validates: Requirement 9.4**
        
        Property: For any approved response, confidence_score must be
        in the range [0.5, 1.0] for normal approval, or exactly 0.3
        for forced approval (repair_count >= 2).
        
        This property ensures confidence scores are computed correctly.
        """
        # Create a response with specified number of sentences
        sentences = [f"Sentence {i}." for i in range(sentence_count)]
        draft_response = " ".join(sentences)
        
        # Create citations
        citations = [
            {"chunk_id": i, "relevance_score": 0.9}
            for i in range(citation_count)
        ]
        
        # Create tool results with chunk texts (no numbers to avoid numerical check)
        tool_results = [
            {
                "tool": "LOOKUP",
                "status": "success",
                "output": {
                    "chunk_text": f"Chunk text {i}.",
                    "chunk_id": i
                }
            }
            for i in range(max(citation_count, 1))
        ]
        
        state = {
            "draft_response": draft_response,
            "citations": citations,
            "tool_results": tool_results,
            "repair_count": 0
        }
        
        result = critic_node(state)
        
        # Only check confidence if approved
        if result["critic_verdict"] == "approved":
            confidence = result["confidence_score"]
            
            # Property assertion: confidence must be in valid range
            assert 0.5 <= confidence <= 1.0, (
                f"Critic confidence_score {confidence} out of range [0.5, 1.0] "
                f"for {sentence_count} sentences and {citation_count} citations"
            )
