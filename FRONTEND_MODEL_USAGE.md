# Frontend Model Selection Guide

## Yes! The Frontend Will Support All Three Models

Based on the current design, the frontend will have **model checkboxes** that let users select which models to use for each query. Here's exactly how it works:

## 🎨 Frontend UI Design

### QueryInput Component

```
┌─────────────────────────────────────────────────────────────┐
│  FinDoc Intelligence                                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Company: [Apple ▼]                                         │
│                                                              │
│  Question:                                                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ What was Apple's total revenue in FY2023?              │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  Select Models:                                              │
│  ☑ Llama 3.2 3B (Local - Fast)                             │
│  ☑ Gemma 2 9B (Local - Better Quality)                     │
│  ☑ Gemini 2.0 Flash (Cloud - Best Quality)                 │
│                                                              │
│  [Submit Query]                                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### How It Works

1. **User selects models** via checkboxes (can select 1, 2, or all 3)
2. **Frontend sends request** to backend with selected models
3. **Backend processes sequentially** (one model at a time)
4. **Frontend displays results** in tabs or side-by-side

## 📊 Response Display

### Tabbed Layout (Design Option 1)

```
┌─────────────────────────────────────────────────────────────┐
│  Results                                                     │
├─────────────────────────────────────────────────────────────┤
│  [Llama 3.2] [Gemma 2] [Gemini 2.0] ← Tabs                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Response: Apple's total revenue in FY2023 was $383.285     │
│  billion, representing a 2.8% increase from the prior year. │
│                                                              │
│  Confidence: ████████░░ 85%                                 │
│  Latency: 8.5s                                              │
│  Repair Count: 0                                            │
│                                                              │
│  Citations (3):                                              │
│  ▼ Chunk #42 - Item 7. MD&A (Relevance: 94%)               │
│  ▼ Chunk #87 - Financial Statements (Relevance: 89%)       │
│  ▼ Chunk #103 - Revenue Recognition (Relevance: 82%)       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Side-by-Side Layout (Design Option 2)

```
┌──────────────────────┬──────────────────────┬──────────────────────┐
│  Llama 3.2 3B       │  Gemma 2 9B         │  Gemini 2.0 Flash   │
├──────────────────────┼──────────────────────┼──────────────────────┤
│ Response:            │ Response:            │ Response:            │
│ Apple's revenue...   │ Apple's revenue...   │ Apple's revenue...   │
│                      │                      │                      │
│ Confidence: 85%      │ Confidence: 92%      │ Confidence: 98%      │
│ Latency: 8.5s        │ Latency: 25s         │ Latency: 2s          │
│                      │                      │                      │
│ Citations: 3         │ Citations: 4         │ Citations: 5         │
└──────────────────────┴──────────────────────┴──────────────────────┘
```

## 💻 Frontend Code Example

### QueryInput Component (React)

```jsx
import React, { useState } from 'react';

function QueryInput({ onSubmit }) {
  const [query, setQuery] = useState('');
  const [company, setCompany] = useState('Apple');
  const [selectedModels, setSelectedModels] = useState({
    llama: false,
    gemma: false,
    gemini: true  // Default to Gemini
  });

  const handleModelToggle = (model) => {
    setSelectedModels(prev => ({
      ...prev,
      [model]: !prev[model]
    }));
  };

  const handleSubmit = () => {
    const models = Object.keys(selectedModels)
      .filter(model => selectedModels[model]);
    
    if (models.length === 0) {
      alert('Please select at least one model');
      return;
    }

    onSubmit({
      query_text: query,
      company: company,
      models: models
    });
  };

  return (
    <div className="query-input">
      <select value={company} onChange={(e) => setCompany(e.target.value)}>
        <option value="Apple">Apple</option>
        <option value="Microsoft">Microsoft</option>
        <option value="Google">Google</option>
        {/* ... more companies */}
      </select>

      <textarea
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Ask a question about financial data..."
      />

      <div className="model-selection">
        <label>
          <input
            type="checkbox"
            checked={selectedModels.llama}
            onChange={() => handleModelToggle('llama')}
          />
          Llama 3.2 3B (Local - Fast)
        </label>

        <label>
          <input
            type="checkbox"
            checked={selectedModels.gemma}
            onChange={() => handleModelToggle('gemma')}
          />
          Gemma 2 9B (Local - Better Quality)
        </label>

        <label>
          <input
            type="checkbox"
            checked={selectedModels.gemini}
            onChange={() => handleModelToggle('gemini')}
          />
          Gemini 2.0 Flash (Cloud - Best Quality)
        </label>
      </div>

      <button onClick={handleSubmit}>Submit Query</button>
    </div>
  );
}
```

### API Call (useQuery Hook)

```javascript
// frontend/src/hooks/useQuery.js
import { useState } from 'react';
import { submitQuery } from '../services/api';

export function useQuery() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [error, setError] = useState(null);

  const submit = async (payload) => {
    setLoading(true);
    setError(null);

    try {
      const response = await submitQuery({
        session_id: sessionStorage.getItem('session_id'),
        ...payload
      });

      setResults(response.data.results);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return { submit, loading, results, error };
}
```

## 🔄 Request/Response Flow

