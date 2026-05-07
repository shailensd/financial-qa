import React from 'react';
import useSession from './useSession';

/**
 * Example component demonstrating useSession hook usage
 * 
 * This component shows how to:
 * - Access the current session ID
 * - Display memory summary
 * - Show recent conversation turns
 * - Manually refresh session data
 */
const SessionExample = () => {
  const { 
    sessionId, 
    memorySummary, 
    recentTurns, 
    refresh, 
    loading, 
    error 
  } = useSession();

  if (loading) {
    return <div>Loading session data...</div>;
  }

  if (error) {
    return (
      <div className="text-red-600">
        Error loading session: {error.message}
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {/* Session ID Display */}
      <div className="bg-gray-100 p-3 rounded">
        <h3 className="font-semibold text-sm text-gray-600">Session ID</h3>
        <p className="text-xs font-mono">{sessionId}</p>
      </div>

      {/* Memory Summary */}
      {memorySummary && (
        <div className="bg-blue-50 p-3 rounded">
          <h3 className="font-semibold text-sm text-blue-800">Memory Summary</h3>
          <p className="text-sm text-gray-700 mt-1">{memorySummary}</p>
        </div>
      )}

      {/* Recent Turns */}
      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <h3 className="font-semibold text-sm text-gray-800">
            Recent Turns ({recentTurns.length})
          </h3>
          <button
            onClick={refresh}
            className="text-xs bg-blue-500 text-white px-3 py-1 rounded hover:bg-blue-600"
          >
            Refresh
          </button>
        </div>

        {recentTurns.length === 0 ? (
          <p className="text-sm text-gray-500 italic">No conversation history yet</p>
        ) : (
          <div className="space-y-3">
            {recentTurns.map((turn, index) => (
              <div key={turn.query_id} className="border-l-4 border-gray-300 pl-3">
                <div className="text-xs text-gray-500">
                  Turn {index + 1} • {new Date(turn.timestamp).toLocaleString()}
                </div>
                <div className="mt-1">
                  <p className="text-sm font-medium text-gray-800">
                    Q: {turn.query_text}
                  </p>
                  <p className="text-sm text-gray-600 mt-1">
                    A: {turn.response_text}
                  </p>
                  <div className="flex gap-2 mt-1">
                    <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">
                      Confidence: {(turn.confidence_score * 100).toFixed(0)}%
                    </span>
                    {turn.refusal_flag && (
                      <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">
                        Refused
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SessionExample;
