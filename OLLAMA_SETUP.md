# Setting Up Ollama for Local LLM Models

The FinDoc Intelligence system supports 3 LLM models:
- **Gemini 2.0 Flash** - Cloud-based (via Google AI Studio API)
- **Llama 3.2 3B** - Local (via Ollama) ⚡
- **Gemma 2 9B** - Local (via Ollama) ⚡

This guide shows you how to set up Ollama to run Llama and Gemma locally.

## Why Use Local Models?

✅ **Privacy**: Your queries never leave your machine  
✅ **No API costs**: Free to use once downloaded  
✅ **Offline capability**: Works without internet  
✅ **Comparison**: Compare local vs cloud model performance  

⚠️ **Trade-offs**:
- Requires ~6-12 GB disk space
- Slower than Gemini (especially on CPU)
- Requires decent hardware (8GB+ RAM recommended)

## Step 1: Install Ollama

### macOS
```bash
# Download and install from website
open https://ollama.ai/download

# Or use Homebrew
brew install ollama
```

### Linux
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### Windows
Download from: https://ollama.ai/download/windows

### Verify Installation
```bash
ollama --version
# Should show: ollama version 0.x.x
```

## Step 2: Start Ollama Service

Ollama runs as a background service on port 11434.

### macOS/Linux
```bash
# Start Ollama (runs in background)
ollama serve

# Or if installed via Homebrew on macOS
brew services start ollama
```

### Verify Ollama is Running
```bash
curl http://localhost:11434/api/tags
# Should return JSON with available models
```

## Step 3: Download Models

### Download Llama 3.2 3B (~2GB)
```bash
ollama pull llama3.2:3b
```

This will download:
- Model weights: ~2 GB
- Takes 2-10 minutes depending on internet speed

### Download Gemma 2 9B (~5.5GB)
```bash
ollama pull gemma2:9b
```

This will download:
- Model weights: ~5.5 GB
- Takes 5-20 minutes depending on internet speed

### Verify Models are Downloaded
```bash
ollama list
```

Expected output:
```
NAME              ID              SIZE      MODIFIED
llama3.2:3b       a80c4f17acd5    2.0 GB    2 minutes ago
gemma2:9b         ff02c3702f32    5.4 GB    5 minutes ago
```

## Step 4: Test Models

### Test Llama 3.2
```bash
ollama run llama3.2:3b "What is 2+2?"
```

### Test Gemma 2
```bash
ollama run gemma2:9b "What is 2+2?"
```

Both should respond with an answer. Press `Ctrl+D` or type `/bye` to exit.

## Step 5: Configure FinDoc Intelligence

Your `backend/.env` should already have:
```bash
OLLAMA_BASE_URL=http://localhost:11434
```

This tells the backend where to find Ollama.

## Step 6: Use Local Models in Queries

Now you can use all three models in your queries!

### Query with Gemini (Cloud)
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-123",
    "query_text": "What was Apple revenue in FY2023?",
    "models": ["gemini"],
    "company": "Apple"
  }'
```

### Query with Llama (Local)
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-123",
    "query_text": "What was Apple revenue in FY2023?",
    "models": ["llama"],
    "company": "Apple"
  }'
```

### Query with Gemma (Local)
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-123",
    "query_text": "What was Apple revenue in FY2023?",
    "models": ["gemma"],
    "company": "Apple"
  }'
```

### Compare All Three Models
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-123",
    "query_text": "What was Apple revenue in FY2023?",
    "models": ["llama", "gemma", "gemini"],
    "company": "Apple"
  }'
```

This will run the query through all three models sequentially and return results from each!

## Performance Expectations

### Llama 3.2 3B (Smaller, Faster)
- **Size**: 2 GB
- **RAM**: ~4 GB during inference
- **Speed**: 
  - CPU: 5-15 seconds per query
  - GPU: 1-3 seconds per query
- **Quality**: Good for simple queries

### Gemma 2 9B (Larger, Better)
- **Size**: 5.5 GB
- **RAM**: ~10 GB during inference
- **Speed**:
  - CPU: 15-45 seconds per query
  - GPU: 3-8 seconds per query
- **Quality**: Better reasoning, more accurate

### Gemini 2.0 Flash (Cloud, Fastest)
- **Size**: N/A (cloud-based)
- **RAM**: N/A
- **Speed**: 1-3 seconds per query
- **Quality**: Best overall, most reliable

## Troubleshooting

### Issue: "Connection refused" to Ollama

**Check if Ollama is running:**
```bash
curl http://localhost:11434/api/tags
```

