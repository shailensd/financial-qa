import { useState, useEffect, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { getHistory } from '../services/api';

/**
 * Custom React hook for managing session state
 * 
 * Responsibilities:
 * - Generate and persist session_id in localStorage
 * - Fetch session history from backend API
 * - Parse and expose memory summary and recent turns
 * - Provide refresh() function to reload session data
 * 
 * @returns {Object} Session state and controls
 * @returns {string} sessionId - Current session UUID
 * @returns {string|null} memorySummary - Compressed LLM summary of prior turns
 * @returns {Array} recentTurns - Last 2-5 query-response pairs
 * @returns {Function} refresh - Function to reload session data from backend
 * @returns {boolean} loading - Loading state for history fetch
 * @returns {Error|null} error - Error object if fetch fails
 */
const useSession = () => {
  const [sessionId, setSessionId] = useState(null);
  const [memorySummary, setMemorySummary] = useState(null);
  const [recentTurns, setRecentTurns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Initialize or retrieve session_id from localStorage
  useEffect(() => {
    let storedSessionId = localStorage.getItem('session_id');
    
    if (!storedSessionId) {
      // Generate new UUID if none exists
      storedSessionId = uuidv4();
      localStorage.setItem('session_id', storedSessionId);
    }
    
    setSessionId(storedSessionId);
  }, []);

  /**
   * Fetch session history from backend and parse memory data
   * Extracts memory summary and recent turns from the response
   */
  const refresh = useCallback(async () => {
    if (!sessionId) {
      return; // Wait for sessionId to be initialized
    }

    setLoading(true);
    setError(null);

    try {
      // /history returns { session_id: str, turns: HistoryTurn[] }
      // HistoryTurn: { query_id, query_text, timestamp, model_used,
      //                response_text, confidence_score, refusal_flag, repair_count }
      const historyData = await getHistory(sessionId);

      // Memory summary is not returned by /history; clear it.
      // (It is stored in memory_summaries table but not yet exposed via this endpoint.)
      setMemorySummary(null);

      // Parse recent turns from `turns` array (last 5, most recent last)
      const turns = historyData.turns ?? [];
      const lastFiveTurns = turns.slice(-5).map((turn) => ({
        query_id:        turn.query_id,
        query_text:      turn.query_text,
        timestamp:       turn.timestamp,
        confidence_score: turn.confidence_score ?? 0,
        refusal_flag:    turn.refusal_flag ?? false,
      }));

      setRecentTurns(lastFiveTurns);
    } catch (err) {
      setError(err);
      console.error('Failed to fetch session history:', err);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  // Auto-refresh on sessionId initialization
  useEffect(() => {
    if (sessionId) {
      refresh();
    }
  }, [sessionId, refresh]);

  return {
    sessionId,
    memorySummary,
    recentTurns,
    refresh,
    loading,
    error,
  };
};

export default useSession;
