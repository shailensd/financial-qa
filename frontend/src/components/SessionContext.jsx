import { useEffect } from 'react';
import PropTypes from 'prop-types';
import useSession from '../hooks/useSession';

function fmtTime(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

function fmtDate(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function truncate(text, max = 80) {
  if (!text || text.length <= max) return text;
  return text.slice(0, max) + '…';
}

function ConfidenceDot({ score }) {
  const color = score >= 0.8 ? 'var(--green)' : score >= 0.5 ? 'var(--yellow)' : 'var(--red)';
  return (
    <span style={{
      width: 7, height: 7, borderRadius: '50%',
      background: color, display: 'inline-block', flexShrink: 0,
    }} title={`${(score * 100).toFixed(0)}% confidence`} />
  );
}

/**
 * SessionContext sidebar panel
 *
 * Shows:
 * - Recent conversation turns
 * - Memory summary
 */
const SessionContext = ({ autoRefresh = false }) => {
  const { sessionId, memorySummary, recentTurns, refresh, loading, error } = useSession();

  useEffect(() => {
    if (autoRefresh && sessionId) refresh();
  }, [autoRefresh, sessionId, refresh]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <div className="sidebar-header">
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>
            Session History
          </div>
          {sessionId && (
            <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
              {sessionId.slice(0, 12)}…
            </div>
          )}
        </div>

        {/* Refresh button */}
        <button
          onClick={() => sessionId && refresh()}
          disabled={loading}
          style={{
            padding: '4px 8px',
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid var(--border)',
            borderRadius: 6,
            fontSize: 11,
            color: loading ? 'var(--text-muted)' : 'var(--text-secondary)',
            cursor: loading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}
          title="Refresh session"
        >
          {loading ? (
            <span style={{
              width: 10, height: 10,
              border: '1.5px solid rgba(255,255,255,0.1)',
              borderTopColor: 'var(--brand-400)',
              borderRadius: '50%',
              animation: 'spin 0.6s linear infinite',
              display: 'inline-block',
            }} />
          ) : (
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="23 4 23 10 17 10" />
              <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10" />
            </svg>
          )}
          Refresh
        </button>
      </div>

      {/* Error */}
      {error && (
        <div style={{
          margin: '8px 12px 0',
          padding: '6px 10px',
          background: 'rgba(248,113,113,0.08)',
          border: '1px solid rgba(248,113,113,0.2)',
          borderRadius: 6,
          fontSize: 11,
          color: 'var(--red)',
        }}>
          Failed to load session data
        </div>
      )}

      {/* Turns */}
      <div className="sidebar-section" style={{ flex: 1 }}>
        <div className="sidebar-section-label">Recent Turns</div>

        {loading && recentTurns.length === 0 ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: '20px 0' }}>
            <span style={{
              width: 18, height: 18,
              border: '2px solid rgba(99,102,241,0.15)',
              borderTopColor: 'var(--brand-500)',
              borderRadius: '50%',
              animation: 'spin 0.7s linear infinite',
              display: 'inline-block',
            }} />
          </div>
        ) : recentTurns.length > 0 ? (
          [...recentTurns].reverse().map((turn, i) => (
            <div key={turn.query_id ?? i} className="turn-card">
              <div className="turn-query">
                {truncate(turn.query_text, 85)}
              </div>
              <div className="turn-meta">
                <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  {turn.confidence_score > 0 && (
                    <ConfidenceDot score={turn.confidence_score} />
                  )}
                  {turn.refusal_flag && (
                    <span className="badge badge-red" style={{ fontSize: 10 }}>refused</span>
                  )}
                  {!turn.refusal_flag && turn.confidence_score >= 0.8 && (
                    <span className="badge badge-green" style={{ fontSize: 10 }}>
                      {(turn.confidence_score * 100).toFixed(0)}%
                    </span>
                  )}
                  {!turn.refusal_flag && turn.confidence_score < 0.8 && turn.confidence_score >= 0.5 && (
                    <span className="badge badge-yellow" style={{ fontSize: 10 }}>
                      {(turn.confidence_score * 100).toFixed(0)}%
                    </span>
                  )}
                  {!turn.refusal_flag && turn.confidence_score < 0.5 && turn.confidence_score > 0 && (
                    <span className="badge badge-red" style={{ fontSize: 10 }}>
                      {(turn.confidence_score * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
                <span className="turn-time">
                  {fmtDate(turn.timestamp)} · {fmtTime(turn.timestamp)}
                </span>
              </div>
            </div>
          ))
        ) : (
          <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-muted)', fontSize: 12 }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
              style={{ margin: '0 auto 8px', display: 'block', opacity: 0.4 }}>
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
            </svg>
            No turns yet
          </div>
        )}
      </div>

      {/* Memory summary */}
      {(memorySummary || loading) && (
        <div className="memory-box">
          <div style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--text-muted)', marginBottom: 6 }}>
            📝 Memory Summary
          </div>
          {loading && !memorySummary ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '4px 0' }}>
              <span style={{
                width: 14, height: 14,
                border: '1.5px solid rgba(139,92,246,0.2)',
                borderTopColor: 'var(--purple)',
                borderRadius: '50%',
                animation: 'spin 0.7s linear infinite',
                display: 'inline-block',
              }} />
            </div>
          ) : (
            <p style={{ fontSize: 11.5, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              {memorySummary}
            </p>
          )}
        </div>
      )}
    </div>
  );
};

SessionContext.propTypes = {
  autoRefresh: PropTypes.bool,
};

export default SessionContext;
