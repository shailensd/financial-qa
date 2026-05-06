#!/bin/bash

# FinDoc Intelligence Backend Startup Script
# This script starts the FastAPI backend server with proper configuration

set -e  # Exit on error

echo "🚀 Starting FinDoc Intelligence Backend..."
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found at .venv"
    echo "Please create it first: python3 -m venv .venv"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source .venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo "Creating .env from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env file - please edit it with your configuration"
        echo ""
    else
        echo "❌ .env.example not found"
        exit 1
    fi
fi

# Check for required environment variables
echo "🔍 Checking environment configuration..."
source .env

if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  DATABASE_URL not set, using SQLite for testing"
    export DATABASE_URL="sqlite+aiosqlite:///./test.db"
fi

if [ -z "$GEMINI_API_KEY" ] || [ "$GEMINI_API_KEY" = "temp_key_for_migration" ]; then
    echo "⚠️  Warning: GEMINI_API_KEY not set or using temporary key"
    echo "   Get your key from: https://aistudio.google.com/apikey"
    echo "   The /query endpoint will not work without a valid key"
    echo ""
fi

# Create ChromaDB directory if it doesn't exist
if [ ! -d "$CHROMA_PERSIST_DIR" ]; then
    echo "📁 Creating ChromaDB directory: $CHROMA_PERSIST_DIR"
    mkdir -p "$CHROMA_PERSIST_DIR"
fi

# Check if data has been ingested
CHUNK_COUNT=0
if [[ $DATABASE_URL == postgresql* ]]; then
    CHUNK_COUNT=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM chunks;" 2>/dev/null || echo "0")
fi

if [ "$CHUNK_COUNT" -eq 0 ]; then
    echo "⚠️  Warning: No data found in database"
    echo "   Run data ingestion scripts to enable query functionality:"
    echo "   1. python scripts/download_filings.py"
    echo "   2. python scripts/ingest_filings.py"
    echo ""
fi

# Display configuration
echo "📋 Configuration:"
echo "   Database: $DATABASE_URL"
echo "   ChromaDB: $CHROMA_PERSIST_DIR"
echo "   API Key: ${GEMINI_API_KEY:0:10}..." 
echo ""

# Start the server
echo "🌐 Starting FastAPI server on http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo "   Health Check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start uvicorn with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
