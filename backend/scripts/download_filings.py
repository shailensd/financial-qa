#!/usr/bin/env python3
"""
SEC EDGAR Filing Downloader

Downloads 10-K and 10-Q filings for specified companies from SEC EDGAR API.
Respects SEC rate limits (10 requests/second) and includes proper User-Agent header.
"""

import json
import os
import time
from pathlib import Path
from typing import List, Dict
import requests
from datetime import datetime

# Configuration
COMPANIES = {
    "AAPL": "0000320193",  # Apple Inc.
    "MSFT": "0000789019",  # Microsoft Corporation
    "GOOGL": "0001652044", # Alphabet Inc. (Google)
    "AMZN": "0001018724",  # Amazon.com Inc.
    "TSLA": "0001318605",  # Tesla Inc.
}

FILING_TYPES = ["10-K", "10-Q"]
FISCAL_YEARS = [2022, 2023, 2024]

# SEC EDGAR API configuration
BASE_URL = "https://data.sec.gov"
USER_AGENT = "FinDoc Intelligence Research Project contact@findoc.example.com"
RATE_LIMIT_DELAY = 0.1  # 100ms between requests = 10 req/sec

# Output directory
OUTPUT_DIR = Path("data/raw")


def get_company_filings(cik: str, ticker: str) -> List[Dict]:
    """
    Fetch filing metadata for a company from SEC EDGAR API.
    
    Args:
        cik: Central Index Key (CIK) for the company
        ticker: Stock ticker symbol
        
    Returns:
        List of filing metadata dictionaries
    """
    url = f"{BASE_URL}/submissions/CIK{cik}.json"
    headers = {"User-Agent": USER_AGENT}
    
    print(f"Fetching filings metadata for {ticker} (CIK: {cik})...")
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Extract recent filings
        recent_filings = data.get("filings", {}).get("recent", {})
        
        filings = []
        for i in range(len(recent_filings.get("form", []))):
            filing = {
                "form": recent_filings["form"][i],
                "filingDate": recent_filings["filingDate"][i],
                "accessionNumber": recent_filings["accessionNumber"][i],
                "primaryDocument": recent_filings["primaryDocument"][i],
            }
            filings.append(filing)
        
        return filings
    
    except requests.RequestException as e:
        print(f"Error fetching filings for {ticker}: {e}")
        return []


def filter_filings(filings: List[Dict], ticker: str) -> List[Dict]:
    """
    Filter filings by type and fiscal year.
    
    Args:
        filings: List of all filings
        ticker: Stock ticker symbol
        
    Returns:
        Filtered list of filings matching criteria
    """
    filtered = []
    
    for filing in filings:
        form_type = filing["form"]
        filing_date = filing["filingDate"]
        
        # Check if filing type matches
        if form_type not in FILING_TYPES:
            continue
        
        # Extract year from filing date (YYYY-MM-DD format)
        try:
            year = int(filing_date.split("-")[0])
        except (ValueError, IndexError):
            continue
        
        # Check if year is in target range
        if year not in FISCAL_YEARS:
            continue
        
        filtered.append(filing)
    
    print(f"  Found {len(filtered)} {FILING_TYPES} filings for {ticker} in years {FISCAL_YEARS}")
    return filtered


def download_filing(ticker: str, filing: Dict) -> bool:
    """
    Download a single filing document.
    
    Args:
        ticker: Stock ticker symbol
        filing: Filing metadata dictionary
        
    Returns:
        True if download successful, False otherwise
    """
    accession_number = filing["accessionNumber"]
    accession_number_no_dashes = accession_number.replace("-", "")
    primary_document = filing["primaryDocument"]
    form_type = filing["form"]
    filing_date = filing["filingDate"]
    
    # Construct document URL - SEC uses CIK without leading zeros in URL path
    cik_no_leading_zeros = COMPANIES[ticker].lstrip("0")
    url = f"https://www.sec.gov/Archives/edgar/data/{cik_no_leading_zeros}/{accession_number_no_dashes}/{primary_document}"
    
    # Create output directory for ticker
    ticker_dir = OUTPUT_DIR / ticker
    ticker_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine file extension based on document name
    if primary_document.endswith(".htm") or primary_document.endswith(".html"):
        extension = ".html"
    else:
        extension = ".txt"
    
    # Create output filename
    output_filename = f"{ticker}_{form_type}_{filing_date}{extension}"
    output_path = ticker_dir / output_filename
    
    # Skip if already downloaded
    if output_path.exists():
        print(f"  Skipping {output_filename} (already exists)")
        return True
    
    # Download the filing
    headers = {"User-Agent": USER_AGENT}
    
    try:
        print(f"  Downloading {output_filename}...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Save to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(response.text)
        
        print(f"  ✓ Saved {output_filename}")
        return True
    
    except requests.RequestException as e:
        print(f"  ✗ Error downloading {output_filename}: {e}")
        return False


def download_all_filings():
    """
    Main function to download all filings for all companies.
    """
    print("=" * 80)
    print("SEC EDGAR Filing Downloader")
    print("=" * 80)
    print(f"Companies: {', '.join(COMPANIES.keys())}")
    print(f"Filing types: {', '.join(FILING_TYPES)}")
    print(f"Fiscal years: {', '.join(map(str, FISCAL_YEARS))}")
    print(f"Output directory: {OUTPUT_DIR.absolute()}")
    print(f"Rate limit: 10 requests/second")
    print("=" * 80)
    print()
    
    total_downloaded = 0
    total_skipped = 0
    total_failed = 0
    
    for ticker, cik in COMPANIES.items():
        print(f"\n{'=' * 80}")
        print(f"Processing {ticker}")
        print(f"{'=' * 80}")
        
        # Fetch all filings metadata
        all_filings = get_company_filings(cik, ticker)
        time.sleep(RATE_LIMIT_DELAY)  # Rate limiting
        
        if not all_filings:
            print(f"No filings found for {ticker}")
            continue
        
        # Filter by type and year
        target_filings = filter_filings(all_filings, ticker)
        
        if not target_filings:
            print(f"No matching filings for {ticker}")
            continue
        
        # Download each filing
        for filing in target_filings:
            success = download_filing(ticker, filing)
            
            if success:
                if (OUTPUT_DIR / ticker / f"{ticker}_{filing['form']}_{filing['filingDate']}.html").exists() or \
                   (OUTPUT_DIR / ticker / f"{ticker}_{filing['form']}_{filing['filingDate']}.txt").exists():
                    total_downloaded += 1
            else:
                total_failed += 1
            
            # Rate limiting
            time.sleep(RATE_LIMIT_DELAY)
    
    print(f"\n{'=' * 80}")
    print("Download Summary")
    print(f"{'=' * 80}")
    print(f"Total filings downloaded: {total_downloaded}")
    print(f"Total filings failed: {total_failed}")
    print(f"Output directory: {OUTPUT_DIR.absolute()}")
    print("=" * 80)


if __name__ == "__main__":
    download_all_filings()