**Start Ollama:**
```bash
ollama serve
# Or
brew services start ollama  # macOS with Homebrew
```

### Issue: "Model not found"

**List available models:**
```bash
ollama list
```

**Pull the model:**
```bash
ollama pull llama3.2:3b
ollama pull gemma2:9b
```

### Issue: Ollama uses too much RAM

**Use smaller models:**
```bash
# Use 1B version of Llama instead of 3B
ollama pull llama3.2:1b
```

**Or limit Ollama memory:**
```bash
# Set environment variable before starting Ollama
export OLLAMA_MAX_LOADED_MODELS=1
ollama serve
```

### Issue: Queries are very slow

**Expected on CPU:**
- Llama 3.2 3B: 5-15 seconds
- Gemma 2 9B: 15-45 seconds

**Speed up options:**
1. Use GPU if available (Ollama auto-detects)
2. Use smaller models (llama3.2:1b)
3. Stick with Gemini for production
4. Close other applications to free RAM

### Issue: "Model llama3.2:3b not found" in backend

**Check model name mapping in backend:**

The backend maps friendly names to Ollama model names:
- `"llama"` → `"ollama/llama3.2:3b"`
- `"gemma"` → `"ollama/gemma2:9b"`
- `"gemini"` → `"gemini/gemini-2.0-flash"`

Make sure you pulled the exact model versions:
```bash
ollama pull llama3.2:3b  # Not llama3.2 or llama3.2:latest
ollama pull gemma2:9b    # Not gemma2 or gemma2:latest
```

## Advanced: Using Different Model Versions

### Smaller Models (Faster, Less Accurate)
```bash
ollama pull llama3.2:1b    # 1B parameters, ~700MB
ollama pull gemma2:2b      # 2B parameters, ~1.6GB
```

### Larger Models (Slower, More Accurate)
```bash
ollama pull llama3.1:8b    # 8B parameters, ~4.7GB
ollama pull gemma2:27b     # 27B parameters, ~16GB
```

To use these, you'll need to modify `backend/app/ml/llm_router.py`:
```python
MODELS = {
    "llama": "ollama/llama3.2:1b",  # Change to your preferred version
    "gemma": "ollama/gemma2:2b",    # Change to your preferred version
    "gemini": "gemini/gemini-2.0-flash"
}
```

## Model Comparison Matrix

| Model | Size | RAM | Speed (CPU) | Speed (GPU) | Quality | Cost |
|-------|------|-----|-------------|-------------|---------|------|
| Llama 3.2 1B | 700MB | 2GB | Fast | Very Fast | Basic | Free |
| Llama 3.2 3B | 2GB | 4GB | Medium | Fast | Good | Free |
| Gemma 2 9B | 5.5GB | 10GB | Slow | Medium | Better | Free |
| Gemini 2.0 Flash | N/A | N/A | Fast | Fast | Best | Paid |

## Recommended Setup

### For Development/Testing
- **Use**: Gemini only
- **Why**: Fastest, most reliable, no local setup needed
- **Cost**: ~$0.01 per 100 queries

### For Privacy/Offline Use
- **Use**: Llama 3.2 3B
- **Why**: Good balance of speed and quality
- **Cost**: Free (after download)

### For Best Local Quality
- **Use**: Gemma 2 9B
- **Why**: Better reasoning than Llama
- **Cost**: Free (requires more RAM)

### For Production Comparison
- **Use**: All three models
- **Why**: Compare local vs cloud performance
- **Cost**: Mixed (Gemini paid, others free)

## Cloud Deployment Note

⚠️ **Important**: When deploying to cloud platforms (Railway, Render, etc.), Ollama models won't work because:
- Cloud platforms typically don't have GPUs
- CPU inference is too slow for production
- Models are too large for free tiers

**For cloud deployment, use Gemini only:**
```json
{
  "models": ["gemini"]
}
```

Local models are best for:
- Local development
- Privacy-sensitive use cases
- Offline operation
- Cost optimization (high volume)

## Next Steps

1. ✅ Install Ollama
2. ✅ Download models (llama3.2:3b, gemma2:9b)
3. ✅ Start Ollama service
4. ✅ Test models with `ollama run`
5. ✅ Use in FinDoc Intelligence queries
6. 📊 Compare model performance with `/evaluate` endpoint

## Resources

- **Ollama Website**: https://ollama.ai
- **Ollama GitHub**: https://github.com/ollama/ollama
- **Model Library**: https://ollama.ai/library
- **Llama 3.2 Info**: https://ollama.ai/library/llama3.2
- **Gemma 2 Info**: https://ollama.ai/library/gemma2
