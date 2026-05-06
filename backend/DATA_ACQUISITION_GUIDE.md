# SEC Filing Data Acquisition Guide

## Overview

This guide explains how to download and ingest SEC filings for the FinDoc Intelligence system. Data acquisition is a critical step that must be completed **after Task 3** (DocumentProcessor implementation) and **before Task 4** (HybridRetriever testing).

## Timeline Position

```
Task 1-2   → Database + config ready
Task 3     → DocumentProcessor code written
             ↕
        *** DOWNLOAD & INGEST DATA HERE (Task 3.5) ***
             ↕
Task 4     → HybridRetriever can now search real chunks
Task 5-11  → Agent pipeline works on real data
Task 18    → Evaluation set grounded in real filings
```

## Data Scope

- **Companies**: 5 (AAPL, MSFT, GOOGL, AMZN, TSLA)
- **Fiscal Years**: 2022, 2023, 2024
- **Filing Types**: 10-K (annual), 10-Q (quarterly - 3 per year)
- **Total Filings**: ~50-60 documents
- **Expected Chunks**: ~15,000-25,000 after ingestion

## Step 1: Download SEC Filings

### Script: `backend/scripts/download_filings.py`

```python
import requests
import os
import time

# EDGAR requires a User-Agent header identifying you
HEADERS = {
    "User-Agent": "YourName your@email.com"  # EDGAR requires this - use your real info
}

COMPANIES = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "GOOGL": "0001652044",
    "AMZN": "0001018724",
    "TSLA": "0001318605"
}

FILING_TYPES = ["10-K", "10-Q"]

def get_filings(cik, filing_type, count=10):
    url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
    resp = requests.get(url, headers=HEADERS)
    data = resp.json()
    
    filings = data["filings"]["recent"]
    results = []
    for i, form in enumerate(filings["form"]):
        if form == filing_type:
            results.append({
                "accession": filings["accessionNumber"][i].replace("-", ""),
                "date": filings["filingDate"][i],
                "form": form
            })
    return results

def download_filing(cik, accession, ticker, form, date):
    filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/"
    
    # Get the filing index to find the actual document
    index_url = filing_url + "index.json"
    resp = requests.get(index_url, headers=HEADERS)
    index = resp.json()
    
    # Find the primary document (usually the .htm or .txt file)
    for doc in index["directory"]["item"]:
        if doc["type"] in ["10-K", "10-Q"] or doc["name"].endswith(".htm"):
            doc_url = filing_url + doc["name"]
            doc_resp = requests.get(doc_url, headers=HEADERS)
            
            # Save it
            os.makedirs(f"data/raw/{ticker}", exist_ok=True)
            filename = f"data/raw/{ticker}/{ticker}_{form}_{date}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(doc_resp.text)
            print(f"Downloaded: {filename}")
            break
        
    time.sleep(0.1)  # EDGAR rate limit: 10 requests/second max

# Run it
for ticker, cik in COMPANIES.items():
    for form in FILING_TYPES:
        filings = get_filings(cik, form)
        # Filter to 2022-2024 only
        recent = [f for f in filings if f["date"].startswith(("2022", "2023", "2024"))]
        for filing in recent[:8]:  # limit per company
            download_filing(cik, filing["accession"], ticker, form, filing["date"])
```

### Running the Download Script

```bash
cd backend
python scripts/download_filings.py
```

This creates a directory structure:
```
data/
  raw/
    AAPL/
      AAPL_10-K_2024-11-01.txt
      AAPL_10-Q_2024-08-02.txt
      ...
    MSFT/
      ...
```

**Time Required**: ~5-10 minutes (with rate limiting)

## Step 2: Ingest Filings into Database

### Script: `backend/scripts/ingest_filings.py`

