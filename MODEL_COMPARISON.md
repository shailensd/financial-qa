# LLM Model Comparison for FinDoc Intelligence

## Overview

FinDoc Intelligence supports three LLM models for query processing. Each has different trade-offs for speed, quality, cost, and deployment.

## Model Comparison

| Feature | Gemini 2.0 Flash ☁️ | Llama 3.2 3B 🏠 | Gemma 2 9B 🏠 |
|---------|-------------------|----------------|--------------|
| **Provider** | Google AI Studio | Meta (via Ollama) | Google (via Ollama) |
| **Location** | Cloud API | Local | Local |
| **Size** | N/A | 2 GB | 5.5 GB |
| **RAM Required** | N/A | ~4 GB | ~10 GB |
| **Setup** | API key only | Ollama + download | Ollama + download |
| **Cost** | ~$0.01/100 queries | Free | Free |
| **Internet Required** | Yes | No | No |
| **Privacy** | Data sent to Google | Fully private | Fully private |

## Performance Comparison

### Speed (Query Latency)

| Model | CPU | GPU | Cloud |
|-------|-----|-----|-------|
| **Gemini 2.0 Flash** | N/A | N/A | 1-3 sec ⚡ |
| **Llama 3.2 3B** | 5-15 sec | 1-3 sec | N/A |
| **Gemma 2 9B** | 15-45 sec | 3-8 sec | N/A |

### Quality (Accuracy & Reasoning)

| Model | Simple Queries | Complex Queries | Numerical Accuracy |
|-------|---------------|-----------------|-------------------|
| **Gemini 2.0 Flash** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐⭐ Excellent |
| **Llama 3.2 3B** | ⭐⭐⭐⭐ Good | ⭐⭐⭐ Fair | ⭐⭐⭐ Fair |
| **Gemma 2 9B** | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐⭐ Good | ⭐⭐⭐⭐ Good |

## Use Case Recommendations

### 🎯 For Production Deployment
**Use: Gemini 2.0 Flash**
- ✅ Fastest response time
- ✅ Best accuracy
- ✅ No local resources needed
- ✅ Scales easily
- ⚠️ Requires API key
- ⚠️ Costs ~$0.01 per 100 queries

### 🔒 For Privacy-Sensitive Use Cases
**Use: Gemma 2 9B**
- ✅ Fully private (data never leaves your machine)
- ✅ Good accuracy
- ✅ Free to use
- ⚠️ Requires 10GB+ RAM
- ⚠️ Slower than cloud

### 💻 For Development/Testing
**Use: Llama 3.2 3B**
- ✅ Fast enough for testing
- ✅ Small download (2GB)
- ✅ Low RAM usage (4GB)
- ✅ Free to use
- ⚠️ Lower accuracy than others

### 📊 For Model Comparison Research
**Use: All Three Models**
- ✅ Compare cloud vs local performance
- ✅ Evaluate cost vs quality trade-offs
- ✅ Test different model sizes
- ⚠️ Requires Ollama setup
- ⚠️ Slower overall (sequential execution)

## Setup Requirements

### Gemini 2.0 Flash
```bash
# 1. Get API key from https://aistudio.google.com/apikey
# 2. Add to backend/.env
GEMINI_API_KEY=your_key_here

# 3. Use in queries
curl -X POST http://localhost:8000/query \
  -d '{"models": ["gemini"], ...}'
```

### Llama 3.2 3B
```bash
# 1. Install Ollama
brew install ollama  # macOS

# 2. Start Ollama
ollama serve

# 3. Download model
ollama pull llama3.2:3b

# 4. Use in queries
curl -X POST http://localhost:8000/query \
  -d '{"models": ["llama"], ...}'
```

### Gemma 2 9B
```bash
# 1. Install Ollama (same as above)
brew install ollama

# 2. Start Ollama
ollama serve

# 3. Download model
ollama pull gemma2:9b

# 4. Use in queries
curl -X POST http://localhost:8000/query \
  -d '{"models": ["gemma"], ...}'
```

## Example Queries

### Single Model Query
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-123",
    "query_text": "What was Apple total revenue in FY2023?",
    "models": ["gemini"],
    "company": "Apple"
  }'
```

### Multi-Model Comparison
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-123",
    "query_text": "What was Apple total revenue in FY2023?",
    "models": ["llama", "gemma", "gemini"],
    "company": "Apple"
  }'
```

