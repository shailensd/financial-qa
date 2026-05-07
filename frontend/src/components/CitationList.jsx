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

function StarIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  );
}

function getRelevanceBadge(score) {
  if (score >= 0.8) return 'badge badge-green';
  if (score >= 0.6) return 'badge badge-cyan';
  if (score >= 0.4) return 'badge badge-yellow';
  return 'badge badge-gray';
}

/**
 * CitationList
 *
 * Renders an expandable list of citation cards with chunk text and relevance score.
 * When used `inline` (inside a result card), it renders without the outer panel wrapper.
 */
const CitationList = ({ citations = [], inline = false }) => {
  const [expanded, setExpanded] = useState(new Set());

  const toggle = (id) => {
    setExpanded(prev => {
      const s = new Set(prev);
      s.has(id) ? s.delete(id) : s.add(id);
      return s;
    });
  };

  const expandAll  = () => setExpanded(new Set(citations.map(c => c.chunk_id)));
  const collapseAll = () => setExpanded(new Set());
  const allOpen    = expanded.size === citations.length && citations.length > 0;

  if (!citations || citations.length === 0) return null;

  const inner = (
    <>
      {/* Header */}
      <div className="citation-panel-header">
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          Source Citations
          <span className="badge badge-blue">{citations.length}</span>
        </span>
        <button
          onClick={allOpen ? collapseAll : expandAll}
          className="expand-btn"
          style={{ fontSize: 11 }}
        >
          {allOpen ? 'Collapse all' : 'Expand all'}
        </button>
      </div>

      {/* Citation list */}
      <div>
        {citations.map((citation, index) => {
          const isOpen = expanded.has(citation.chunk_id);
          return (
            <div key={citation.chunk_id} className="citation-item">
              <button
                className="citation-toggle"
                onClick={() => toggle(citation.chunk_id)}
                aria-expanded={isOpen}
              >
                <span className="citation-num">{index + 1}</span>
                <div className="citation-meta">
                  <div className="citation-id">chunk #{citation.chunk_id}</div>
                </div>
                <span className={getRelevanceBadge(citation.relevance_score)} style={{ marginLeft: 'auto', marginRight: 6 }}>
                  <StarIcon />
                  {(citation.relevance_score * 100).toFixed(0)}%
                </span>
                <ChevronIcon open={isOpen} />
              </button>

              {isOpen && (
                <div className="citation-body">
                  {citation.chunk_text}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </>
  );

  if (inline) {
    return <div>{inner}</div>;
  }

  return (
    <div className="citation-panel">
      {inner}
    </div>
  );
};

CitationList.propTypes = {
  citations: PropTypes.arrayOf(
    PropTypes.shape({
      chunk_id:        PropTypes.number.isRequired,
      chunk_text:      PropTypes.string.isRequired,
      relevance_score: PropTypes.number.isRequired,
    })
  ),
  inline: PropTypes.bool,
};

export default CitationList;
