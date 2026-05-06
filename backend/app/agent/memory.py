"""
Memory system for FinDoc Intelligence agent.

This module implements the MemorySystem class that manages session context through:
- write: Persist raw turns after every query-response exchange
- retrieve: Fetch session context (latest summary + recent turns) for Planner injection
- summarize: Compress session history every 5 turns using LLM

The memory system enables stateful multi-turn conversations by maintaining
and injecting relevant context into the agent pipeline.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import re

from app.crud import write_memory, get_recent_memory, get_raw_turns


class MemorySystem:
    """
    Manages session memory for multi-turn conversations.
    
    The memory system operates in three modes:
    1. Write: Store raw turn data after every query-response exchange
    2. Retrieve: Fetch context for injection into Planner prompts
    3. Summarize: Compress history every N turns to manage context window
    """
    
    def __init__(self, llm_router=None):
        """
        Initialize the MemorySystem.
        
        Args:
            llm_router: Optional LLMRouter instance for summarization.
                       Can also be provided directly to summarize() method.
        """
        self.llm_router = llm_router
    
    async def write(
        self,
        db: AsyncSession,
        session_id: str,
        turn_num: int,
        query: str,
        response: str,
    ) -> None:
        """
        Write a raw turn to memory after every query-response exchange.
        
        Extracts key entities (company names, financial terms) from the query
        and response, then persists the turn to the memory_summaries table.
        
        Args:
            db: Database session
            session_id: Session identifier
            turn_num: Turn number within the session
            query: User's query text
            response: Agent's response text
        
        Returns:
            None
        """
        # Extract key entities from query and response
        entities = self._extract_entities(query, response)
        
        # Format summary text with entities and turn content
        summary_text = self._format_raw_turn(turn_num, query, response, entities)
        
        # Write to memory_summaries table
        await write_memory(
            db=db,
            session_id=session_id,
            turn_range_start=turn_num,
            turn_range_end=turn_num,
            summary_text=summary_text,
        )
    
    async def retrieve(
        self,
        db: AsyncSession,
        session_id: str,
    ) -> str:
        """
        Retrieve session context for injection into Planner prompts.
        
        Fetches the latest memory summary (if available) and the last 2 raw turns,
        then formats them into a memory_context string suitable for prompt injection.
        
        Args:
            db: Database session
            session_id: Session identifier
        
        Returns:
            Formatted memory context string with structure:
            [Session Summary]
            <compressed summary text>
            
            [Recent Turns]
            Turn N-1: Q: <query> A: <response>
            Turn N: Q: <query> A: <response>
        """
        # Fetch recent memory summaries
        recent_summaries = await get_recent_memory(db, session_id, limit=10)
        
        # Separate compressed summaries from raw turns
        compressed_summary = None
        raw_turn_summaries = []
        
        for summary in recent_summaries:
            if summary.turn_range_end > summary.turn_range_start:
                # This is a compressed summary (multi-turn range)
                if compressed_summary is None:
                    compressed_summary = summary
            else:
                # This is a raw turn (single turn)
                raw_turn_summaries.append(summary)
        
        # Take only the last 2 raw turns
        raw_turn_summaries = raw_turn_summaries[:2]
        
        # Format memory context
        memory_context = ""
        
        if compressed_summary:
            memory_context += "[Session Summary]\n"
            memory_context += f"{compressed_summary.summary_text}\n\n"
        
        if raw_turn_summaries:
            memory_context += "[Recent Turns]\n"
            # raw_turn_summaries are in descending order (most recent first), reverse for chronological
            for summary in reversed(raw_turn_summaries):
                memory_context += f"{summary.summary_text}\n"
        
        return memory_context.strip()
    
    async def summarize(
        self,
        db: AsyncSession,
        session_id: str,
        llm_router=None,
    ) -> None:
        """
        Compress session history every 5 turns using LLM.
        
        Fetches the last 5 turns from memory_summaries, calls the LLM to compress
        them into a 150-word summary, then writes the compressed summary back to
        the memory_summaries table with an updated turn range.
        
        Args:
            db: Database session
            session_id: Session identifier
            llm_router: Optional LLMRouter instance for calling the LLM.
                       If not provided, uses the instance's llm_router.
        
        Returns:
            None
        
        Raises:
            ValueError: If no LLM router is available (neither provided nor in instance)
        """
        # Use provided router or fall back to instance router
        router = llm_router or self.llm_router
        
        if router is None:
            raise ValueError("LLM router is required for summarization. Provide it in constructor or as argument.")
        
        # Fetch last 5 memory entries (raw turns)
        recent_memories = await get_recent_memory(db, session_id, limit=5)
        
        if not recent_memories:
            return
        
        # Filter to only raw turns (single-turn entries)
        raw_turns = [m for m in recent_memories if m.turn_range_start == m.turn_range_end]
        
        if len(raw_turns) < 5:
            # Not enough turns to summarize yet
            return
        
        # Take exactly the last 5 raw turns (they're in descending order, so reverse)
        turns_to_summarize = list(reversed(raw_turns[:5]))
        
        # Build prompt for LLM compression
        turns_text = "\n\n".join([
            f"Turn {m.turn_range_start}:\n{m.summary_text}"
            for m in turns_to_summarize
        ])
        
        system_prompt = """You are a summarization assistant for a financial Q&A system. 