Response will include results from all three models:
```json
{
  "results": [
    {
      "model": "llama",
      "response_text": "...",
      "confidence_score": 0.85,
      "latency_ms": 8500
    },
    {
      "model": "gemma",
      "response_text": "...",
      "confidence_score": 0.92,
      "latency_ms": 25000
    },
    {
      "model": "gemini",
      "response_text": "...",
      "confidence_score": 0.98,
      "latency_ms": 2000
    }
  ]
}
```

## Cost Analysis

### Gemini 2.0 Flash Pricing
- **Input**: $0.075 per 1M tokens (~$0.0001 per query)
- **Output**: $0.30 per 1M tokens (~$0.0003 per query)
- **Total**: ~$0.01 per 100 queries
- **Monthly (10K queries)**: ~$1.00

### Local Models (Llama & Gemma)
- **Download**: Free (one-time)
- **Usage**: Free (unlimited)
- **Cost**: Electricity only (~$0.001 per query on CPU)
- **Monthly (10K queries)**: ~$0.00 (effectively free)

### Break-Even Analysis
- **Low volume (<1000 queries/month)**: Use Gemini (convenience)
- **Medium volume (1K-10K queries/month)**: Use Gemini (still cheap)
- **High volume (>10K queries/month)**: Consider local models (cost savings)
- **Privacy required**: Use local models (regardless of volume)

## Cloud Deployment Considerations

### Railway / Render / Heroku
❌ **Local models (Llama/Gemma) NOT recommended**
- No GPU support on free/hobby tiers
- CPU inference too slow for production
- Models too large for container limits

✅ **Gemini recommended**
- Fast response times
- No local resources needed
- Scales automatically

### Self-Hosted (AWS/GCP/Azure)
✅ **Local models viable with GPU instances**
- EC2 g4dn.xlarge: ~$0.50/hour
- Supports both Llama and Gemma
- Good for high-volume use cases

## Hardware Requirements

### Minimum (Gemini Only)
- **CPU**: Any modern processor
- **RAM**: 4 GB
- **Disk**: 1 GB
- **Internet**: Required

### Recommended (Llama 3.2 3B)
- **CPU**: 4+ cores
- **RAM**: 8 GB
- **Disk**: 5 GB
- **Internet**: For download only

### Optimal (All Models)
- **CPU**: 8+ cores or GPU
- **RAM**: 16 GB
- **Disk**: 10 GB
- **GPU**: NVIDIA with 8GB+ VRAM (optional but recommended)
- **Internet**: For Gemini API

## Troubleshooting

### Gemini Issues
- **"Invalid API key"**: Get new key from https://aistudio.google.com/apikey
- **"Rate limit exceeded"**: Wait or upgrade to paid tier
- **"Timeout"**: Check internet connection

### Ollama Issues
- **"Connection refused"**: Start Ollama with `ollama serve`
- **"Model not found"**: Download with `ollama pull llama3.2:3b`
- **"Out of memory"**: Close other apps or use smaller model

### Performance Issues
- **Slow responses**: 
  - Use GPU if available
  - Use smaller models (llama3.2:1b)
  - Stick with Gemini for production
- **High RAM usage**:
  - Limit loaded models: `export OLLAMA_MAX_LOADED_MODELS=1`
  - Use smaller models

## Quick Reference

| Need | Use This | Command |
|------|----------|---------|
| Fastest | Gemini | `{"models": ["gemini"]}` |
| Most Accurate | Gemini | `{"models": ["gemini"]}` |
| Most Private | Gemma 2 9B | `{"models": ["gemma"]}` |
| Cheapest | Llama/Gemma | `{"models": ["llama"]}` |
| Best Balance | Gemini | `{"models": ["gemini"]}` |
| Compare All | All Three | `{"models": ["llama","gemma","gemini"]}` |

## Next Steps

1. **Start with Gemini** - Easiest to set up, best performance
2. **Add Ollama** - For privacy or cost optimization
3. **Compare Models** - Use evaluation endpoint to measure quality
4. **Choose Best Fit** - Based on your requirements

For detailed setup instructions:
- **Gemini**: See `QUICKSTART.md`
- **Ollama**: See `OLLAMA_SETUP.md`
- **Backend**: See `RUNNING_BACKEND.md`