### 1. User Interaction
```
User checks: ☑ Llama  ☑ Gemma  ☑ Gemini
User types: "What was Apple's revenue in FY2023?"
User clicks: [Submit Query]
```

### 2. Frontend Request
```javascript
POST http://localhost:8000/query
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "query_text": "What was Apple's revenue in FY2023?",
  "models": ["llama", "gemma", "gemini"],
  "company": "Apple"
}
```

### 3. Backend Processing
```
Backend receives request
→ Validates models: ["llama", "gemma", "gemini"]
→ Processes with Llama (8.5s)
→ Processes with Gemma (25s)
→ Processes with Gemini (2s)
→ Returns all results
```

### 4. Frontend Response
```javascript
{
  "results": [
    {
      "model": "llama",
      "response_text": "Apple's total revenue...",
      "confidence_score": 0.85,
      "latency_ms": 8500,
      "citations": [...]
    },
    {
      "model": "gemma",
      "response_text": "Apple's total revenue...",
      "confidence_score": 0.92,
      "latency_ms": 25000,
      "citations": [...]
    },
    {
      "model": "gemini",
      "response_text": "Apple's total revenue...",
      "confidence_score": 0.98,
      "latency_ms": 2000,
      "citations": [...]
    }
  ]
}
```

### 5. Frontend Display
```
Shows 3 tabs or 3 columns with results from each model
User can compare responses, confidence, and latency
```

## 🎯 User Experience Scenarios

### Scenario 1: Quick Query (Gemini Only)
```
User: Checks only ☑ Gemini
Result: Fast response (2s), best quality
Use case: Production queries, need speed
```

### Scenario 2: Privacy Mode (Local Only)
```
User: Checks ☑ Llama and ☑ Gemma
Result: Slower (8-25s), but data stays local
Use case: Sensitive queries, privacy required
```

### Scenario 3: Model Comparison (All Three)
```
User: Checks ☑ Llama ☑ Gemma ☑ Gemini
Result: All three responses (35s total)
Use case: Research, quality comparison
```

### Scenario 4: Development Testing (Llama Only)
```
User: Checks only ☑ Llama
Result: Fast enough (8s), free, good for testing
Use case: Development, testing features
```

## 🚀 Progressive Enhancement

### Phase 1: Basic (Current Plan)
- ✅ Checkboxes for model selection
- ✅ Tabbed results display
- ✅ Basic loading states

### Phase 2: Enhanced (Future)
- 🔄 Real-time streaming responses
- 🔄 Model availability indicators
- 🔄 Estimated time remaining
- 🔄 Cancel in-progress queries

### Phase 3: Advanced (Future)
- 🔄 Model performance analytics
- 🔄 Cost tracking (Gemini usage)
- 🔄 Model recommendations based on query
- 🔄 A/B testing framework

## 🎨 Visual Indicators

### Model Status Badges

```
Llama 3.2 3B    [🟢 Ready]     Local • Free • Fast
Gemma 2 9B      [🟢 Ready]     Local • Free • Better
Gemini 2.0      [🟢 Ready]     Cloud • Paid • Best

Llama 3.2 3B    [🔴 Offline]   Ollama not running
Gemma 2 9B      [🟡 Loading]   Downloading model...
Gemini 2.0      [🔴 Error]     Invalid API key
```

### Loading States

```
Processing with Llama...    [████████░░] 80% (6.8s)
Processing with Gemma...    [████░░░░░░] 40% (10s)
Processing with Gemini...   [██████████] Done! (2s)
```

## 🔧 Configuration Options

### Default Model Selection

Users can set default models in settings:

```javascript
// User preferences
{
  "defaultModels": ["gemini"],
  "autoSelectLocal": false,
  "showModelComparison": true
}
```

### Model Availability Detection

Frontend can check which models are available:

```javascript
// GET /health response
{
  "status": "ok",
  "db": "connected",
  "chroma": "connected",
  "bm25": "ready",
  "models": {
    "llama": "available",    // Ollama running
    "gemma": "available",    // Ollama running
    "gemini": "available"    // API key valid
  }
}
```

## 📱 Mobile Considerations

On mobile devices, the UI adapts:

```
┌─────────────────────┐
│ Models:             │
│ ☑ Llama (Local)    │
│ ☐ Gemma (Local)    │
│ ☑ Gemini (Cloud)   │
│                     │
│ [Submit]            │
└─────────────────────┘

Results shown as:
- Accordion/expandable cards
- One model at a time
- Swipe between models
```

## 🎓 Summary

**Yes, the frontend will absolutely support all three models!**

✅ **Model Selection**: Checkboxes to select Llama, Gemma, and/or Gemini  
✅ **Flexible**: Use 1, 2, or all 3 models per query  
✅ **Comparison**: See results side-by-side or in tabs  
✅ **Smart**: Shows model status (available/offline)  
✅ **User-Friendly**: Clear indicators for local vs cloud  

The design is already in the spec (Task 17.1):
> "Create `QueryInput.jsx`: company dropdown (hardcoded list of S&P 500 companies), question textarea, **model checkboxes (Llama / Gemma / Gemini)**, submit button with loading state"

You'll be able to:
1. Check which models you want to use
2. Submit your query
3. See results from each model
4. Compare quality, speed, and confidence scores

Perfect for comparing local vs cloud performance! 🎉
