import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from './App';
import * as useQueryModule from './hooks/useQuery';
import * as useSessionModule from './hooks/useSession';

// ── Mock hooks ────────────────────────────────────────────────────────────────

vi.mock('./hooks/useQuery');
vi.mock('./hooks/useSession');

// ── Mock child components (keep tests focused on App logic) ───────────────────

vi.mock('./components/QueryInput', () => ({
  default: ({ sessionId, loading }) => (
    <div data-testid="query-input">
      QueryInput sid={sessionId} loading={loading.toString()}
    </div>
  ),
}));

vi.mock('./components/SessionContext', () => ({
  default: () => <div data-testid="session-context">SessionContext</div>,
}));

vi.mock('./components/CitationList', () => ({
  default: ({ citations }) => (
    <div data-testid="citation-list">citations:{citations?.length ?? 0}</div>
  ),
}));

vi.mock('./components/AgentTrace', () => ({
  default: ({ agentTrace }) => (
    <div data-testid="agent-trace">trace:{agentTrace ? 'yes' : 'no'}</div>
  ),
}));

// ── Fixtures ──────────────────────────────────────────────────────────────────

const BASE_QUERY = {
  submit: vi.fn(),
  loading: false,
  error: null,
  results: [],
};

const BASE_SESSION = {
  sessionId: 'test-session-123',
  memorySummary: null,
  recentTurns: [],
  refresh: vi.fn(),
  loading: false,
  error: null,
};

const MOCK_RESULT = {
  model: 'gemini',
  response_text: 'Apple revenue was $383B in FY2023.',
  confidence_score: 0.9,
  refusal_flag: false,
  refusal_reason: null,
  repair_count: 0,
  latency_ms: 1200,
  citations: [{ chunk_id: 1, chunk_text: 'Net sales $383,285M', relevance_score: 0.95 }],
  agent_trace: {
    plan: [{ tool: 'LOOKUP', inputs: { entity: 'Apple', attribute: 'revenue' } }],
    tool_results: [],
    critic_verdict: 'approved',
  },
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(useQueryModule, 'default').mockReturnValue(BASE_QUERY);
    vi.spyOn(useSessionModule, 'default').mockReturnValue(BASE_SESSION);
  });

  it('renders app header with product name', () => {
    render(<App />);
    expect(screen.getByText('FinDoc Intelligence')).toBeInTheDocument();
  });

  it('renders the session sidebar', () => {
    render(<App />);
    expect(screen.getByTestId('session-context')).toBeInTheDocument();
  });

  it('renders QueryInput when sessionId is available', () => {
    render(<App />);
    const qi = screen.getByTestId('query-input');
    expect(qi).toBeInTheDocument();
    expect(qi).toHaveTextContent('test-session-123');
  });

  it('does NOT render QueryInput when sessionId is null', () => {
    vi.spyOn(useSessionModule, 'default').mockReturnValue({
      ...BASE_SESSION,
      sessionId: null,
    });
    render(<App />);
    expect(screen.queryByTestId('query-input')).not.toBeInTheDocument();
  });

  it('shows welcome empty state when there are no results', () => {
    render(<App />);
    expect(screen.getByText('Welcome to FinDoc Intelligence')).toBeInTheDocument();
  });

  it('shows loading indicator while query is running', () => {
    vi.spyOn(useQueryModule, 'default').mockReturnValue({
      ...BASE_QUERY,
      loading: true,
    });
    render(<App />);
    // The loading spinner / message should appear and the empty state should not
    expect(screen.queryByText('Welcome to FinDoc Intelligence')).not.toBeInTheDocument();
  });

  it('shows an error banner when the query hook reports an error', () => {
    vi.spyOn(useQueryModule, 'default').mockReturnValue({
      ...BASE_QUERY,
      error: new Error('LLM timeout'),
    });
    render(<App />);
    expect(screen.getByText('LLM timeout')).toBeInTheDocument();
  });

  it('renders result cards when results are present', () => {
    vi.spyOn(useQueryModule, 'default').mockReturnValue({
      ...BASE_QUERY,
      results: [MOCK_RESULT],
    });
    render(<App />);
    // Response text should be visible inside the result card
    expect(screen.getByText('Apple revenue was $383B in FY2023.')).toBeInTheDocument();
  });

  it('renders CitationList inside result card when citations exist', () => {
    vi.spyOn(useQueryModule, 'default').mockReturnValue({
      ...BASE_QUERY,
      results: [MOCK_RESULT],
    });
    render(<App />);
    const cl = screen.getByTestId('citation-list');
    expect(cl).toBeInTheDocument();
    expect(cl).toHaveTextContent('citations:1');
  });

  it('renders AgentTrace inside result card when trace exists', () => {
    vi.spyOn(useQueryModule, 'default').mockReturnValue({
      ...BASE_QUERY,
      results: [MOCK_RESULT],
    });
    render(<App />);
    expect(screen.getByTestId('agent-trace')).toHaveTextContent('trace:yes');
  });

  it('renders multiple result cards for multiple models', () => {
    const results = [
      { ...MOCK_RESULT, model: 'gemini' },
      { ...MOCK_RESULT, model: 'llama', citations: [], agent_trace: null },
    ];
    vi.spyOn(useQueryModule, 'default').mockReturnValue({
      ...BASE_QUERY,
      results,
    });
    render(<App />);
    // Both model labels should appear in the cards
    expect(screen.getByText('Gemini 2.5 Flash')).toBeInTheDocument();
    expect(screen.getByText('Llama 3.2')).toBeInTheDocument();
  });
});
