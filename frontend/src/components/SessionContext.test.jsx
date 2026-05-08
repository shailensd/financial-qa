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

      expect(screen.getByText('Session History')).toBeInTheDocument();
      expect(screen.getByText('📝 Memory Summary')).toBeInTheDocument();
      expect(screen.getByText(/Recent Turns/)).toBeInTheDocument();
    });

    it('should display session ID truncated', () => {
      render(<SessionContext />);

      expect(screen.getByText('test-session…')).toBeInTheDocument();
    });

    it('should display memory summary', () => {
      render(<SessionContext />);

      expect(
        screen.getByText('This is a test memory summary of the conversation.')
      ).toBeInTheDocument();
    });

    it('should display recent turns queries', () => {
      render(<SessionContext />);

      expect(screen.getByText('What is Apple revenue?')).toBeInTheDocument();
      expect(screen.getByText('What about Microsoft?')).toBeInTheDocument();
    });

    it('should display confidence scores', () => {
      render(<SessionContext />);

      expect(screen.getByText('92%')).toBeInTheDocument();
      expect(screen.getByText('88%')).toBeInTheDocument();
    });
  });

  describe('Empty States', () => {
    it('should show empty state when no memory summary exists', () => {
      useSession.mockReturnValue({
        ...defaultSessionData,
        memorySummary: null,
      });

      render(<SessionContext />);

      // Memory box should not render if empty
      expect(screen.queryByText('📝 Memory Summary')).not.toBeInTheDocument();
    });

    it('should show empty state when no recent turns exist', () => {
      useSession.mockReturnValue({
        ...defaultSessionData,
        recentTurns: [],
      });

      render(<SessionContext />);

      expect(
        screen.getByText('No turns yet')
      ).toBeInTheDocument();
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
        screen.getByText('Failed to load session data')
      ).toBeInTheDocument();
    });
  });

  describe('Interactions', () => {
    it('should call refresh when refresh button is clicked', () => {
      render(<SessionContext />);

      const refreshButton = screen.getByTitle('Refresh session');
      fireEvent.click(refreshButton);

      expect(mockRefresh).toHaveBeenCalledTimes(1);
    });

    it('should disable refresh button when loading', () => {
      useSession.mockReturnValue({
        ...defaultSessionData,
        loading: true,
      });

      render(<SessionContext />);

      const refreshButton = screen.getByTitle('Refresh session');
      expect(refreshButton).toBeDisabled();
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

      expect(screen.getByText('refused')).toBeInTheDocument();
      expect(screen.getByText('refused')).toHaveClass('badge', 'badge-red');
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
      expect(badge).toHaveClass('badge', 'badge-green');
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
      expect(badge).toHaveClass('badge', 'badge-yellow');
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
      expect(badge).toHaveClass('badge', 'badge-red');
    });
  });
});

