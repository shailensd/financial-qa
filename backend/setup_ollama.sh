#!/bin/bash

# Ollama Setup Script for FinDoc Intelligence
# This script helps you set up local LLM models (Llama and Gemma)

set -e

echo "🤖 Ollama Setup for FinDoc Intelligence"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Ollama is installed
echo "1. Checking Ollama installation..."
if command -v ollama &> /dev/null; then
    OLLAMA_VERSION=$(ollama --version 2>&1 | head -n1)
    echo -e "${GREEN}✓${NC} Ollama is installed: $OLLAMA_VERSION"
else
    echo -e "${RED}✗${NC} Ollama is not installed"
    echo ""
    echo "Please install Ollama first:"
    echo ""
    echo "  macOS:   brew install ollama"
    echo "           or visit https://ollama.ai/download"
    echo ""
    echo "  Linux:   curl -fsSL https://ollama.ai/install.sh | sh"
    echo ""
    echo "  Windows: https://ollama.ai/download/windows"
    echo ""
    exit 1
fi
echo ""

# Check if Ollama is running
echo "2. Checking Ollama service..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Ollama service is running on port 11434"
else
    echo -e "${YELLOW}⚠${NC} Ollama service is not running"
    echo ""
    echo "Starting Ollama service..."
    
    # Try to start Ollama
    if command -v brew &> /dev/null; then
        # macOS with Homebrew
        brew services start ollama 2>/dev/null || true
        sleep 2
    fi
    
    # Check again
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Ollama service started successfully"
    else
        echo -e "${YELLOW}⚠${NC} Could not start Ollama automatically"
        echo ""
        echo "Please start Ollama manually in another terminal:"
        echo "  ollama serve"
        echo ""
        echo "Then run this script again."
        exit 1
    fi
fi
echo ""

# Check available models
echo "3. Checking installed models..."
INSTALLED_MODELS=$(ollama list 2>/dev/null | tail -n +2 || echo "")

HAS_LLAMA=false
HAS_GEMMA=false

if echo "$INSTALLED_MODELS" | grep -q "llama3.2:3b"; then
    echo -e "${GREEN}✓${NC} Llama 3.2 3B is installed"
    HAS_LLAMA=true
else
    echo -e "${YELLOW}⚠${NC} Llama 3.2 3B is not installed"
fi

if echo "$INSTALLED_MODELS" | grep -q "gemma2:9b"; then
    echo -e "${GREEN}✓${NC} Gemma 2 9B is installed"
    HAS_GEMMA=true
else
    echo -e "${YELLOW}⚠${NC} Gemma 2 9B is not installed"
fi
echo ""

# Offer to download models
if [ "$HAS_LLAMA" = false ] || [ "$HAS_GEMMA" = false ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Would you like to download the missing models?"
    echo ""
    
    if [ "$HAS_LLAMA" = false ]; then
        echo -e "${BLUE}Llama 3.2 3B${NC}"
        echo "  Size: ~2 GB"
        echo "  Speed: Fast (good for development)"
        echo "  Quality: Good"
        echo ""
    fi
    
    if [ "$HAS_GEMMA" = false ]; then
        echo -e "${BLUE}Gemma 2 9B${NC}"
        echo "  Size: ~5.5 GB"
        echo "  Speed: Medium (better quality)"
        echo "  Quality: Better"
        echo ""
    fi
    
    echo "Total download: ~7.5 GB (if downloading both)"
    echo "This will take 5-20 minutes depending on your internet speed."
    echo ""
    
    read -p "Download models? (y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        if [ "$HAS_LLAMA" = false ]; then
            echo "4. Downloading Llama 3.2 3B (~2 GB)..."
            echo "   This may take 2-10 minutes..."
            ollama pull llama3.2:3b
            echo -e "${GREEN}✓${NC} Llama 3.2 3B downloaded successfully"
            echo ""
        fi
        
        if [ "$HAS_GEMMA" = false ]; then
            echo "5. Downloading Gemma 2 9B (~5.5 GB)..."
            echo "   This may take 5-20 minutes..."
            ollama pull gemma2:9b
            echo -e "${GREEN}✓${NC} Gemma 2 9B downloaded successfully"
            echo ""
        fi
    else
        echo ""
        echo "Skipping model download."
        echo "You can download them later with:"
        echo "  ollama pull llama3.2:3b"
        echo "  ollama pull gemma2:9b"
        echo ""
    fi
fi

# Test models
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Testing installed models..."
echo ""

INSTALLED_MODELS=$(ollama list 2>/dev/null | tail -n +2 || echo "")

if echo "$INSTALLED_MODELS" | grep -q "llama3.2:3b"; then
    echo -n "Testing Llama 3.2 3B... "
    LLAMA_TEST=$(echo "What is 2+2? Answer with just the number." | ollama run llama3.2:3b 2>/dev/null | head -n1)
    if [ -n "$LLAMA_TEST" ]; then
        echo -e "${GREEN}✓${NC} Working (response: $LLAMA_TEST)"
    else
        echo -e "${RED}✗${NC} Failed"
    fi
fi

if echo "$INSTALLED_MODELS" | grep -q "gemma2:9b"; then
    echo -n "Testing Gemma 2 9B... "
    GEMMA_TEST=$(echo "What is 2+2? Answer with just the number." | ollama run gemma2:9b 2>/dev/null | head -n1)
    if [ -n "$GEMMA_TEST" ]; then
        echo -e "${GREEN}✓${NC} Working (response: $GEMMA_TEST)"
    else
        echo -e "${RED}✗${NC} Failed"
    fi
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Setup Summary:"
echo ""

ollama list

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✓ Setup complete!${NC}"
echo ""
echo "You can now use local models in your queries:"
echo ""
echo "  # Use Llama"
echo '  curl -X POST http://localhost:8000/query \'
echo '    -H "Content-Type: application/json" \'
echo '    -d '"'"'{"session_id":"test","query_text":"What is Apple revenue?","models":["llama"]}'"'"
echo ""
echo "  # Use Gemma"
echo '  curl -X POST http://localhost:8000/query \'
echo '    -H "Content-Type: application/json" \'
echo '    -d '"'"'{"session_id":"test","query_text":"What is Apple revenue?","models":["gemma"]}'"'"
echo ""
echo "  # Compare all three models"
echo '  curl -X POST http://localhost:8000/query \'
echo '    -H "Content-Type: application/json" \'
echo '    -d '"'"'{"session_id":"test","query_text":"What is Apple revenue?","models":["llama","gemma","gemini"]}'"'"
echo ""
echo "For more information, see: OLLAMA_SETUP.md"
echo ""
