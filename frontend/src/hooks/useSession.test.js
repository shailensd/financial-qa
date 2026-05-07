import { renderHook, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import useSession from './useSession';
import * as api from '../services/api';

// Mock the api module
vi.mock('../services/api', () => ({
  getHistory: vi.fn(),
}));

describe('useSession', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    vi.clearAllMocks();
    
    // Default mock implementation to prevent errors
    api.getHistory.mockResolvedValue({
      memory_summaries: [],
      queries: [],
    });
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('should generate and persist a new session_id if none exists', async () => {
    const { result } = renderHook(() => useSession());
    
    await waitFor(() => {
      expect(result.current.sessionId).toBeTruthy();
      expect(result.current.loading).toBe(false);
    });
    
    // Verify it's a valid UUID format
    expect(result.current.sessionId).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
  });

  it('should retrieve existing session_id from localStorage', async () => {
    const existingId = 'existing-uuid-5678';
    localStorage.setItem('session_id', existingId);
    
    const { result } = renderHook(() => useSession());
    
    await waitFor(() => {
      expect(result.current.sessionId).toBeTruthy();
      expect(result.current.loading).toBe(false);
    });
    
    // The hook should use the existing ID
    expect(result.current.sessionId).toBe(existingId);
  });

  it('should fetch and parse session history on mount', async () => {
    const mockHistoryData = {
      memory_summaries: [
        {
          id: 1,
          session_id: 'test-uuid-1234',
          turn_range_start: 1,
          turn_range_end: 5,
          summary_text: 'User asked about Apple revenue in FY2023.',
        },
      ],
      queries: [
        {
          id: 1,
          query_text: 'What was Apple revenue in FY2023?',
          timestamp: '2024-01-01T10:00:00Z',
          response: {
            response_text: 'Apple revenue was $383.3B in FY2023.',
            confidence_score: 0.95,
            refusal_flag: false,
          },
        },
      ],
    };

    api.getHistory.mockResolvedValue(mockHistoryData);

    const { result } = renderHook(() => useSession());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.memorySummary).toBe('User asked about Apple revenue in FY2023.');
    expect(result.current.recentTurns).toHaveLength(1);
    expect(result.current.recentTurns[0].query_text).toBe('What was Apple revenue in FY2023?');
    expect(result.current.recentTurns[0].response_text).toBe('Apple revenue was $383.3B in FY2023.');
  });

  it('should handle empty history gracefully', async () => {
    const mockHistoryData = {
      memory_summaries: [],
      queries: [],
    };

    api.getHistory.mockResolvedValue(mockHistoryData);

    const { result } = renderHook(() => useSession());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.memorySummary).toBeNull();
    expect(result.current.recentTurns).toHaveLength(0);
  });

  it('should limit recent turns to last 5', async () => {
    const mockHistoryData = {
      memory_summaries: [],
      queries: Array.from({ length: 10 }, (_, i) => ({
        id: i + 1,
        query_text: `Query ${i + 1}`,
        timestamp: `2024-01-01T10:${i}:00Z`,
        response: {
          response_text: `Response ${i + 1}`,
          confidence_score: 0.9,
          refusal_flag: false,
        },
      })),
    };

    api.getHistory.mockResolvedValue(mockHistoryData);

    const { result } = renderHook(() => useSession());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.recentTurns).toHaveLength(5);
    expect(result.current.recentTurns[0].query_text).toBe('Query 6');
    expect(result.current.recentTurns[4].query_text).toBe('Query 10');
  });

  it('should handle API errors gracefully', async () => {
    const mockError = new Error('Network error');
    api.getHistory.mockRejectedValue(mockError);

    const { result } = renderHook(() => useSession());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe(mockError);
    expect(result.current.memorySummary).toBeNull();
    expect(result.current.recentTurns).toHaveLength(0);
  });

  it('should allow manual refresh of session data', async () => {
    const mockHistoryData = {
      memory_summaries: [
        {
          summary_text: 'Initial summary',
        },
      ],
      queries: [],
    };

    api.getHistory.mockResolvedValue(mockHistoryData);

    const { result } = renderHook(() => useSession());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.memorySummary).toBe('Initial summary');

    // Update mock data
    const updatedHistoryData = {
      memory_summaries: [
        {
          summary_text: 'Updated summary',
        },
      ],
      queries: [],
    };

    api.getHistory.mockResolvedValue(updatedHistoryData);

    // Call refresh
    await act(async () => {
      await result.current.refresh();
    });

    await waitFor(() => {
      expect(result.current.memorySummary).toBe('Updated summary');
    });
  });

  it('should handle queries without responses', async () => {
    const mockHistoryData = {
      memory_summaries: [],
      queries: [
        {
          id: 1,
          query_text: 'Test query',
          timestamp: '2024-01-01T10:00:00Z',
          // No response field
        },
      ],
    };

    api.getHistory.mockResolvedValue(mockHistoryData);

    const { result } = renderHook(() => useSession());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.recentTurns).toHaveLength(1);
    expect(result.current.recentTurns[0].response_text).toBe('No response');
    expect(result.current.recentTurns[0].confidence_score).toBe(0);
  });
});
