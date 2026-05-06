"""
Structured logging for FinDoc Intelligence agent pipeline.

This module provides the StructuredLogger class for persisting detailed
execution traces to the database. All log entries are stored as JSON in
the logs table for auditing and debugging.

Security: API keys and credentials are automatically filtered from log entries.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app import crud


logger = logging.getLogger(__name__)


# Sensitive field patterns to filter from logs
SENSITIVE_PATTERNS = [
    r'api[_-]?key',
    r'password',
    r'secret',
    r'token',
    r'credential',
    r'auth',
    r'bearer',
]


class StructuredLogger:
    """
    Structured logger for agent pipeline execution traces.
    
    Builds comprehensive JSON log entries containing all execution details
    and persists them to the database logs table via CRUD operations.
    
    Security: Automatically filters API keys and credentials from log entries.
    """
    
    def __init__(self):
        """Initialize the structured logger."""
        self._sensitive_regex = re.compile(
            '|'.join(SENSITIVE_PATTERNS),
            re.IGNORECASE
        )
    
    def _sanitize_value(self, key: str, value: Any) -> Any:
        """
        Sanitize sensitive values from log entries.
        
        Replaces sensitive field values with "[REDACTED]" to prevent
        API keys and credentials from being logged.
        
        Args:
            key: Field name to check for sensitivity
            value: Field value to potentially sanitize
        
        Returns:
            Original value if not sensitive, "[REDACTED]" if sensitive
        """
        # Check if key matches any sensitive pattern
        if self._sensitive_regex.search(key):
            return "[REDACTED]"
        
        # Recursively sanitize nested dictionaries
        if isinstance(value, dict):
            return {
                k: self._sanitize_value(k, v)
                for k, v in value.items()
            }
        
        # Recursively sanitize lists
        if isinstance(value, list):
            return [
                self._sanitize_value(key, item) if isinstance(item, dict) else item
                for item in value
            ]
        
        return value
    
    def _sanitize_log_entry(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize entire log entry to remove sensitive information.
        
        Args:
            log_entry: Raw log entry dictionary
        
        Returns:
            Sanitized log entry with sensitive values redacted
        """
        return {
            key: self._sanitize_value(key, value)
            for key, value in log_entry.items()
        }
    
    async def log_request(
        self,
        db: AsyncSession,
        session_id: str,
        query_id: int,
        query_text: str,
        model_used: str,
        plan: List[Dict[str, Any]],
        tool_results: List[Dict[str, Any]],
        chunk_ids: List[int],
        refusal_decision: bool,
        critic_verdict: str,
        repair_count: int,
        total_latency_ms: int,
        refusal_reason: Optional[str] = None,
        confidence_score: Optional[float] = None,
        draft_response: Optional[str] = None,
    ) -> None:
        """
        Log a complete agent pipeline execution to the database.
        
        Builds a comprehensive JSON log entry containing all execution details
        and persists it to the logs table via crud.create_log().
        
        Args:
            db: Database session
            session_id: Session identifier
            query_id: Query ID from queries table
            query_text: User's query text
            model_used: LLM model used for this request
            plan: List of tool calls from Planner
            tool_results: List of tool execution results from Executor
            chunk_ids: List of chunk IDs cited in response
            refusal_decision: Whether query was refused by RefusalGuard
            critic_verdict: Critic's verdict (approved/repair_numerical/repair_citation)
            repair_count: Number of repair iterations performed
            total_latency_ms: Total request latency in milliseconds
            refusal_reason: Reason for refusal if applicable
            confidence_score: Critic's confidence score if approved
            draft_response: Generated response text (optional, for debugging)
        
        Returns:
            None
        
        Side Effects:
            - Creates a new log entry in the database
            - Logs errors if database write fails
        """
        # Build raw log entry
        log_entry = {
            "session_id": session_id,
            "query_id": query_id,
            "query_text": query_text,
            "model_used": model_used,
            "plan": plan,
            "tool_results": tool_results,
            "chunk_ids": chunk_ids,
            "refusal_decision": refusal_decision,
            "refusal_reason": refusal_reason,
            "critic_verdict": critic_verdict,
            "repair_count": repair_count,
            "confidence_score": confidence_score,
            "total_latency_ms": total_latency_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Optionally include draft response for debugging
        # (can be large, so only include if provided)
        if draft_response:
            log_entry["draft_response_preview"] = draft_response[:500]  # First 500 chars
        
        # Sanitize sensitive information
        sanitized_log_entry = self._sanitize_log_entry(log_entry)
        
        # Persist to database
        try:
            await crud.create_log(
                db=db,
                session_id=session_id,
                query_id=query_id,
                log_json=sanitized_log_entry,
            )
            
            logger.info(
                f"Structured log persisted for query_id={query_id}, "
                f"session_id={session_id}, model={model_used}"
            )
        
        except Exception as e:
            # Log error but don't raise - logging failures should not break the pipeline
            logger.error(
                f"Failed to persist structured log for query_id={query_id}: {e}",
                exc_info=True
            )
    
    def format_log_for_display(self, log_json: Dict[str, Any]) -> str:
        """
        Format a log entry for human-readable display.
        
        Args:
            log_json: Log entry dictionary from database
        
        Returns:
            Formatted string representation of the log
        """
        lines = [
            "=" * 80,
            f"Session: {log_json.get('session_id', 'N/A')}",
            f"Query: {log_json.get('query_text', 'N/A')}",
            f"Model: {log_json.get('model_used', 'N/A')}",
            f"Timestamp: {log_json.get('timestamp', 'N/A')}",
            "-" * 80,
            f"Refusal: {log_json.get('refusal_decision', False)}",
        ]
        
        if log_json.get('refusal_reason'):
            lines.append(f"Refusal Reason: {log_json['refusal_reason']}")
        
        lines.extend([
            f"Critic Verdict: {log_json.get('critic_verdict', 'N/A')}",
            f"Repair Count: {log_json.get('repair_count', 0)}",
            f"Confidence Score: {log_json.get('confidence_score', 'N/A')}",
            f"Latency: {log_json.get('total_latency_ms', 0)}ms",
            "-" * 80,
            f"Plan ({len(log_json.get('plan', []))} steps):",
        ])
        
        for i, step in enumerate(log_json.get('plan', []), 1):
            lines.append(f"  {i}. {step.get('tool', 'N/A')}: {step.get('inputs', {})}")
        
        lines.append("-" * 80)
        lines.append(f"Tool Results ({len(log_json.get('tool_results', []))}):")
        
        for i, result in enumerate(log_json.get('tool_results', []), 1):
            status = result.get('status', 'unknown')
            tool = result.get('tool', 'N/A')
            lines.append(f"  {i}. {tool} - {status}")
        
        lines.append("-" * 80)
        lines.append(f"Citations: {len(log_json.get('chunk_ids', []))} chunks")
        lines.append("=" * 80)
        
        return "\n".join(lines)


# Global logger instance
structured_logger = StructuredLogger()
