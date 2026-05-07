import React, { useState } from 'react';
import useQuery from './useQuery';
import useSession from './useSession';

/**
 * Example component demonstrating useQuery hook usage
 * 
 * This example shows:
 * - How to submit queries with the useQuery hook
 * - How to handle loading and error states
 * - How to display multi-model results
 * - How to integrate with useSession for session management
 */
const QueryExample = () => {
  const { sessionId } = useSession();
  const { submit, loading, error, results, history } = useQuery();
  
  const [queryText, setQueryText] = useState('');
  const [selectedModels, setSelectedModels] = useState(['llama']);
  const [company, setCompany] = useState('Apple');

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!sessionId) {
      console.error('Session ID not initialized');
      return;
    }

    const payload = {
      session_id: sessionId,
      query_text: queryText,
      models: selectedModels,
      company: company,
    };

    await submit(payload);
  };

  const handleModelToggle = (model) => {
    setSelectedModels((prev) => {
      if (prev.includes(model)) {
        return prev.filter((m) => m !== model);
      } else {
        return [...prev, model];
      }
    });
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Query Example</h1>

      {/* Query Form */}
      <form onSubmit={handleSubmit} className="mb-8 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">
            Company
          </label>
          <select
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            className="w-full px-3 py-2 border rounded-md"
          >
            <option value="Apple">Apple</option>
            <option value="Microsoft">Microsoft</option>
            <option value="Google">Google</option>
            <option value="Amazon">Amazon</option>
            <option value="Tesla">Tesla</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">
            Question
          </label>
          <textarea
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
            placeholder="What was Apple's net income in FY2023?"
            className="w-full px-3 py-2 border rounded-md"
            rows={3}
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">
            Models
          </label>
          <div className="flex gap-4">
            {['llama', 'gemma', 'gemini'].map((model) => (
              <label key={model} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={selectedModels.includes(model)}
                  onChange={() => handleModelToggle(model)}
                />
                <span className="capitalize">{model}</span>
              </label>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || !queryText.trim() || selectedModels.length === 0}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
        >
          {loading ? 'Submitting...' : 'Submit Query'}
        </button>
      </form>

      {/* Error Display */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
          <p className="text-red-800 font-medium">Error:</p>
          <p className="text-red-600">{error.message}</p>
        </div>
      )}

      {/* Loading Indicator */}
      {loading && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-md">
          <p className="text-blue-800">Processing your query...</p>
        </div>
      )}

      {/* Results Display */}
      {results.length > 0 && (
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-4">Results</h2>
          <div className="space-y-6">
            {results.map((result, index) => (
              <div
                key={index}
                className="p-4 border rounded-md bg-white shadow-sm"
              >
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-medium capitalize">
                    {result.model}
                  </h3>
                  <div className="flex gap-2">
                    <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                      Confidence: {(result.confidence_score * 100).toFixed(0)}%
                    </span>
                    {result.refusal_flag && (
                      <span className="px-2 py-1 text-xs bg-red-100 text-red-800 rounded">
                        Refused: {result.refusal_reason}
                      </span>
                    )}
                    {result.repair_count > 0 && (
                      <span className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded">
                        Repairs: {result.repair_count}
                      </span>
                    )}
                  </div>
                </div>

                <p className="text-gray-700 mb-3">{result.response_text}</p>

                {/* Citations */}
                {result.citations && result.citations.length > 0 && (
                  <div className="mt-3 pt-3 border-t">
                    <p className="text-sm font-medium mb-2">Citations:</p>
                    <div className="space-y-2">
                      {result.citations.map((citation, citIndex) => (
                        <div
                          key={citIndex}
                          className="text-sm p-2 bg-gray-50 rounded"
                        >
                          <p className="text-gray-600 text-xs mb-1">
                            Chunk {citation.chunk_id} (Relevance:{' '}
                            {(citation.relevance_score * 100).toFixed(0)}%)
                          </p>
                          <p className="text-gray-700">{citation.chunk_text}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Agent Trace */}
                {result.agent_trace && (
                  <details className="mt-3 pt-3 border-t">
                    <summary className="text-sm font-medium cursor-pointer">
                      Agent Trace
                    </summary>
                    <div className="mt-2 text-sm">
                      <p className="mb-1">
                        <strong>Critic Verdict:</strong>{' '}
                        {result.agent_trace.critic_verdict}
                      </p>
                      <p className="mb-1">
                        <strong>Latency:</strong> {result.latency_ms}ms
                      </p>
                      {result.agent_trace.plan && (
                        <div className="mt-2">
                          <strong>Plan:</strong>
                          <pre className="mt-1 p-2 bg-gray-50 rounded text-xs overflow-x-auto">
                            {JSON.stringify(result.agent_trace.plan, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  </details>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Query History */}
      {history.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold mb-4">Query History</h2>
          <div className="space-y-2">
            {history.map((entry, index) => (
              <div
                key={index}
                className="p-3 border rounded-md bg-gray-50 text-sm"
              >
                <p className="font-medium">{entry.query_text}</p>
                <p className="text-gray-600 text-xs mt-1">
                  Models: {entry.models.join(', ')} | Company: {entry.company} |{' '}
                  {new Date(entry.timestamp).toLocaleTimeString()}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default QueryExample;
