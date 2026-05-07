# React Hooks

This directory contains custom React hooks for the FinDoc Intelligence frontend.

## useQuery

A custom hook for managing query submission and results in the application.

### Features

- **Query Submission**: Submit queries to the backend with multi-model support
- **Loading State**: Track loading state during query execution
- **Error Handling**: Handle and expose API errors gracefully
- **Results Management**: Store and expose query results from multiple models
- **Query History**: Maintain a history of all queries submitted in the current session
- **Input Validation**: Validate required fields before submission

### Usage

```javascript
import useQuery from './hooks/useQuery';
import useSession from './hooks/useSession';

function MyComponent() {
  const { sessionId } = useSession();
  const { 
    submit,    // Function to submit a query
    loading,   // Loading state during query execution
    error,     // Error object if submission fails
    results,   // Array of model-specific response objects
    history    // Array of all queries submitted in this session
  } = useQuery();

  const handleSubmit = async () => {
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
      <button onClick={handleSubmit} disabled={loading}>
        {loading ? 'Submitting...' : 'Submit Query'}
      </button>
      {error && <p>Error: {error.message}</p>}
      {results.map((result, i) => (
        <div key={i}>
          <h3>{result.model}</h3>
          <p>{result.response_text}</p>
        </div>
      ))}
    </div>
  );
}
```

### Return Values

| Property | Type | Description |
|----------|------|-------------|
| `submit` | `Function` | Async function to submit a query payload |
| `loading` | `boolean` | True while query is being processed |
| `error` | `Error \| null` | Error object if submission fails |
| `results` | `Array` | Array of model-specific response objects |
| `history` | `Array` | Array of all queries submitted in this session |

### Query Payload Structure

The `submit()` function expects a payload with the following structure:

```javascript
{
  session_id: string,      // Required: Session UUID
  query_text: string,      // Required: User's question (non-empty)
  models: string[],        // Required: Array of model names (at least one)
  company: string          // Optional: Company name for context
}
```

### Result Structure

Each item in the `results` array has the following structure:

```javascript
{
  model: string,                    // Model name (e.g., "llama", "gemini")
  response_text: string,            // Generated response text
  confidence_score: number,         // Confidence score (0-1)
  refusal_flag: boolean,            // Whether the query was refused
  refusal_reason: string | null,    // Reason for refusal (if applicable)
  repair_count: number,             // Number of repair iterations
  citations: [                      // Array of source citations
    {
      chunk_id: number,             // Chunk identifier
      chunk_text: string,           // Source text
      relevance_score: number       // Relevance score (0-1)
    }
  ],
  agent_trace: {                    // Agent execution trace
    plan: Array,                    // Planner's tool call plan
    tool_results: Array,            // Tool execution results
    critic_verdict: string          // Critic's verdict
  },
  latency_ms: number                // Query latency in milliseconds
}
```

### History Entry Structure

Each item in the `history` array has the following structure:

```javascript
{
  query_text: string,      // User's question
  models: string[],        // Models used for this query
  company: string,         // Company context
  timestamp: string,       // ISO 8601 timestamp
  results: Array           // Full results array from the response
}
```

### Input Validation

The hook validates the following before submitting:

1. **session_id**: Must be present
2. **query_text**: Must be non-empty (after trimming whitespace)
3. **models**: Must contain at least one model

If validation fails, the hook sets an error and does not call the API.

### Backend API Integration

The hook uses the `submitQuery()` function from `services/api.js` to submit queries:

- **Endpoint**: `POST /query`
- **Request Body**:
  ```json
  {
    "session_id": "uuid",
    "query_text": "What was Apple's net income in FY2023?",
    "models": ["llama", "gemini"],
    "company": "Apple"
  }
  ```
- **Expected Response**:
  ```json
  {
    "results": [
      {
        "model": "llama",
        "response_text": "Apple's net income in FY2023 was $96.995 billion.",
        "confidence_score": 0.92,
        "refusal_flag": false,
        "refusal_reason": null,
        "repair_count": 0,
        "citations": [...],
        "agent_trace": {...},
        "latency_ms": 2341
      }
    ]
  }
  ```

### Behavior

