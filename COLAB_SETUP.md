# Google Colab GPU Setup for FinDoc Intelligence

This guide shows you how to run Ollama with GPU acceleration on Google Colab and connect it to your local backend.

## Benefits

- ✅ **10-20x faster** than local CPU (Llama: 2-3 sec vs 33 sec, Gemma: 3-5 sec vs 24 min)
- ✅ **Free GPU** with Colab free tier (T4 GPU)
- ✅ **Better GPU** with Colab Pro (A100/V100)
- ✅ **No code changes** needed in your backend
- ✅ **Easy to set up** - just run the notebook

## Step-by-Step Setup

### Step 1: Open Google Colab

1. Go to https://colab.research.google.com/
2. Click **"New Notebook"**
3. Go to **Runtime → Change runtime type**
4. Select **"T4 GPU"** (or A100 if you have Colab Pro)
5. Click **"Save"**

### Step 2: Copy the Notebook Code

Copy and paste the following code into your Colab notebook:

```python
# ============================================================================
# FinDoc Intelligence - Ollama GPU Setup with ngrok
# ============================================================================

# Step 1: Install Ollama
print("📦 Installing Ollama...")
!curl -fsSL https://ollama.com/install.sh | sh

# Step 2: Start Ollama server in background
print("🚀 Starting Ollama server...")
import subprocess
import time

# Start Ollama serve in background
ollama_process = subprocess.Popen(
    ['ollama', 'serve'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Wait for server to start
time.sleep(5)
print("✅ Ollama server started")

# Step 3: Pull models
print("📥 Pulling Llama 3.2:3b model...")
!ollama pull llama3.2:3b

print("📥 Pulling Gemma 2:9b model...")
!ollama pull gemma2:9b

print("✅ Models downloaded")

# Step 4: Test Ollama locally
print("\n🧪 Testing Ollama locally...")
!ollama run llama3.2:3b "Hello, respond with just 'OK'" --verbose=false

# Step 5: Install and configure ngrok
print("\n🌐 Setting up ngrok tunnel...")
!pip install pyngrok -q

from pyngrok import ngrok, conf
import getpass

# Get ngrok auth token
print("\n⚠️  You need an ngrok auth token (free at https://dashboard.ngrok.com/signup)")
print("After signing up, get your token from: https://dashboard.ngrok.com/get-started/your-authtoken")
ngrok_token = getpass.getpass("Enter your ngrok auth token: ")

# Set ngrok auth token
conf.get_default().auth_token = ngrok_token

# Create tunnel to Ollama (port 11434)
public_url = ngrok.connect(11434)
print(f"\n✅ Ollama is now accessible at: {public_url}")

# Step 6: Display connection info
print("\n" + "="*70)
print("🎉 SETUP COMPLETE!")
print("="*70)
print(f"\n📍 Your Ollama URL: {public_url}")
print("\n📝 Next steps:")
print("1. Copy the URL above")
print("2. Update your backend/.env file:")
print(f"   OLLAMA_BASE_URL={public_url}")
print("3. Restart your FastAPI server")
print("4. Test with: curl -X POST http://localhost:8000/query ...")
print("\n⚠️  Keep this Colab notebook running while using the API")
print("="*70)

# Step 7: Keep the notebook alive
print("\n⏳ Keeping connection alive... (Press Ctrl+C to stop)")
try:
    while True:
        time.sleep(60)
        print(".", end="", flush=True)
except KeyboardInterrupt:
    print("\n\n🛑 Stopping Ollama server...")
    ollama_process.terminate()
    ngrok.disconnect(public_url)
    print("✅ Cleanup complete")
```

### Step 3: Run the Notebook

1. Click **"Runtime → Run all"** or press **Ctrl+F9**
2. Wait for Ollama to install (~2 minutes)
3. Wait for models to download (~5 minutes for both models)
4. When prompted, enter your **ngrok auth token**:
   - Sign up at https://dashboard.ngrok.com/signup (free)
   - Get your token from https://dashboard.ngrok.com/get-started/your-authtoken
   - Paste it into the prompt

### Step 4: Update Your Backend

1. Copy the ngrok URL from the Colab output (looks like `https://xxxx-xx-xxx-xxx-xx.ngrok-free.app`)
2. Update your `backend/.env` file:

```bash
# Replace with your ngrok URL from Colab
OLLAMA_BASE_URL=https://xxxx-xx-xxx-xxx-xx.ngrok-free.app
```

3. Restart your FastAPI server:

```bash
# Stop the current server (Ctrl+C in the terminal where it's running)
# Then restart it:
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 5: Test It!

Run a query to see the GPU speedup:

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-gpu",
    "query_text": "What was Apple revenue in FY2023?",
    "models": ["llama"],
    "company": "Apple"
  }'
```

**Expected results:**
- **Llama**: ~2-3 seconds (vs 33 seconds on CPU) 🚀
- **Gemma**: ~3-5 seconds (vs 24 minutes on CPU) 🚀

## Troubleshooting

### Issue: "ngrok auth token required"
**Solution**: Sign up at https://dashboard.ngrok.com/signup and get your free auth token

### Issue: "Connection refused"
**Solution**: Make sure the Colab notebook is still running and the ngrok tunnel is active

### Issue: "Model not found"
**Solution**: Wait for the models to finish downloading in Colab (check the output)

### Issue: "Colab disconnected"
**Solution**: Colab free tier disconnects after ~12 hours of inactivity. Just restart the notebook.

### Issue: "GPU not available"
**Solution**: 
1. Go to Runtime → Change runtime type
2. Select "T4 GPU"
3. Click Save
4. Re-run the notebook

## Performance Comparison

| Model | CPU (Local) | GPU (Colab Free - T4) | GPU (Colab Pro - A100) |
|-------|-------------|----------------------|------------------------|
| Llama 3.2:3b | 33 sec | ~2-3 sec ⚡ | ~1-2 sec ⚡⚡ |
| Gemma 2:9b | 24 min | ~3-5 sec ⚡ | ~2-3 sec ⚡⚡ |

## Tips

1. **Keep Colab running**: The notebook must stay open and running for the tunnel to work
2. **Free tier limits**: Colab free disconnects after ~12 hours or 90 minutes of inactivity
3. **Colab Pro**: Get faster GPUs (A100) and longer sessions with Colab Pro ($10/month)
4. **Multiple models**: You can pull more models in Colab (just add `!ollama pull model-name`)
5. **Monitor usage**: Check GPU usage in Colab with `!nvidia-smi`

## Alternative: Colab Pro Benefits

If you have Colab Pro ($10/month):
- ✅ **A100 GPU** - 2-3x faster than T4
- ✅ **Longer sessions** - Up to 24 hours
- ✅ **More RAM** - 50GB vs 12GB
- ✅ **Priority access** - No waiting for GPUs

## Next Steps

Once you have GPU acceleration working:
1. Test with different companies (Google, Microsoft, Amazon)
2. Try Gemma model for better quality responses
3. Optimize prompts to reduce token usage
4. Build a frontend for your users

## Need Help?

If you run into issues:
1. Check the Colab output for error messages
2. Verify the ngrok URL is correct in your `.env` file
3. Make sure your FastAPI server restarted after updating `.env`
4. Test the ngrok URL directly: `curl https://your-ngrok-url.ngrok-free.app/api/tags`
