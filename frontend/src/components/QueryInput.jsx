import { useState } from 'react';
import PropTypes from 'prop-types';

const SP500_COMPANIES = [
  { ticker: 'AAPL', name: 'Apple Inc.' },
  { ticker: 'MSFT', name: 'Microsoft Corporation' },
  { ticker: 'GOOGL', name: 'Alphabet Inc. (Google)' },
  { ticker: 'AMZN', name: 'Amazon.com Inc.' },
  { ticker: 'TSLA', name: 'Tesla Inc.' },
  { ticker: 'NVDA', name: 'NVIDIA Corporation' },
  { ticker: 'META', name: 'Meta Platforms Inc.' },
  { ticker: 'BRK.B', name: 'Berkshire Hathaway Inc.' },
  { ticker: 'JPM', name: 'JPMorgan Chase & Co.' },
  { ticker: 'V', name: 'Visa Inc.' },
  { ticker: 'JNJ', name: 'Johnson & Johnson' },
  { ticker: 'WMT', name: 'Walmart Inc.' },
  { ticker: 'PG', name: 'Procter & Gamble Co.' },
  { ticker: 'MA', name: 'Mastercard Inc.' },
  { ticker: 'HD', name: 'The Home Depot Inc.' },
  { ticker: 'DIS', name: 'The Walt Disney Company' },
  { ticker: 'BAC', name: 'Bank of America Corp.' },
  { ticker: 'NFLX', name: 'Netflix Inc.' },
  { ticker: 'ADBE', name: 'Adobe Inc.' },
  { ticker: 'CRM', name: 'Salesforce Inc.' },
];

const AVAILABLE_MODELS = [
  { id: 'llama', label: 'Llama 3.3 70B', icon: '🦙', desc: 'Groq · Cloud' },
  { id: 'gemma', label: 'Llama 4 Scout', icon: '🔭', desc: 'Groq · Cloud' },
  { id: 'gemini', label: 'Gemini 2.5 Flash', icon: '✨', desc: 'Google AI' },
];

function SendIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  );
}

/**
 * QueryInput
 *
 * Provides: company dropdown, model pill toggles, question text input, submit.
 */
const QueryInput = ({ onSubmit, loading = false, sessionId }) => {
  const [company, setCompany] = useState('');
  const [question, setQuestion] = useState('');
  const [selectedModels, setSelectedModels] = useState(['gemini']);
  const [validationMsg, setValidationMsg] = useState('');

  const toggleModel = (id) => {
    setSelectedModels(prev =>
      prev.includes(id) ? prev.filter(m => m !== id) : [...prev, id]
    );
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setValidationMsg('');

    if (!company) return setValidationMsg('Please select a company.');
    if (!question.trim()) return setValidationMsg('Please enter a question.');
    if (!selectedModels.length) return setValidationMsg('Please select at least one model.');

    onSubmit({
      session_id: sessionId,
      query_text: question.trim(),
      models: selectedModels,
      company,
    });
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleSubmit(e);
    }
  };

  return (
    <div className="query-card">
      <form onSubmit={handleSubmit}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

          {/* Row 1: Company + Question */}
          <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: 10 }}>
            {/* Company */}
            <div>
              <label htmlFor="qin-company" className="form-label">Company</label>
              <select
                id="qin-company"
                value={company}
                onChange={e => setCompany(e.target.value)}
                disabled={loading}
                className="form-select"
              >
                <option value="">Select ticker…</option>
                {SP500_COMPANIES.map(c => (
                  <option key={c.ticker} value={c.name}>{c.ticker} — {c.name}</option>
                ))}
              </select>
            </div>

            {/* Question */}
            <div>
              <label htmlFor="qin-question" className="form-label">Question</label>
              <input
                id="qin-question"
                type="text"
                value={question}
                onChange={e => setQuestion(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading}
                placeholder="e.g. What was Apple's total revenue in FY2023?"
                className="form-input"
              />
            </div>
          </div>

          {/* Row 2: Models + Submit */}
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
            {/* Model pills */}
            <div>
              <div className="form-label">Models</div>
              <div style={{ display: 'flex', gap: 6 }}>
                {AVAILABLE_MODELS.map(m => (
                  <label
                    key={m.id}
                    className={`model-pill${selectedModels.includes(m.id) ? ' selected' : ''}`}
                    title={m.desc}
                  >
                    <input
                      type="checkbox"
                      checked={selectedModels.includes(m.id)}
                      onChange={() => toggleModel(m.id)}
                      disabled={loading}
                    />
                    <span>{m.icon}</span>
                    <span>{m.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Submit */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {validationMsg && (
                <span style={{ fontSize: 11.5, color: 'var(--red)' }}>{validationMsg}</span>
              )}
              <button
                type="submit"
                disabled={loading}
                className="submit-btn"
                title="Submit (⌘+Enter)"
              >
                {loading ? (
                  <>
                    <span style={{
                      width: 12, height: 12, border: '2px solid rgba(255,255,255,0.3)',
                      borderTopColor: '#fff', borderRadius: '50%',
                      animation: 'spin 0.6s linear infinite',
                      display: 'inline-block',
                    }} />
                    Running…
                  </>
                ) : (
                  <>
                    <SendIcon />
                    Ask
                  </>
                )}
              </button>
            </div>
          </div>

        </div>
      </form>
    </div>
  );
};

QueryInput.propTypes = {
  onSubmit: PropTypes.func.isRequired,
  loading: PropTypes.bool,
  sessionId: PropTypes.string.isRequired,
};

export default QueryInput;
