import { useState, useCallback } from 'react';
import { submitQuery } from '../services/api';

/**
 * Custom React hook for managing query submission and results
 * 
 * Responsibilities:
 * - Submit queries to the backend via submitQuery() API function
 * - Track loading state during query execution
 * - Handle and expose errors from API calls
 * - Store and expose query results (multi-model responses)
 * - Maintain query history for the current session
 * 
 * @returns {Object} Query state and controls
 * @returns {Function} submit - Function to submit a query payload
 * @returns {boolean} loading - Loading state during query execution
 * @returns {Error|null} error - Error object if submission fails
 * @returns {Array} results - Array of model-specific response objects
 * @returns {Array} history - Array of all queries submitted in this session
 */
const useQuery = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState([]);
  const [history, setHistory] = useState([]);

  /**
   * Submit a query to the backend
   * 
   * @param {Object} payload - Query payload
   * @param {string} payload.session_id - Session UUID
   * @param {string} payload.query_text - User's question
   * @param {string[]} payload.models - Array of model names (e.g., ["llama", "gemini"])
   * @param {string} payload.company - Company name (e.g., "Apple")
   * 
   * Expected response structure:
   * {
   *   results: [
   *     {
   *       model: "llama",
   *       response_text: "Apple's net income...",
   *       confidence_score: 0.92,
   *       refusal_flag: false,
   *       refusal_reason: null,
   *       repair_count: 0,
   *       citations: [
   *         {
   *           chunk_id: 42,
   *           chunk_text: "Net income: $96,995 million",
   *           relevance_score: 0.94
   *         }
   *       ],
   *       agent_trace: {
   *         plan: [...],
   *         tool_results: [...],
   *         critic_verdict: "approved"
   *       },
   *       latency_ms: 2341
   *     }
   *   ]
   * }
   */
  const submit = useCallback(async (payload) => {
    // Validate required fields
    if (!payload.session_id) {
      const validationError = new Error('session_id is required');
      setError(validationError);
      return;
    }
    if (!payload.query_text || payload.query_text.trim() === '') {
      const validationError = new Error('query_text cannot be empty');
      setError(validationError);
      return;
    }
    if (!payload.models || payload.models.length === 0) {
      const validationError = new Error('At least one model must be selected');
      setError(validationError);
      return;
    }

    setLoading(true);
    setError(null);
    setResults([]); // Clear previous results

    try {
      const responseData = await submitQuery(payload);
      
      // Store the results from the response
      if (responseData.results && Array.isArray(responseData.results)) {
        setResults(responseData.results);
        
        // Add this query to the history
        const historyEntry = {
          query_text: payload.query_text,
          models: payload.models,
          company: payload.company,
          timestamp: new Date().toISOString(),
          results: responseData.results,
        };
        
        setHistory((prevHistory) => [...prevHistory, historyEntry]);
      } else {
        throw new Error('Invalid response format: missing results array');
      }
    } catch (err) {
      setError(err);
      console.error('Failed to submit query:', err);
      // Clear results on error
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    submit,
    loading,
    error,
    results,
    history,
  };
};

export default useQuery;
