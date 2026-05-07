# Task 16.4 Implementation Summary

## Overview
Successfully implemented the `useQuery.js` custom React hook for managing query submission and results in the FinDoc Intelligence frontend application.

## Files Created

### 1. `/frontend/src/hooks/useQuery.js`
The main hook implementation with the following features:
- **Query Submission**: Submit queries to backend via `submitQuery()` API function
- **Loading State**: Track loading state during query execution
- **Error Handling**: Handle and expose API errors gracefully
- **Results Management**: Store and expose query results from multiple models
- **Query History**: Maintain history of all queries submitted in current session
- **Input Validation**: Validate required fields (session_id, query_text, models) before submission

### 2. `/frontend/src/hooks/useQuery.test.js`
Comprehensive test suite with 13 test cases covering:
- Initialization with empty state
- Successful query submission and result updates
- Multi-model query handling
- Loading state management during submission
- API error handling
- Input validation (session_id, query_text, models)
- Result clearing on new submission
- Query history accumulation
- Refusal response handling
- Invalid response format handling
- Error state clearing on successful submission

**Test Results**: ✅ All 13 tests passing

### 3. `/frontend/src/hooks/useQuery.example.jsx`
Example component demonstrating hook usage with:
- Query form with company selector, question textarea, and model checkboxes
- Submit button with loading state
- Error display
- Results display with confidence scores, refusal badges, repair counts
- Citations display with expandable chunks
- Agent trace visualization (collapsible)
- Query history display
- Tailwind CSS styling

### 4. `/frontend/src/hooks/README.md` (Updated)
Added complete documentation for useQuery including:
- Feature overview
- Usage examples
- API reference
- Payload structure
- Result structure
- History entry structure
- Input validation rules
- Backend integration details
- Testing instructions

## Implementation Details

### Query Payload Structure
```javascript
const payload = {
  session_id: "uuid",                    // Required
  query_text: "What was Apple's revenue?", // Required (non-empty)
  models: ["llama", "gemini"],           // Required (at least one)
  company: "Apple"                       // Optional
};
```

### Result Structure
```javascript
{
  model: "llama",
  response_text: "Apple's net income in FY2023 was $96.995 billion.",
  confidence_score: 0.92,
  refusal_flag: false,
  refusal_reason: null,
  repair_count: 0,
  citations: [
    {
      chunk_id: 42,
      chunk_text: "Net income: $96,995 million",
      relevance_score: 0.94
    }
  ],
  agent_trace: {
    plan: [...],
    tool_results: [...],
    critic_verdict: "approved"
  },
  latency_ms: 2341
}
```

### Hook Return Values
```javascript
const {
  submit,    // (payload) => Promise<void>
  loading,   // boolean
  error,     // Error | null
  results,   // Array of result objects
  history    // Array of history entries
} = useQuery();
```

## Input Validation

The hook validates the following before submitting:

1. **session_id**: Must be present
   - Error: "session_id is required"
   
2. **query_text**: Must be non-empty after trimming whitespace
   - Error: "query_text cannot be empty"
   
3. **models**: Must contain at least one model
   - Error: "At least one model must be selected"

If validation fails, the hook sets an error and does not call the API.

## Integration with Existing Code

### API Service Integration
The hook uses the existing `submitQuery()` function from `/frontend/src/services/api.js`:
- Endpoint: `POST /query`
- Request body: Query payload with session_id, query_text, models, company
- Response: Object with results array containing model-specific responses
- Error normalization handled by response interceptor

### Design Compliance
Implements all requirements from `design.md`:
- ✅ Submit queries with multi-model support
- ✅ Track loading state during execution
- ✅ Handle and expose errors
- ✅ Store and expose query results
- ✅ Maintain query history for current session
- ✅ Validate input before submission

### Requirements Compliance
Satisfies **Requirement 16: React Frontend Application**:
- ✅ Provide query submission functionality
- ✅ Support multi-model queries
- ✅ Display confidence scores, refusal flags, repair counts
- ✅ Expose citations and agent trace
- ✅ Handle loading and error states

## Behavior

### On Submit
1. Validates payload (session_id, query_text, models)
2. Clears previous results
3. Sets loading state to true
4. Clears any previous errors
5. Calls submitQuery() API function

### On Success
1. Updates results with response data
2. Adds entry to history array
3. Clears error state
4. Sets loading state to false

### On Error
1. Sets error state with error object
2. Clears results array
3. Logs error to console
4. Sets loading state to false

### Result Clearing
- Previous results are cleared when a new query is submitted
- This ensures the UI always shows results for the most recent query

### History Accumulation
- All successful queries are added to the history array
- History persists for the lifetime of the component
- Each entry includes query_text, models, company, timestamp, and results

## Testing Strategy

### Unit Tests
- **Isolation**: All API calls mocked using vitest
- **Coverage**: 13 test cases covering all functionality
- **Edge Cases**: Empty inputs, invalid payloads, API errors, invalid responses
- **Async Handling**: Proper use of waitFor() and act()
- **State Management**: Verify loading, error, results, and history states

### Test Execution
```bash
npm test -- useQuery.test.js
```

## Usage Example

```javascript
import useQuery from './hooks/useQuery';
import useSession from './hooks/useSession';

function QueryForm() {
  const { sessionId } = useSession();
  const { submit, loading, error, results, history } = useQuery();

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const payload = {
      session_id: sessionId,
      query_text: "What was Apple's net income in FY2023?",
      models: ['llama', 'gemini'],
      company: 'Apple'
    };
    
    await submit(payload);
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <button type="submit" disabled={loading}>
          {loading ? 'Submitting...' : 'Submit Query'}
        </button>
      </form>
      
      {error && <div>Error: {error.message}</div>}
      
      {results.map((result, i) => (
        <div key={i}>
          <h3>{result.model}</h3>
          <p>{result.response_text}</p>
          <span>Confidence: {result.confidence_score}</span>
        </div>
      ))}
      
      <h4>History ({history.length} queries)</h4>
      {history.map((entry, i) => (
        <div key={i}>{entry.query_text}</div>
      ))}
    </div>
  );
}
```

## Next Steps

The hook is ready for integration into the main application:

1. **Import in QueryInput component** (Task 16.1)
2. **Integrate with AnswerDisplay component** (Task 16.2)
3. **Connect with SessionContext for auto-refresh** (Task 16.5)
4. **Display agent trace in AgentTrace component** (Task 16.6)

## Notes

- The hook validates all required fields before making API calls
- Previous results are cleared when a new query is submitted
- All errors are logged to console and exposed via the error property
- The history array accumulates all queries for the current session
- Multi-model queries return results for all selected models
- Refusal responses are handled gracefully with refusal_flag and refusal_reason
- The hook is fully tested and production-ready

## Dependencies

No new dependencies required. The hook uses:
- React hooks (useState, useCallback)
- Existing API service (submitQuery from services/api.js)

## Performance Considerations

- Results are cleared before each new submission to prevent memory leaks
- History array grows with each query (consider implementing a max limit if needed)
- Loading state prevents duplicate submissions
- Validation happens synchronously before API call

## Error Handling

The hook handles the following error scenarios:
1. **Validation Errors**: Set error state without calling API
2. **Network Errors**: Caught and exposed via error state
3. **API Errors**: Normalized by axios interceptor and exposed
4. **Invalid Response Format**: Detected and error set
5. **Timeout Errors**: Handled by axios timeout configuration (30s)

All errors are logged to console for debugging purposes.