1. **On Submit**: Validates payload, clears previous results, sets loading state
2. **On Success**: Updates results, adds entry to history, clears error
3. **On Error**: Sets error, clears results, maintains loading state
4. **Result Clearing**: Previous results are cleared when a new query is submitted
5. **History Accumulation**: All successful queries are added to the history array

### Example Component

See `useQuery.example.jsx` for a complete example of how to use this hook in a component with:
- Form handling for query input
- Model selection with checkboxes
- Company dropdown
- Results display with citations
- Agent trace visualization
- Query history display

### Testing

The hook includes comprehensive unit tests in `useQuery.test.js`:

- Initialization with empty state
- Successful query submission
- Multi-model query handling
- Loading state management
- API error handling
- Input validation (session_id, query_text, models)
- Result clearing on new submission
- Query history accumulation
- Refusal response handling
- Invalid response format handling
- Error state clearing on success

Run tests with:
```bash
npm test -- useQuery.test.js
```

## useSession

A custom hook for managing session state in the application.

### Features

- **Automatic Session ID Generation**: Generates a UUID on first load and persists it to localStorage
- **Session Persistence**: Retrieves existing session_id from localStorage on subsequent loads
- **History Fetching**: Automatically fetches session history from the backend API
- **Memory Summary**: Exposes the most recent LLM-compressed memory summary
- **Recent Turns**: Provides the last 2-5 query-response pairs
- **Manual Refresh**: Allows manual reloading of session data

### Usage

```javascript
import useSession from './hooks/useSession';

function MyComponent() {
  const { 
    sessionId,        // Current session UUID
    memorySummary,    // Compressed LLM summary of prior turns
    recentTurns,      // Array of last 2-5 query-response pairs
    refresh,          // Function to reload session data
    loading,          // Loading state for history fetch
    error             // Error object if fetch fails
  } = useSession();

  // Use the session data in your component
  return (
    <div>
      <p>Session ID: {sessionId}</p>
      {memorySummary && <p>Summary: {memorySummary}</p>}
      <button onClick={refresh}>Refresh</button>
    </div>
  );
}
```

### Return Values

| Property | Type | Description |
|----------|------|-------------|
| `sessionId` | `string \| null` | Current session UUID (null until initialized) |
| `memorySummary` | `string \| null` | Compressed LLM summary of prior turns |
| `recentTurns` | `Array` | Last 2-5 query-response pairs |
| `refresh` | `Function` | Async function to reload session data from backend |
| `loading` | `boolean` | True while fetching history data |
| `error` | `Error \| null` | Error object if history fetch fails |

### Recent Turn Structure

Each item in the `recentTurns` array has the following structure:

```javascript
{
  query_id: number,           // Unique query ID
  query_text: string,         // User's question
  timestamp: string,          // ISO 8601 timestamp
  response_text: string,      // System's response
  confidence_score: number,   // Confidence score (0-1)
  refusal_flag: boolean       // Whether the query was refused
}
```

### Backend API Integration

The hook uses the `getHistory()` function from `services/api.js` to fetch session data from the backend:

- **Endpoint**: `GET /history?session_id={sessionId}`
- **Expected Response**:
  ```json
  {
    "memory_summaries": [
      {
        "id": 1,
        "session_id": "uuid",
        "turn_range_start": 1,
        "turn_range_end": 5,
        "summary_text": "Compressed summary..."
      }
    ],
    "queries": [
      {
        "id": 1,
        "query_text": "What was Apple's revenue?",
        "timestamp": "2024-01-01T10:00:00Z",
        "response": {
          "response_text": "Apple's revenue was...",
          "confidence_score": 0.95,
          "refusal_flag": false
        }
      }
    ]
  }
  ```

### Automatic Behavior

1. **On Mount**: The hook automatically generates or retrieves a session_id
2. **On Session ID Change**: Automatically fetches session history
3. **Error Handling**: Logs errors to console and exposes them via the `error` property

### Example Component

See `useSession.example.jsx` for a complete example of how to use this hook in a component.

### Testing

The hook includes comprehensive unit tests in `useSession.test.js`:

- Session ID generation and persistence
- Retrieving existing session IDs
- Fetching and parsing session history
- Handling empty history
- Limiting recent turns to 5
- Error handling
- Manual refresh functionality

Run tests with:
```bash
npm test -- useSession.test.js
```
