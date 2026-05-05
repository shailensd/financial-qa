"""
Unit tests and property-based tests for RefusalGuard node.

Tests cover:
- Investment advice keyword detection
- Future prediction keyword detection
- Allowed queries pass through
- Property-based test: any query with investment keyword must be refused
"""

import pytest
from hypothesis import given, strategies as st

from app.agent.pipeline import (
    refusal_guard_node,
    INVESTMENT_KEYWORDS,
    PREDICTION_KEYWORDS
)


class TestRefusalGuardUnit:
    """Unit tests for RefusalGuard node."""
    
    def test_investment_advice_buy(self):
        """Test that 'buy' keyword triggers investment advice refusal."""
        state = {"query": "Should I buy Apple stock?"}
        result = refusal_guard_node(state)
        
        assert result["refusal"] is True
        assert result["refusal_reason"] == "investment_advice_prohibited"
    
    def test_investment_advice_sell(self):
        """Test that 'sell' keyword triggers investment advice refusal."""
        state = {"query": "When should I sell my Tesla shares?"}
        result = refusal_guard_node(state)
        
        assert result["refusal"] is True
        assert result["refusal_reason"] == "investment_advice_prohibited"
    
    def test_investment_advice_invest(self):
        """Test that 'invest' keyword triggers investment advice refusal."""
        state = {"query": "Where should I invest my money?"}
        result = refusal_guard_node(state)
        
        assert result["refusal"] is True
        assert result["refusal_reason"] == "investment_advice_prohibited"
    
    def test_investment_advice_recommend(self):
        """Test that 'recommend' keyword triggers investment advice refusal."""
        state = {"query": "What stocks do you recommend?"}
        result = refusal_guard_node(state)
        
        assert result["refusal"] is True
        assert result["refusal_reason"] == "investment_advice_prohibited"
    
    def test_investment_advice_portfolio(self):
        """Test that 'portfolio' keyword triggers investment advice refusal."""
        state = {"query": "How should I structure my portfolio?"}
        result = refusal_guard_node(state)
        
        assert result["refusal"] is True
        assert result["refusal_reason"] == "investment_advice_prohibited"
    
    def test_investment_advice_stock_pick(self):
        """Test that 'stock pick' keyword triggers investment advice refusal."""
        state = {"query": "What's your best stock pick for 2024?"}
        result = refusal_guard_node(state)
        
        assert result["refusal"] is True
        assert result["refusal_reason"] == "investment_advice_prohibited"
    
    def test_future_prediction_will(self):
        """Test that 'will' keyword triggers future prediction refusal."""
        state = {"query": "What will Apple's stock price be next month?"}
        result = refusal_guard_node(state)
        
        assert result["refusal"] is True
        assert result["refusal_reason"] == "future_prediction_prohibited"
    
    def test_future_prediction_predict(self):
        """Test that 'predict' keyword triggers future prediction refusal."""
        state = {"query": "Can you predict Tesla's earnings?"}
        result = refusal_guard_node(state)
        
        assert result["refusal"] is True
        assert result["refusal_reason"] == "future_prediction_prohibited"
    
    def test_future_prediction_forecast(self):
        """Test that 'forecast' keyword triggers future prediction refusal."""
        state = {"query": "What's the forecast for Microsoft revenue?"}
        result = refusal_guard_node(state)
        
        assert result["refusal"] is True
        assert result["refusal_reason"] == "future_prediction_prohibited"
    
    def test_future_prediction_next_quarter(self):
        """Test that 'next quarter' keyword triggers future prediction refusal."""
        state = {"query": "What will revenue be next quarter?"}
        result = refusal_guard_node(state)
        
        assert result["refusal"] is True
        assert result["refusal_reason"] == "future_prediction_prohibited"
    
    def test_future_prediction_next_year(self):
        """Test that 'next year' keyword triggers future prediction refusal."""
        state = {"query": "How will the company perform next year?"}
        result = refusal_guard_node(state)
        
        assert result["refusal"] is True
        assert result["refusal_reason"] == "future_prediction_prohibited"
    
    def test_future_prediction_price_target(self):
        """Test that 'price target' keyword triggers future prediction refusal."""
        state = {"query": "What's your price target for Amazon?"}
        result = refusal_guard_node(state)
        
        assert result["refusal"] is True
        assert result["refusal_reason"] == "future_prediction_prohibited"
    
    def test_allowed_factual_query(self):
        """Test that factual queries are allowed."""
        state = {"query": "What was Apple's revenue in FY2023?"}
        result = refusal_guard_node(state)
        
        assert result["refusal"] is False
        assert result["refusal_reason"] is None
    
    def test_allowed_comparison_query(self):
        """Test that comparison queries are allowed."""
        state = {"query": "Compare Microsoft and Google revenue in 2023"}
        result = refusal_guard_node(state)
        
        assert result["refusal"] is False
        assert result["refusal_reason"] is None
    
    def test_allowed_calculation_query(self):
        """Test that calculation queries are allowed."""
        state = {"query": "What is the profit margin for Tesla?"}
        result = refusal_guard_node(state)
        
        assert result["refusal"] is False
        assert result["refusal_reason"] is None
    
    def test_case_insensitive_investment(self):
        """Test that keyword matching is case-insensitive."""
        state = {"query": "Should I BUY Apple stock?"}
        result = refusal_guard_node(state)
        
        assert result["refusal"] is True
        assert result["refusal_reason"] == "investment_advice_prohibited"
    
    def test_case_insensitive_prediction(self):
        """Test that keyword matching is case-insensitive."""
        state = {"query": "What WILL the stock price be?"}
        result = refusal_guard_node(state)
        
        assert result["refusal"] is True
        assert result["refusal_reason"] == "future_prediction_prohibited"
    
    def test_empty_query(self):
        """Test that empty query is allowed (no refusal)."""
        state = {"query": ""}
        result = refusal_guard_node(state)
        
        assert result["refusal"] is False
        assert result["refusal_reason"] is None
    
    def test_missing_query_key(self):
        """Test that missing query key is handled gracefully."""
        state = {}
        result = refusal_guard_node(state)
        
        assert result["refusal"] is False
        assert result["refusal_reason"] is None
    
    def test_investment_keyword_priority(self):
        """Test that investment keywords are checked first."""
        # Query contains both investment and prediction keywords
        state = {"query": "Should I buy stocks that will grow next year?"}
        result = refusal_guard_node(state)
        
        # Should refuse with investment reason (checked first)
        assert result["refusal"] is True
        assert result["refusal_reason"] == "investment_advice_prohibited"


