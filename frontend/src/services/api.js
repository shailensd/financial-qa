import axios from 'axios';

// Create Axios instance with base configuration
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000, // 30 second timeout for LLM operations
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach session_id header from localStorage
api.interceptors.request.use(
  (config) => {
    const sessionId = localStorage.getItem('session_id');
    if (sessionId) {
      config.headers['X-Session-ID'] = sessionId;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor: normalize errors to consistent format
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // Normalize error structure
    const normalizedError = {
      message: 'An unexpected error occurred',
      status: error.response?.status || 500,
      data: error.response?.data || null,
    };

    // Extract error message from various possible locations
    if (error.response?.data?.detail) {
      normalizedError.message = error.response.data.detail;
    } else if (error.response?.data?.message) {
      normalizedError.message = error.response.data.message;
    } else if (error.message) {
      normalizedError.message = error.message;
    }

    // Handle specific error cases
    if (error.code === 'ECONNABORTED') {
      normalizedError.message = 'Request timeout - the server took too long to respond';
    } else if (error.code === 'ERR_NETWORK') {
      normalizedError.message = 'Network error - unable to reach the server';
    }

    return Promise.reject(normalizedError);
  }
);

/**
 * Submit a query to the backend
 * @param {Object} payload - Query payload
 * @param {string} payload.session_id - Session UUID
 * @param {string} payload.query_text - User's question
 * @param {string[]} payload.models - Array of model names (e.g., ["llama", "gemini"])
 * @param {string} payload.company - Company name (e.g., "Apple")
 * @returns {Promise<Object>} Response with results array
 */
export const submitQuery = async (payload) => {
  const response = await api.post('/query', payload);
  return response.data;
};

/**
 * Get query history for a session
 * @param {string} sessionId - Session UUID
 * @returns {Promise<Object>} History data with queries and responses
 */
export const getHistory = async (sessionId) => {
  const response = await api.get('/history', {
    params: { session_id: sessionId },
  });
  return response.data;
};

/**
 * Run evaluation framework
 * @returns {Promise<Object>} Evaluation results with Ragas metrics
 */
export const runEvaluation = async () => {
  const response = await api.post('/evaluate');
  return response.data;
};

/**
 * Get structured logs for a session
 * @param {string} sessionId - Session UUID (optional)
 * @returns {Promise<Object>} Log entries
 */
export const getLogs = async (sessionId = null) => {
  const params = {};
  if (sessionId) {
    params.session_id = sessionId;
  }
  const response = await api.get('/logs', { params });
  return response.data;
};

/**
 * Health check endpoint
 * @returns {Promise<Object>} Health status
 */
export const checkHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

export default api;
