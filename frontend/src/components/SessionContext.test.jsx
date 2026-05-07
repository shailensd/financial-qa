import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import SessionContext from './SessionContext';
import useSession from '../hooks/useSession';

// Mock the useSession hook
vi.mock('../hooks/useSession');

describe('SessionContext Component', () => {
  const mockRefresh = vi.fn();

  const defaultSessionData = {
    sessionId: 'test-session-123',
    memorySummary: 'This is a test memory summary of the conversation.',
    recentTurns: [
      {
        query_id: 1,
        query_text: 'What is Apple revenue?',
        timestamp: '2024-01-15T10:30:00Z',
        response_text: 'Apple revenue was $383.3B in FY2023.',
        confidence_score: 0.92,
        refusal_flag: false,
      },
      {
        query_id: 2,
        query_text: 'What about Microsoft?',
        timestamp: '2024-01-15T10:31:00Z',
        response_text: 'Microsoft revenue was $211.9B in FY2023.',
        confidence_score: 0.88,
        refusal_flag: false,
      },
    ],
    refresh: mockRefresh,
    loading: false,
    error: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    useSession.mockReturnValue(defaultSessionData);
  });

  describe('Rendering', () => {
    it('should render the component with session data', () => {
      render(<SessionContext />);

      expect(screen.getByText('Session Context')).toBeInTheDocument();
      expect(screen.getByText('Session ID')).toBeInTheDocument();
      expect(screen.getByText('Memory Summary')).toBeInTheDocument();
      expect(screen.getByText(/Recent Turns/)).toBeInTheDocument();
    });

    it('should display session ID', () => {
      render(<SessionContext />);

      expect(screen.getByText('test-session-123')).toBeInTheDocument();
    });

    it('should display memory summary', () => {
      render(<SessionContext />);

      expect(
        screen.getByText('This is a test memory summary of the conversation.')
      ).toBeInTheDocument();
    });

    it('should display recent turns', () => {
      render(<SessionContext />);

      expect(screen.getByText(/What is Apple revenue/)).toBeInTheDocument();
      expect(screen.getByText(/Apple revenue was \$383.3B/)).toBeInTheDocument();
      expect(screen.getByText(/What about Microsoft/)).toBeInTheDocument();
      expect(screen.getByText(/Microsoft revenue was \$211.9B/)).toBeInTheDocument();
    });

    it('should display turn numbers correctly', () => {
      render(<SessionContext />);

      // With 2 turns, should show Turn 2 and Turn 1
      expect(screen.getByText('Turn 2')).toBeInTheDocument();
      expect(screen.getByText('Turn 1')).toBeInTheDocument();
    });

    it('should display confidence scores', () => {
      render(<SessionContext />);

      expect(screen.getByText('92%')).toBeInTheDocument();
      expect(screen.getByText('88%')).toBeInTheDocument();
    });
  });

  describe('Empty States', () => {
    it('should show loading state when sessionId is not available', () => {
      useSession.mockReturnValue({
        ...defaultSessionData,
        sessionId: null,
      });

      render(<SessionContext />);

      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('should show empty state when no memory summary exists', () => {
      useSession.mockReturnValue({
        ...defaultSessionData,
        memorySummary: null,
      });

      render(<SessionContext />);

      expect(
        screen.getByText(/No memory summary available yet/)
      ).toBeInTheDocument();
    });

    it('should show empty state when no recent turns exist', () => {
      useSession.mockReturnValue({
        ...defaultSessionData,
        recentTurns: [],
      });

      render(<SessionContext />);

      expect(
        screen.getByText(/No conversation history yet/)
      ).toBeInTheDocument();
    });

    it('should show loading spinner when loading memory summary', () => {
      useSession.mockReturnValue({
        ...defaultSessionData,
        memorySummary: null,
        loading: true,
      });

      const { container } = render(<SessionContext />);

      const spinner = container.querySelector('.animate-spin.border-purple-600');
      expect(spinner).toBeInTheDocument();
    });

    it('should show loading spinner when loading recent turns', () => {
      useSession.mockReturnValue({
        ...defaultSessionData,
        recentTurns: [],
        loading: true,
      });

      const { container } = render(<SessionContext />);

      const spinner = container.querySelector('.animate-spin.border-blue-600');
      expect(spinner).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('should display error message when error occurs', () => {
      useSession.mockReturnValue({
        ...defaultSessionData,
        error: { message: 'Failed to fetch session data' },
      });

      render(<SessionContext />);

      expect(
        screen.getByText(/Failed to load session data: Failed to fetch session data/)
      ).toBeInTheDocument();
    });
  });

  describe('Interactions', () => {
    it('should call refresh when refresh button is clicked', () => {
      render(<SessionContext />);

      const refreshButton = screen.getByTitle('Refresh session data');
      fireEvent.click(refreshButton);

      expect(mockRefresh).toHaveBeenCalledTimes(1);
    });

    it('should disable refresh button when loading', () => {
      useSession.mockReturnValue({
        ...defaultSessionData,
        loading: true,
      });

      render(<SessionContext />);

      const refreshButton = screen.getByTitle('Refresh session data');
      expect(refreshButton).toBeDisabled();
    });

    it('should show spinning icon when loading', () => {
      useSession.mockReturnValue({
        ...defaultSessionData,
        loading: true,
      });

      render(<SessionContext />);

      const refreshButton = screen.getByTitle('Refresh session data');
      const svg = refreshButton.querySelector('svg');
      expect(svg).toHaveClass('animate-spin');
    });
  });

  describe('Auto-refresh', () => {
    it('should call refresh when autoRefresh prop changes to true', async () => {
      const { rerender } = render(<SessionContext autoRefresh={false} />);

      expect(mockRefresh).not.toHaveBeenCalled();

      rerender(<SessionContext autoRefresh={true} />);

      await waitFor(() => {
        expect(mockRefresh).toHaveBeenCalledTimes(1);
      });
    });

    it('should not call refresh when autoRefresh is false', () => {
      render(<SessionContext autoRefresh={false} />);

      expect(mockRefresh).not.toHaveBeenCalled();
    });

    it('should not call refresh when sessionId is not available', () => {
      useSession.mockReturnValue({
        ...defaultSessionData,
        sessionId: null,
      });

      render(<SessionContext autoRefresh={true} />);

      expect(mockRefresh).not.toHaveBeenCalled();
    });
  });

  describe('Refusal Badge', () => {
    it('should display refusal badge when refusal_flag is true', () => {
      useSession.mockReturnValue({
        ...defaultSessionData,
        recentTurns: [
          {
            query_id: 1,
            query_text: 'Should I buy Apple stock?',
            timestamp: '2024-01-15T10:30:00Z',
            response_text: 'I cannot provide investment advice.',
            confidence_score: 0,
            refusal_flag: true,
          },
        ],
      });

      render(<SessionContext />);

      expect(screen.getByText('Refused')).toBeInTheDocument();
    });

    it('should not display refusal badge when refusal_flag is false', () => {
      render(<SessionContext />);

      expect(screen.queryByText('Refused')).not.toBeInTheDocument();
    });
  });

  describe('Text Truncation', () => {
    it('should truncate long query text', () => {
      const longQuery = 'A'.repeat(150);
      useSession.mockReturnValue({
        ...defaultSessionData,
        recentTurns: [
          {
            query_id: 1,
            query_text: longQuery,
            timestamp: '2024-01-15T10:30:00Z',
            response_text: 'Short response',
            confidence_score: 0.9,
            refusal_flag: false,
          },
        ],
      });

      render(<SessionContext />);

      const displayedText = screen.getByText(/A{100,120}\.\.\./);
      expect(displayedText).toBeInTheDocument();
      expect(displayedText.textContent.length).toBeLessThan(longQuery.length);
    });

    it('should truncate long response text', () => {
      const longResponse = 'B'.repeat(150);
      useSession.mockReturnValue({
        ...defaultSessionData,
        recentTurns: [
          {
            query_id: 1,
            query_text: 'Short query',
            timestamp: '2024-01-15T10:30:00Z',
            response_text: longResponse,
            confidence_score: 0.9,
            refusal_flag: false,
          },
        ],
      });

      render(<SessionContext />);

      const displayedText = screen.getByText(/B{100,120}\.\.\./);
      expect(displayedText).toBeInTheDocument();
      expect(displayedText.textContent.length).toBeLessThan(longResponse.length);
    });
  });

  describe('Timestamp Formatting', () => {
    it('should format timestamps correctly', () => {
      render(<SessionContext />);

      // Check that timestamps are displayed (exact format may vary by locale)
      const timestamps = screen.getAllByText(/Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec/);
      expect(timestamps.length).toBeGreaterThan(0);
    });

    it('should handle missing timestamps', () => {
      useSession.mockReturnValue({
        ...defaultSessionData,
        recentTurns: [
          {
            query_id: 1,
            query_text: 'Test query',
            timestamp: null,
            response_text: 'Test response',
            confidence_score: 0.9,
            refusal_flag: false,
          },
        ],
      });

      render(<SessionContext />);

      expect(screen.getByText('N/A')).toBeInTheDocument();
    });
  });

  describe('Confidence Score Colors', () => {
    it('should show green badge for high confidence (>= 0.8)', () => {
      useSession.mockReturnValue({
        ...defaultSessionData,
        recentTurns: [
          {
            query_id: 1,
            query_text: 'Test',
            timestamp: '2024-01-15T10:30:00Z',
            response_text: 'Test',
            confidence_score: 0.9,
            refusal_flag: false,
          },
        ],
      });

      render(<SessionContext />);

      const badge = screen.getByText('90%');
      expect(badge).toHaveClass('bg-green-100', 'text-green-800');
    });

    it('should show yellow badge for medium confidence (0.5-0.8)', () => {
      useSession.mockReturnValue({
        ...defaultSessionData,
        recentTurns: [
          {
            query_id: 1,
            query_text: 'Test',
            timestamp: '2024-01-15T10:30:00Z',
            response_text: 'Test',
            confidence_score: 0.6,
            refusal_flag: false,
          },
        ],
      });

      render(<SessionContext />);

      const badge = screen.getByText('60%');
      expect(badge).toHaveClass('bg-yellow-100', 'text-yellow-800');
    });

    it('should show red badge for low confidence (< 0.5)', () => {
      useSession.mockReturnValue({
        ...defaultSessionData,
        recentTurns: [
          {
            query_id: 1,
            query_text: 'Test',
            timestamp: '2024-01-15T10:30:00Z',
            response_text: 'Test',
            confidence_score: 0.3,
            refusal_flag: false,
          },
        ],
      });

      render(<SessionContext />);

      const badge = screen.getByText('30%');
      expect(badge).toHaveClass('bg-red-100', 'text-red-800');
    });

    it('should not show confidence badge when score is 0', () => {
      useSession.mockReturnValue({
        ...defaultSessionData,
        recentTurns: [
          {
            query_id: 1,
            query_text: 'Test',
            timestamp: '2024-01-15T10:30:00Z',
            response_text: 'Test',
            confidence_score: 0,
            refusal_flag: false,
          },
        ],
      });

      render(<SessionContext />);

      expect(screen.queryByText('0%')).not.toBeInTheDocument();
    });
  });
});
