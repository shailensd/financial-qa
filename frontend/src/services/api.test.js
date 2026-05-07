/**
 * Basic verification tests for API service
 * These tests verify the structure and configuration of the API service
 */

import { describe, test, expect, beforeEach, vi } from 'vitest';
import api, { submitQuery, getHistory, runEvaluation, getLogs, checkHealth } from './api.js';

describe('API Service Configuration', () => {
  test('Axios instance is configured with correct baseURL', () => {
    expect(api.defaults.baseURL).toBeDefined();
    expect(api.defaults.baseURL).toMatch(/http:\/\/localhost:8000/);
  });

  test('Axios instance has correct timeout', () => {
    expect(api.defaults.timeout).toBe(30000);
  });

  test('Axios instance has correct headers', () => {
    expect(api.defaults.headers['Content-Type']).toBe('application/json');
  });

  test('Request interceptor is configured', () => {
    expect(api.interceptors.request.handlers.length).toBeGreaterThan(0);
  });

  test('Response interceptor is configured', () => {
    expect(api.interceptors.response.handlers.length).toBeGreaterThan(0);
  });
});

describe('API Functions', () => {
  test('submitQuery function is exported', () => {
    expect(typeof submitQuery).toBe('function');
  });

  test('getHistory function is exported', () => {
    expect(typeof getHistory).toBe('function');
  });

  test('runEvaluation function is exported', () => {
    expect(typeof runEvaluation).toBe('function');
  });

  test('getLogs function is exported', () => {
    expect(typeof getLogs).toBe('function');
  });

  test('checkHealth function is exported', () => {
    expect(typeof checkHealth).toBe('function');
  });
});

describe('Request Interceptor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('Attaches session_id from localStorage to request headers', () => {
    const mockSessionId = 'test-session-123';
    localStorage.getItem.mockReturnValue(mockSessionId);

    const config = { headers: {} };
    const interceptor = api.interceptors.request.handlers[0];
    const result = interceptor.fulfilled(config);

    expect(result.headers['X-Session-ID']).toBe(mockSessionId);
  });

  test('Does not add session_id header if not in localStorage', () => {
    localStorage.getItem.mockReturnValue(null);

    const config = { headers: {} };
    const interceptor = api.interceptors.request.handlers[0];
    const result = interceptor.fulfilled(config);

    expect(result.headers['X-Session-ID']).toBeUndefined();
  });
});

describe('Response Interceptor Error Normalization', () => {
  test('Normalizes error with detail field', async () => {
    const mockError = {
      response: {
        status: 400,
        data: { detail: 'Invalid query format' }
      }
    };

    const interceptor = api.interceptors.response.handlers[0];
    
    try {
      await interceptor.rejected(mockError);
    } catch (error) {
      expect(error.message).toBe('Invalid query format');
      expect(error.status).toBe(400);
    }
  });

  test('Normalizes error with message field', async () => {
    const mockError = {
      response: {
        status: 500,
        data: { message: 'Internal server error' }
      }
    };

    const interceptor = api.interceptors.response.handlers[0];
    
    try {
      await interceptor.rejected(mockError);
    } catch (error) {
      expect(error.message).toBe('Internal server error');
      expect(error.status).toBe(500);
    }
  });

  test('Handles timeout errors', async () => {
    const mockError = {
      code: 'ECONNABORTED',
      message: 'timeout of 30000ms exceeded'
    };

    const interceptor = api.interceptors.response.handlers[0];
    
    try {
      await interceptor.rejected(mockError);
    } catch (error) {
      expect(error.message).toContain('timeout');
    }
  });

  test('Handles network errors', async () => {
    const mockError = {
      code: 'ERR_NETWORK',
      message: 'Network Error'
    };

    const interceptor = api.interceptors.response.handlers[0];
    
    try {
      await interceptor.rejected(mockError);
    } catch (error) {
      expect(error.message).toContain('Network error');
    }
  });
});
