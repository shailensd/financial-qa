import { renderHook, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import useQuery from './useQuery';
import * as api from '../services/api';

// Mock the api module
vi.mock('../services/api', () => ({
  submitQuery: vi.fn(),
}));

describe('useQuery', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should initialize with empty state', () => {
    const { result } = renderHook(() => useQuery());
    
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.results).toEqual([]);
    expect(result.current.history).toEqual([]);
    expect(typeof result.current.submit).toBe('function');
  });

  it('should submit a query successfully and update results', async () => {
    const mockResponse = {
      results: [
        {
          model: 'llama',
          response_text: "Apple's net income in FY2023 was $96.995 billion.",
          confidence_score: 0.92,
          refusal_flag: false,
          refusal_reason: null,
          repair_count: 0,
          citations: [
            {
              chunk_id: 42,
              chunk_text: 'Net income: $96,995 million',
              relevance_score: 0.94,
            },
          ],
          agent_trace: {
            plan: [{ tool: 'LOOKUP', inputs: { entity: 'Apple', attribute: 'net_income' } }],
            tool_results: [],
            critic_verdict: 'approved',
          },
          latency_ms: 2341,
        },
      ],
    };

    api.submitQuery.mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useQuery());

    const payload = {
      session_id: 'test-uuid-1234',
      query_text: "What was Apple's net income in FY2023?",
      models: ['llama'],
      company: 'Apple',
    };

    await act(async () => {
      await result.current.submit(payload);
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.results).toEqual(mockResponse.results);
    expect(result.current.error).toBeNull();
    expect(result.current.history).toHaveLength(1);
    expect(result.current.history[0].query_text).toBe(payload.query_text);
    expect(result.current.history[0].models).toEqual(payload.models);
  });

  it('should handle multi-model queries', async () => {
    const mockResponse = {
      results: [
        {
          model: 'llama',
          response_text: 'Response from Llama',
          confidence_score: 0.90,
          refusal_flag: false,
          refusal_reason: null,
          repair_count: 0,
          citations: [],
          agent_trace: {},
          latency_ms: 2000,
        },
        {
          model: 'gemini',
          response_text: 'Response from Gemini',
          confidence_score: 0.95,
          refusal_flag: false,
          refusal_reason: null,
          repair_count: 0,
          citations: [],
          agent_trace: {},
          latency_ms: 1500,
        },
      ],
    };

    api.submitQuery.mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useQuery());

    const payload = {
      session_id: 'test-uuid-1234',
      query_text: 'What was Apple revenue?',
      models: ['llama', 'gemini'],
      company: 'Apple',
    };

    await act(async () => {
      await result.current.submit(payload);
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.results).toHaveLength(2);
    expect(result.current.results[0].model).toBe('llama');
    expect(result.current.results[1].model).toBe('gemini');
  });

  it('should set loading state during query submission', async () => {
    const mockResponse = {
      results: [
        {
          model: 'llama',
          response_text: 'Test response',
          confidence_score: 0.9,
          refusal_flag: false,
          refusal_reason: null,
          repair_count: 0,
          citations: [],
          agent_trace: {},
          latency_ms: 1000,
        },
      ],
    };

    // Create a promise that we can control
    let resolvePromise;
    const controlledPromise = new Promise((resolve) => {
      resolvePromise = resolve;
    });

    api.submitQuery.mockReturnValue(controlledPromise);

    const { result } = renderHook(() => useQuery());

    const payload = {
      session_id: 'test-uuid-1234',
      query_text: 'Test query',
      models: ['llama'],
      company: 'Apple',
    };

    // Start submission
    act(() => {
      result.current.submit(payload);
    });

    // Check loading state is true
    await waitFor(() => {
      expect(result.current.loading).toBe(true);
    });

    // Resolve the promise
    act(() => {
      resolvePromise(mockResponse);
    });

    // Check loading state is false after completion
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
  });

  it('should handle API errors gracefully', async () => {
    const mockError = new Error('Network error');
    api.submitQuery.mockRejectedValue(mockError);

    const { result } = renderHook(() => useQuery());

    const payload = {
      session_id: 'test-uuid-1234',
      query_text: 'Test query',
      models: ['llama'],
      company: 'Apple',
    };

    await act(async () => {
      await result.current.submit(payload);
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe(mockError);
    expect(result.current.results).toEqual([]);
  });

  it('should validate required session_id', async () => {
    const { result } = renderHook(() => useQuery());

    const payload = {
      // Missing session_id
      query_text: 'Test query',
      models: ['llama'],
      company: 'Apple',
    };

    await act(async () => {
      await result.current.submit(payload);
    });

    expect(result.current.error).toBeTruthy();
    expect(result.current.error.message).toBe('session_id is required');
    expect(api.submitQuery).not.toHaveBeenCalled();
  });

  it('should validate non-empty query_text', async () => {
    const { result } = renderHook(() => useQuery());

    const payload = {
      session_id: 'test-uuid-1234',
      query_text: '   ', // Empty/whitespace only
      models: ['llama'],
      company: 'Apple',
    };

    await act(async () => {
      await result.current.submit(payload);
    });

    expect(result.current.error).toBeTruthy();
    expect(result.current.error.message).toBe('query_text cannot be empty');
    expect(api.submitQuery).not.toHaveBeenCalled();
  });

  it('should validate at least one model is selected', async () => {
    const { result } = renderHook(() => useQuery());

    const payload = {
      session_id: 'test-uuid-1234',
      query_text: 'Test query',
      models: [], // Empty models array
      company: 'Apple',
    };

    await act(async () => {
      await result.current.submit(payload);
    });

    expect(result.current.error).toBeTruthy();
    expect(result.current.error.message).toBe('At least one model must be selected');
    expect(api.submitQuery).not.toHaveBeenCalled();
  });

  it('should clear previous results when submitting a new query', async () => {
    const mockResponse1 = {
      results: [
        {
          model: 'llama',
          response_text: 'First response',
          confidence_score: 0.9,
          refusal_flag: false,
          refusal_reason: null,
          repair_count: 0,
          citations: [],
          agent_trace: {},
          latency_ms: 1000,
        },
      ],
    };

    const mockResponse2 = {
      results: [
        {
          model: 'gemini',
          response_text: 'Second response',
          confidence_score: 0.95,
          refusal_flag: false,
          refusal_reason: null,
          repair_count: 0,
          citations: [],
          agent_trace: {},
          latency_ms: 1500,
        },
      ],
    };

    api.submitQuery.mockResolvedValueOnce(mockResponse1).mockResolvedValueOnce(mockResponse2);

    const { result } = renderHook(() => useQuery());

    // First query
    await act(async () => {
      await result.current.submit({
        session_id: 'test-uuid-1234',
        query_text: 'First query',
        models: ['llama'],
        company: 'Apple',
      });
    });

    await waitFor(() => {
      expect(result.current.results).toEqual(mockResponse1.results);
    });

    // Second query
    await act(async () => {
      await result.current.submit({
        session_id: 'test-uuid-1234',
        query_text: 'Second query',
        models: ['gemini'],
        company: 'Apple',
      });
    });

    await waitFor(() => {
      expect(result.current.results).toEqual(mockResponse2.results);
    });

    // History should contain both queries
    expect(result.current.history).toHaveLength(2);
  });

  it('should maintain query history across multiple submissions', async () => {
    const mockResponse = {
      results: [
        {
          model: 'llama',
          response_text: 'Test response',
          confidence_score: 0.9,
          refusal_flag: false,
          refusal_reason: null,
          repair_count: 0,
          citations: [],
          agent_trace: {},
          latency_ms: 1000,
        },
      ],
    };

    api.submitQuery.mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useQuery());

    // Submit three queries
    for (let i = 1; i <= 3; i++) {
      await act(async () => {
        await result.current.submit({
          session_id: 'test-uuid-1234',
          query_text: `Query ${i}`,
          models: ['llama'],
          company: 'Apple',
        });
      });
    }

    await waitFor(() => {
      expect(result.current.history).toHaveLength(3);
    });

    expect(result.current.history[0].query_text).toBe('Query 1');
    expect(result.current.history[1].query_text).toBe('Query 2');
    expect(result.current.history[2].query_text).toBe('Query 3');
  });

  it('should handle refusal responses', async () => {
    const mockResponse = {
      results: [
        {
          model: 'llama',
          response_text: 'I cannot provide investment advice.',
          confidence_score: 0.0,
          refusal_flag: true,
          refusal_reason: 'investment_advice_prohibited',
          repair_count: 0,
          citations: [],
          agent_trace: {},
          latency_ms: 500,
        },
      ],
    };

    api.submitQuery.mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useQuery());

    await act(async () => {
      await result.current.submit({
        session_id: 'test-uuid-1234',
        query_text: 'Should I buy Apple stock?',
        models: ['llama'],
        company: 'Apple',
      });
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.results[0].refusal_flag).toBe(true);
    expect(result.current.results[0].refusal_reason).toBe('investment_advice_prohibited');
  });

  it('should handle invalid response format', async () => {
    const invalidResponse = {
      // Missing results array
      data: 'some data',
    };

    api.submitQuery.mockResolvedValue(invalidResponse);

    const { result } = renderHook(() => useQuery());

    await act(async () => {
      await result.current.submit({
        session_id: 'test-uuid-1234',
        query_text: 'Test query',
        models: ['llama'],
        company: 'Apple',
      });
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBeTruthy();
    expect(result.current.error.message).toBe('Invalid response format: missing results array');
    expect(result.current.results).toEqual([]);
  });

  it('should clear error state on successful submission', async () => {
    const mockError = new Error('Network error');
    const mockResponse = {
      results: [
        {
          model: 'llama',
          response_text: 'Success response',
          confidence_score: 0.9,
          refusal_flag: false,
          refusal_reason: null,
          repair_count: 0,
          citations: [],
          agent_trace: {},
          latency_ms: 1000,
        },
      ],
    };

    api.submitQuery.mockRejectedValueOnce(mockError).mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useQuery());

    // First submission fails
    await act(async () => {
      await result.current.submit({
        session_id: 'test-uuid-1234',
        query_text: 'First query',
        models: ['llama'],
        company: 'Apple',
      });
    });

    await waitFor(() => {
      expect(result.current.error).toBe(mockError);
    });

    // Second submission succeeds
    await act(async () => {
      await result.current.submit({
        session_id: 'test-uuid-1234',
        query_text: 'Second query',
        models: ['llama'],
        company: 'Apple',
      });
    });

    await waitFor(() => {
      expect(result.current.error).toBeNull();
      expect(result.current.results).toEqual(mockResponse.results);
    });
  });
});
