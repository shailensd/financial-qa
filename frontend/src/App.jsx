import { useState } from 'react';
import './App.css';
import QueryInput from './components/QueryInput';
import CitationList from './components/CitationList';
import AgentTrace from './components/AgentTrace';
import SessionContext from './components/SessionContext';
import useQuery from './hooks/useQuery';
import useSession from './hooks/useSession';

/* ── Helpers ─────────────────────────────────────────────────────── */
const MODEL_META = {
  llama:  { label: 'Llama 3.2', icon: '🦙', color: '#fb923c' },
  gemma:  { label: 'Gemma 2',   icon: '💎', color: '#34d399' },
  gemini: { label: 'Gemini 2.5 Flash', icon: '✨', color: '#60a5fa' },
};

function getModelMeta(model) {
  return MODEL_META[model] || { label: model, icon: '🤖', color: '#a78bfa' };
}

function getConfidenceBadge(score) {
  if (score >= 0.8) return 'badge badge-green';
  if (score >= 0.5) return 'badge badge-yellow';
  return 'badge badge-red';
}

/* ── Small icon components ───────────────────────────────────────── */
function IconDoc({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="9" y1="13" x2="15" y2="13" />
      <line x1="9" y1="17" x2="15" y2="17" />
    </svg>
  );
}

function IconChat({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
    </svg>
  );
}

function IconAlertCircle({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

function IconChevron({ open, size = 14 }) {
  return (
    <svg
      width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
      className={`chevron${open ? ' open' : ''}`}
    >
      <path d="M6 9l6 6 6-6" />
    </svg>
  );
}

/* ── Result Card ─────────────────────────────────────────────────── */
function ResultCard({ result }) {
  const [showCitations, setShowCitations] = useState(false);
  const [showTrace, setShowTrace]         = useState(false);
  const meta = getModelMeta(result.model);

  const hasCitations = result.citations && result.citations.length > 0;
  const hasTrace     = result.agent_trace != null;

  return (
    <div className="result-card animate-fade-in">
      {/* Header */}
      <div className="result-card-header">
        <div className="model-name">
          <div className="model-icon" style={{ background: `${meta.color}22` }}>
            <span style={{ fontSize: 12 }}>{meta.icon}</span>
          </div>
          <span>{meta.label}</span>
        </div>

        {/* Confidence */}
        {result.confidence_score != null && (
          <span className={getConfidenceBadge(result.confidence_score)}>
            {(result.confidence_score * 100).toFixed(0)}% conf
          </span>
        )}
      </div>

      {/* Badges row */}
      <div className="result-badges">
        {!result.refusal_flag && result.repair_count === 0 && (
          <span className="badge badge-green">✓ Approved</span>
        )}
        {result.repair_count > 0 && (
          <span className="badge badge-orange">⚠ Repaired ×{result.repair_count}</span>
        )}
        {result.refusal_flag && (
          <span className="badge badge-red">✗ Refused</span>
        )}
        {result.latency_ms != null && (
          <span className="badge badge-gray">⚡ {(result.latency_ms / 1000).toFixed(1)}s</span>
        )}
      </div>

      {/* Response text */}
      <div className="result-body">
        {result.response_text || <em style={{ color: 'var(--text-muted)' }}>No response</em>}
      </div>

      {/* Footer with toggle buttons */}
      {(hasCitations || hasTrace) && (
        <div className="result-footer">
          {hasCitations && (
            <button
              className={`expand-btn${showCitations ? ' active' : ''}`}
              onClick={() => setShowCitations(v => !v)}
            >
              <IconDoc size={12} />
              Citations ({result.citations.length})
              <IconChevron open={showCitations} size={11} />
            </button>
          )}
          {hasTrace && (
            <button
              className={`expand-btn${showTrace ? ' active' : ''}`}
              onClick={() => setShowTrace(v => !v)}
            >
              <IconChat size={12} />
              Agent Trace
              <IconChevron open={showTrace} size={11} />
            </button>
          )}
        </div>
      )}

      {/* Inline citation panel */}
      {hasCitations && showCitations && (
        <div style={{ borderTop: '1px solid var(--border)' }}>
          <CitationList citations={result.citations} inline />
        </div>
      )}

      {/* Inline trace panel */}
      {hasTrace && showTrace && (
        <div style={{ borderTop: '1px solid var(--border)' }}>
          <AgentTrace agentTrace={result.agent_trace} inline />
        </div>
      )}
    </div>
  );
}

/* ── App ─────────────────────────────────────────────────────────── */
function App() {
  const { submit, loading, error, results } = useQuery();
  const { sessionId }                       = useSession();
  const [autoRefresh, setAutoRefresh]       = useState(false);

  const handleQuerySubmit = async (payload) => {
    await submit(payload);
    setAutoRefresh(p => !p);
  };

  const hasResults = !loading && results.length > 0;

  return (
    <div className="app-layout">
      {/* ── Header ─────────────────────────────────────────────── */}
      <header className="app-header">
        <div className="header-logo">
          <div className="logo-icon">
            <IconDoc size={16} />
          </div>
          <div>
            <div className="header-title">FinDoc Intelligence</div>
            <div className="header-subtitle">SEC Filing Q&amp;A · Multi-Model</div>
          </div>
        </div>

        <div className="header-spacer" />

        {sessionId && (
          <div className="session-badge">
            <span className="session-dot" />
            <span>Session</span>
            <span style={{ color: 'var(--brand-400)' }}>
              {sessionId.slice(0, 8)}…
            </span>
          </div>
        )}
      </header>

      {/* ── Body ───────────────────────────────────────────────── */}
      <div className="app-body">
        {/* Sidebar */}
        <aside className="sidebar">
          <SessionContext autoRefresh={autoRefresh} />
        </aside>

        {/* Main */}
        <main className="main-content">
          {/* Error banner */}
          {error && (
            <div className="error-banner">
              <IconAlertCircle size={15} />
              <span>{error.message || 'An unexpected error occurred'}</span>
            </div>
          )}

          {/* Query input */}
          {sessionId && (
            <QueryInput
              onSubmit={handleQuerySubmit}
              loading={loading}
              sessionId={sessionId}
            />
          )}

          {/* Loading */}
          {loading && (
            <div className="loading-card">
              <div className="spinner" />
              <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
                Running multi-model inference…
              </p>
            </div>
          )}

          {/* Results grid */}
          {hasResults && (
            <div className="results-grid">
              {results.map(result => (
                <ResultCard key={result.model} result={result} />
              ))}
            </div>
          )}

          {/* Empty state */}
          {!loading && results.length === 0 && !error && (
            <div className="empty-state">
              <div className="empty-icon">
                <IconDoc size={28} />
              </div>
              <div>
                <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>
                  Welcome to FinDoc Intelligence
                </p>
                <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 6 }}>
                  Select a company, choose your models, and ask a question about SEC filings.
                </p>
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center', marginTop: 4 }}>
                {['What was Apple\'s FY2023 revenue?', 'Summarize Tesla\'s risk factors', 'NVDA gross margin trend'].map(ex => (
                  <span key={ex} style={{
                    padding: '4px 12px',
                    background: 'rgba(99,102,241,0.08)',
                    border: '1px solid rgba(99,102,241,0.2)',
                    borderRadius: 8,
                    fontSize: 12,
                    color: 'var(--brand-400)',
                    cursor: 'default',
                  }}>
                    {ex}
                  </span>
                ))}
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