Your task is to compress conversation history into concise summaries that preserve key information."""
        
        user_prompt = f"""Compress the following conversation turns into a concise 150-word summary that captures:
- Key entities mentioned (companies, financial metrics, time periods)
- Main topics discussed
- Important facts or numbers referenced

Conversation turns:
{turns_text}

Provide a 150-word summary:"""
        
        # Call LLM to compress
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        compressed_summary = router.complete(
            model="gemini",  # Use Gemini for summarization
            messages=messages,
        )
        
        # Determine turn range for the compressed summary
        turn_range_start = turns_to_summarize[0].turn_range_start
        turn_range_end = turns_to_summarize[-1].turn_range_end
        
        # Write compressed summary back to memory_summaries
        await write_memory(
            db=db,
            session_id=session_id,
            turn_range_start=turn_range_start,
            turn_range_end=turn_range_end,
            summary_text=compressed_summary.strip(),
        )
    
    def _extract_entities(self, query: str, response: str) -> list[str]:
        """
        Extract key entities from query and response text.
        
        Entities include:
        - Company names (capitalized words, common stock tickers)
        - Financial terms (revenue, profit, margin, etc.)
        - Time periods (FY2023, Q1, 2024, etc.)
        
        Args:
            query: User's query text
            response: Agent's response text
        
        Returns:
            List of extracted entity strings
        """
        combined_text = f"{query} {response}"
        entities = []
        
        # Extract company names (common patterns)
        company_pattern = r'\b(?:Apple|Microsoft|Google|Amazon|Tesla|AAPL|MSFT|GOOGL|AMZN|TSLA)\b'
        companies = re.findall(company_pattern, combined_text, re.IGNORECASE)
        entities.extend(set(companies))
        
        # Extract financial terms
        financial_terms = [
            'revenue', 'profit', 'income', 'margin', 'earnings', 'EPS',
            'EBITDA', 'cash flow', 'assets', 'liabilities', 'equity'
        ]
        for term in financial_terms:
            if term.lower() in combined_text.lower():
                entities.append(term)
        
        # Extract time periods
        time_pattern = r'\b(?:FY\s*\d{4}|Q[1-4]\s*\d{4}|\d{4})\b'
        time_periods = re.findall(time_pattern, combined_text, re.IGNORECASE)
        entities.extend(set(time_periods))
        
        return list(set(entities))  # Remove duplicates
    
    def _format_raw_turn(
        self,
        turn_num: int,
        query: str,
        response: str,
        entities: list[str],
    ) -> str:
        """
        Format a raw turn for storage in memory_summaries.
        
        Args:
            turn_num: Turn number
            query: User's query text
            response: Agent's response text
            entities: Extracted entities
        
        Returns:
            Formatted summary text
        """
        entities_str = ", ".join(entities) if entities else "none"
        
        summary = f"""Turn {turn_num}
[Entities: {entities_str}]
Query: {query}
Response: {response[:200]}{"..." if len(response) > 200 else ""}"""
        
        return summary