class TestRefusalGuardPropertyBased:
    """Property-based tests for RefusalGuard node."""
    
    @given(
        keyword=st.sampled_from(INVESTMENT_KEYWORDS),
        prefix=st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs")), max_size=50),
        suffix=st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs")), max_size=50)
    )
    def test_property_any_investment_keyword_must_refuse(self, keyword, prefix, suffix):
        """
        **Validates: Requirement 6.1**
        
        Property: For any query containing an investment keyword,
        refusal_flag must always be True.
        
        This property ensures that the RefusalGuard never allows
        investment advice queries to pass through to the Planner.
        """
        # Construct query with investment keyword embedded
        query = f"{prefix} {keyword} {suffix}"
        state = {"query": query}
        
        result = refusal_guard_node(state)
        
        # Property assertion: refusal must be True
        assert result["refusal"] is True, (
            f"RefusalGuard failed to refuse query with investment keyword '{keyword}': {query}"
        )
        assert result["refusal_reason"] == "investment_advice_prohibited"
    
    @given(
        keyword=st.sampled_from(PREDICTION_KEYWORDS),
        prefix=st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs")), max_size=50),
        suffix=st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs")), max_size=50)
    )
    def test_property_any_prediction_keyword_must_refuse(self, keyword, prefix, suffix):
        """
        **Validates: Requirement 6.2**
        
        Property: For any query containing a prediction keyword,
        refusal_flag must always be True.
        
        This property ensures that the RefusalGuard never allows
        future prediction queries to pass through to the Planner.
        """
        # Construct query with prediction keyword embedded
        query = f"{prefix} {keyword} {suffix}"
        state = {"query": query}
        
        result = refusal_guard_node(state)
        
        # Property assertion: refusal must be True
        assert result["refusal"] is True, (
            f"RefusalGuard failed to refuse query with prediction keyword '{keyword}': {query}"
        )
        assert result["refusal_reason"] == "future_prediction_prohibited"
    
    @given(
        query_text=st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd", "Zs"),
                blacklist_characters="".join(INVESTMENT_KEYWORDS + PREDICTION_KEYWORDS)
            ),
            min_size=1,
            max_size=100
        ).filter(
            lambda q: not any(kw in q.lower() for kw in INVESTMENT_KEYWORDS + PREDICTION_KEYWORDS)
        )
    )
    def test_property_queries_without_keywords_allowed(self, query_text):
        """
        **Validates: Requirement 6 (inverse)**
        
        Property: For any query NOT containing prohibited keywords,
        refusal_flag must be False.
        
        This property ensures that the RefusalGuard does not
        over-block legitimate queries.
        """
        state = {"query": query_text}
        result = refusal_guard_node(state)
        
        # Property assertion: refusal must be False
        assert result["refusal"] is False, (
            f"RefusalGuard incorrectly refused query without prohibited keywords: {query_text}"
        )
        assert result["refusal_reason"] is None