```python
from app.ml.document_processor import DocumentProcessor
from app.database import SessionLocal
import os

processor = DocumentProcessor()
db = SessionLocal()

data_dir = "data/raw"

for ticker in os.listdir(data_dir):
    ticker_dir = f"{data_dir}/{ticker}"
    if not os.path.isdir(ticker_dir):
        continue
        
    for filename in os.listdir(ticker_dir):
        filepath = f"{ticker_dir}/{filename}"
        
        # Parse the filing type and year from filename
        parts = filename.replace(".txt", "").split("_")
        form_type = parts[1]   # "10-K" or "10-Q"
        date = parts[2]        # "2024-11-01"
        
        print(f"Ingesting {ticker} {form_type} {date}...")
        processor.ingest(
            filepath=filepath,
            company=ticker,
            filing_type=form_type,
            filing_date=date,
            db=db
        )

db.close()
print("Done. All filings ingested.")
```

### Running the Ingestion Script

```bash
cd backend
python scripts/ingest_filings.py
```

**Time Required**: 30-60 minutes (embedding generation is CPU-intensive)

**Note**: This is a one-time operation. Results are persisted to PostgreSQL and ChromaDB.

## Step 3: Verify Ingestion

After ingestion completes, verify the data:

```python
from app.database import SessionLocal
from app.models import Document, Chunk

db = SessionLocal()

# Check document count
doc_count = db.query(Document).count()
print(f"Total documents: {doc_count}")

# Check chunk count per company
from sqlalchemy import func
chunk_counts = db.query(
    Document.company,
    Document.filing_type,
    func.count(Chunk.id)
).join(Chunk).group_by(Document.company, Document.filing_type).all()

for company, filing_type, count in chunk_counts:
    print(f"{company} {filing_type}: {count} chunks")

db.close()
```

Expected output:
```
Total documents: 55
AAPL 10-K: 1200 chunks
AAPL 10-Q: 2800 chunks
MSFT 10-K: 1100 chunks
...
```

## HTML Cleaning

SEC EDGAR filings are typically HTML documents. The `parse()` function in `DocumentProcessor` includes HTML cleaning:

```python
from bs4 import BeautifulSoup

def clean_html(raw_text: str) -> str:
    """Remove HTML tags and extract clean text."""
    soup = BeautifulSoup(raw_text, "html.parser")
    return soup.get_text(separator=" ", strip=True)
```

This runs **before** any regex-based section splitting to ensure consistent text extraction.

## What Gets Created

After ingestion, your databases will contain:

| What | Where | Approx Count |
|------|-------|--------------|
| Filing metadata | PostgreSQL `documents` table | ~60 rows |
| Text chunks | PostgreSQL `chunks` table | ~15,000-25,000 rows |
| Embedding vectors | ChromaDB | ~15,000-25,000 vectors |
| BM25 index | Built in memory at server startup | Rebuilt each time |

## Why Do This Early?

Without real data, you cannot:

1. **Verify chunking works correctly** - Need to see actual section splits
2. **Tune retrieval parameters** - Need to test if the right chunks are found
3. **Write evaluation test cases** - Task 18 needs real filing content for ground truth
4. **Debug Critic number-matching** - Needs real numbers from real documents
5. **Test end-to-end pipeline** - Mocks hide integration issues

**Recommendation**: Complete data acquisition immediately after Task 3.6 (document processor unit tests pass), then test all subsequent tasks against real SEC filings.

## Troubleshooting

### Download Issues

- **403 Forbidden**: Missing or invalid User-Agent header
- **429 Too Many Requests**: Rate limit exceeded (add more delay)
- **Missing filings**: Some quarters may not have 10-Qs (consolidated into 10-K)

### Ingestion Issues

- **HTML parsing errors**: Ensure BeautifulSoup and lxml are installed
- **Embedding errors**: Check sentence-transformers model download
- **Database errors**: Verify PostgreSQL connection and schema migration
- **ChromaDB errors**: Check ChromaDB service is running

### Performance

- **Slow embedding**: Normal - embedding 60 documents takes 30-60 minutes on CPU
- **Memory usage**: Embedding generation can use 2-4GB RAM
- **Disk space**: Raw filings + embeddings = ~500MB-1GB total

## Next Steps

After successful ingestion:

1. ✅ Verify chunk counts per company
2. ✅ Test HybridRetriever with real queries (Task 4)
3. ✅ Build agent pipeline with real data (Tasks 5-11)
4. ✅ Create evaluation set from real filings (Task 18)
