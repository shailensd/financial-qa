#!/bin/bash

# FinDoc Intelligence Setup Test Script
# This script verifies your backend setup is ready to run

echo "🔍 FinDoc Intelligence Backend Setup Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check counters
PASS=0
WARN=0
FAIL=0

# Function to print status
print_status() {
    if [ "$1" = "PASS" ]; then
        echo -e "${GREEN}✓${NC} $2"
        ((PASS++))
    elif [ "$1" = "WARN" ]; then
        echo -e "${YELLOW}⚠${NC} $2"
        ((WARN++))
    else
        echo -e "${RED}✗${NC} $2"
        ((FAIL++))
    fi
}

# 1. Check Python version
echo "1. Checking Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_status "PASS" "Python $PYTHON_VERSION found"
else
    print_status "FAIL" "Python 3 not found"
fi
echo ""

# 2. Check virtual environment
echo "2. Checking virtual environment..."
if [ -d ".venv" ]; then
    print_status "PASS" "Virtual environment exists at .venv/"
    
    # Check if uvicorn is installed
    if [ -f ".venv/bin/uvicorn" ]; then
        print_status "PASS" "uvicorn installed"
    else
        print_status "FAIL" "uvicorn not found - run: pip install -r requirements.txt"
    fi
else
    print_status "FAIL" "Virtual environment not found - run: python3 -m venv .venv"
fi
echo ""

# 3. Check .env file
echo "3. Checking environment configuration..."
if [ -f ".env" ]; then
    print_status "PASS" ".env file exists"
    
    # Source .env and check variables
    source .env
    
    if [ -n "$DATABASE_URL" ]; then
        print_status "PASS" "DATABASE_URL is set"
    else
        print_status "WARN" "DATABASE_URL not set - will use SQLite"
    fi
    
    if [ -n "$GEMINI_API_KEY" ] && [ "$GEMINI_API_KEY" != "temp_key_for_migration" ]; then
        print_status "PASS" "GEMINI_API_KEY is set"
    else
        print_status "WARN" "GEMINI_API_KEY not set or using temp key"
    fi
    
    if [ -n "$CHROMA_PERSIST_DIR" ]; then
        print_status "PASS" "CHROMA_PERSIST_DIR is set to: $CHROMA_PERSIST_DIR"
    else
        print_status "WARN" "CHROMA_PERSIST_DIR not set"
    fi
else
    print_status "FAIL" ".env file not found"
    if [ -f ".env.example" ]; then
        echo "   Run: cp .env.example .env"
    fi
fi
echo ""

# 4. Check database connection
echo "4. Checking database..."
if [ -n "$DATABASE_URL" ]; then
    if [[ $DATABASE_URL == postgresql* ]]; then
        if command -v psql &> /dev/null; then
            if psql "$DATABASE_URL" -c "SELECT 1;" &> /dev/null; then
                print_status "PASS" "PostgreSQL connection successful"
                
                # Check if tables exist
                TABLE_COUNT=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo "0")
                if [ "$TABLE_COUNT" -gt 0 ]; then
                    print_status "PASS" "Database has $TABLE_COUNT tables"
                else
                    print_status "WARN" "No tables found - run: alembic upgrade head"
                fi
            else
                print_status "FAIL" "Cannot connect to PostgreSQL"
            fi
        else
            print_status "WARN" "psql not found - cannot verify PostgreSQL connection"
        fi
    elif [[ $DATABASE_URL == sqlite* ]]; then
        print_status "PASS" "Using SQLite (good for testing)"
    fi
else
    print_status "WARN" "DATABASE_URL not set"
fi
echo ""

# 5. Check ChromaDB directory
echo "5. Checking ChromaDB..."
if [ -n "$CHROMA_PERSIST_DIR" ] && [ -d "$CHROMA_PERSIST_DIR" ]; then
    print_status "PASS" "ChromaDB directory exists"
else
    print_status "WARN" "ChromaDB directory not found - will be created on startup"
fi
echo ""

# 6. Check data ingestion
echo "6. Checking data ingestion..."
if [ -d "data/raw" ]; then
    FILE_COUNT=$(find data/raw -name "*.html" -o -name "*.txt" | wc -l | tr -d ' ')
    if [ "$FILE_COUNT" -gt 0 ]; then
        print_status "PASS" "Found $FILE_COUNT SEC filing files"
    else
        print_status "WARN" "No SEC filings found - run: python scripts/download_filings.py"
    fi
else
    print_status "WARN" "data/raw directory not found - run download script"
fi

if [ -n "$DATABASE_URL" ] && [[ $DATABASE_URL == postgresql* ]]; then
    CHUNK_COUNT=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM chunks;" 2>/dev/null || echo "0")
    CHUNK_COUNT=$(echo $CHUNK_COUNT | tr -d ' ')
    if [ "$CHUNK_COUNT" -gt 0 ]; then
        print_status "PASS" "Database has $CHUNK_COUNT chunks ingested"
    else
        print_status "WARN" "No chunks in database - run: python scripts/ingest_filings.py"
    fi
fi
echo ""

# 7. Check required Python packages
echo "7. Checking Python dependencies..."
if [ -f ".venv/bin/python" ]; then
    REQUIRED_PACKAGES=("fastapi" "uvicorn" "sqlalchemy" "chromadb" "sentence-transformers" "langgraph")
    
    for package in "${REQUIRED_PACKAGES[@]}"; do
        if .venv/bin/python -c "import $package" 2>/dev/null; then
            print_status "PASS" "$package installed"
        else
            print_status "FAIL" "$package not installed"
        fi
    done
else
    print_status "WARN" "Cannot check packages - virtual environment not activated"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Summary:"
echo -e "  ${GREEN}✓ Passed: $PASS${NC}"
echo -e "  ${YELLOW}⚠ Warnings: $WARN${NC}"
echo -e "  ${RED}✗ Failed: $FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ Setup looks good! You can start the server with:${NC}"
    echo "  ./start_server.sh"
    echo ""
    echo "Or manually:"
    echo "  source .venv/bin/activate"
    echo "  uvicorn app.main:app --reload"
else
    echo -e "${RED}✗ Please fix the failed checks before starting the server${NC}"
fi
echo ""
