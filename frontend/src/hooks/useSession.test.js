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
      session_id: 'test-uuid',
      turns: [],
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
      session_id: 'test-uuid-1234',
      turns: [
        {
          query_id: 1,
          query_text: 'What was Apple revenue in FY2023?',
          timestamp: '2024-01-01T10:00:00Z',
          confidence_score: 0.95,
          refusal_flag: false,
        },
      ],
    };

    api.getHistory.mockResolvedValue(mockHistoryData);

    const { result } = renderHook(() => useSession());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.memorySummary).toBeNull();
    expect(result.current.recentTurns).toHaveLength(1);
    expect(result.current.recentTurns[0].query_text).toBe('What was Apple revenue in FY2023?');
    expect(result.current.recentTurns[0].confidence_score).toBe(0.95);
  });

  it('should handle empty history gracefully', async () => {
    const mockHistoryData = {
      session_id: 'test-uuid',
      turns: [],
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
      session_id: 'test-uuid',
      turns: Array.from({ length: 10 }, (_, i) => ({
        query_id: i + 1,
        query_text: `Query ${i + 1}`,
        timestamp: `2024-01-01T10:${i}:00Z`,
        confidence_score: 0.9,
        refusal_flag: false,
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
      session_id: 'test-uuid',
      turns: [
        {
          query_id: 1,
          query_text: 'Initial query',
          timestamp: '2024-01-01T10:00:00Z',
          confidence_score: 0.95,
          refusal_flag: false,
        },
      ],
    };

    api.getHistory.mockResolvedValue(mockHistoryData);

    const { result } = renderHook(() => useSession());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.recentTurns[0].query_text).toBe('Initial query');

    // Update mock data
    const updatedHistoryData = {
      session_id: 'test-uuid',
      turns: [
        {
          query_id: 1,
          query_text: 'Updated query',
          timestamp: '2024-01-01T10:00:00Z',
          confidence_score: 0.95,
          refusal_flag: false,
        },
      ],
    };

    api.getHistory.mockResolvedValue(updatedHistoryData);

    // Call refresh
    await act(async () => {
      await result.current.refresh();
    });

    await waitFor(() => {
      expect(result.current.recentTurns[0].query_text).toBe('Updated query');
    });
  });

  it('should provide default values for missing fields in turns', async () => {
    const mockHistoryData = {
      session_id: 'test-uuid',
      turns: [
        {
          query_id: 1,
          query_text: 'Test query',
          timestamp: '2024-01-01T10:00:00Z',
          // Missing confidence_score and refusal_flag
        },
      ],
    };

    api.getHistory.mockResolvedValue(mockHistoryData);

    const { result } = renderHook(() => useSession());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.recentTurns).toHaveLength(1);
    expect(result.current.recentTurns[0].confidence_score).toBe(0);
    expect(result.current.recentTurns[0].refusal_flag).toBe(false);
  });
});
