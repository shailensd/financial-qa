import { useState } from 'react';
import PropTypes from 'prop-types';

function ChevronIcon({ open }) {
  return (
    <svg
      width="12" height="12" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
      className={`chevron${open ? ' open' : ''}`}
    >
      <path d="M6 9l6 6 6-6" />
    </svg>
  );
}

function getVerdictBadge(verdict) {
  switch (verdict) {
    case 'approved':          return 'badge badge-green';
    case 'repair_numerical':  return 'badge badge-yellow';
    case 'repair_citation':   return 'badge badge-orange';
    default:                  return 'badge badge-gray';
  }
}

function formatVerdict(verdict) {
  if (!verdict) return 'Unknown';
  return verdict.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

function getRepairBadge(count) {
  if (count === 0) return 'badge badge-green';
  if (count === 1)  return 'badge badge-yellow';
  return 'badge badge-red';
}

/**
 * AgentTrace
 *
 * Collapsible panel showing:
 * - Planner steps (tool calls)
 * - Tool results
 * - Critic verdict + repair count
 *
 * `inline` prop skips the outer panel wrapper (used inside result cards).
 */
const AgentTrace = ({ agentTrace = null, inline = false }) => {
  const [open, setOpen] = useState(false);

  if (!agentTrace) return null;

  const {
    plan          = [],
    tool_results  = [],
    critic_verdict = 'unknown',
    repair_count   = 0,
  } = agentTrace;

  const header = (
    <button
      className={`agent-trace-header${open ? ' open' : ''}`}
      onClick={() => setOpen(v => !v)}
      aria-expanded={open}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {/* Icon */}
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
          stroke="var(--purple)" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>
          Agent Trace
        </span>
        {/* Summary badges always visible */}
        <span className={getVerdictBadge(critic_verdict)}>
          {formatVerdict(critic_verdict)}
        </span>
        <span className={getRepairBadge(repair_count)}>
          {repair_count} {repair_count === 1 ? 'repair' : 'repairs'}
        </span>
      </div>
      <ChevronIcon open={open} />
    </button>
  );

  const body = open && (
    <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* Plan steps */}
      {plan.length > 0 && (
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--text-muted)', marginBottom: 8 }}>
            Planner · {plan.length} step{plan.length !== 1 ? 's' : ''}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {plan.map((step, i) => (
              <div key={i} className="trace-step">
                <div className="trace-tool-name">{step.tool}</div>
                {step.inputs && Object.keys(step.inputs).length > 0 && (
                  <pre className="trace-pre">{JSON.stringify(step.inputs, null, 2)}</pre>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tool results */}
      {tool_results.length > 0 && (
        <div>
          <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--text-muted)', marginBottom: 8 }}>
            Tool Results · {tool_results.length}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {tool_results.map((r, i) => (
              <div key={i} className="trace-step">
                <div className="trace-tool-name" style={{ color: 'var(--green)' }}>{r.tool}</div>
                {r.output && (
                  <pre className="trace-pre">
                    {typeof r.output === 'string' ? r.output : JSON.stringify(r.output, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Critic row */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <div style={{
          flex: 1, minWidth: 120,
          background: 'rgba(0,0,0,0.15)',
          border: '1px solid var(--border)',
          borderRadius: 8,
          padding: '8px 12px',
        }}>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 5 }}>
            Critic verdict
          </div>
          <span className={getVerdictBadge(critic_verdict)}>
            {formatVerdict(critic_verdict)}
          </span>
        </div>
        <div style={{
          flex: 1, minWidth: 120,
          background: 'rgba(0,0,0,0.15)',
          border: '1px solid var(--border)',
          borderRadius: 8,
          padding: '8px 12px',
        }}>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 5 }}>
            Repair iterations
          </div>
          <span className={getRepairBadge(repair_count)}>
            {repair_count}
          </span>
        </div>
      </div>

    </div>
  );

  if (inline) {
    return (
      <div>
        {header}
        {body}
      </div>
    );
  }

  return (
    <div className="agent-trace-panel">
      {header}
      {body}
    </div>
  );
};

AgentTrace.propTypes = {
  agentTrace: PropTypes.shape({
    plan: PropTypes.arrayOf(PropTypes.shape({
      tool:   PropTypes.string.isRequired,
      inputs: PropTypes.object,
    })),
    tool_results: PropTypes.arrayOf(PropTypes.shape({
      tool:   PropTypes.string.isRequired,
      output: PropTypes.oneOfType([PropTypes.string, PropTypes.object]),
    })),
    critic_verdict: PropTypes.string,
    repair_count:   PropTypes.number,
  }),
  inline: PropTypes.bool,
};

export default AgentTrace;
