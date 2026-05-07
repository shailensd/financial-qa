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
      const historyData = await getHistory(sessionId);
      
      // Parse memory summary from history data
      // The backend returns memory_summaries array with compressed summaries
      if (historyData.memory_summaries && historyData.memory_summaries.length > 0) {
        // Get the most recent memory summary
        const latestSummary = historyData.memory_summaries[historyData.memory_summaries.length - 1];
        setMemorySummary(latestSummary.summary_text);
      } else {
        setMemorySummary(null);
      }

      // Parse recent turns (query-response pairs)
      // The backend returns queries with their associated responses
      if (historyData.queries && historyData.queries.length > 0) {
        // Get last 5 turns (or fewer if less than 5 exist)
        const lastFiveTurns = historyData.queries.slice(-5).map((query) => ({
          query_id: query.id,
          query_text: query.query_text,
          timestamp: query.timestamp,
          response_text: query.response?.response_text || 'No response',
          confidence_score: query.response?.confidence_score || 0,
          refusal_flag: query.response?.refusal_flag || false,
        }));
        
        setRecentTurns(lastFiveTurns);
      } else {
        setRecentTurns([]);
      }
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
