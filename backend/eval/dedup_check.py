#!/usr/bin/env python3
"""
Deduplication checker for few-shot examples and evaluation set.

This script computes cosine similarity between queries in few_shot_examples.json
and evaluation_set_seed.json, flagging any pairs with similarity > 0.85 to prevent
data leakage.

Usage:
    python backend/eval/dedup_check.py
"""

import json
import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer


def load_json(filepath: Path) -> List[dict]:
    """Load JSON file and return parsed data."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_queries(data: List[dict], query_field: str) -> List[str]:
    """Extract query strings from data."""
    queries = []
    for item in data:
        if query_field in item:
            queries.append(item[query_field])
    return queries


def compute_cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


def find_duplicates(
    few_shot_queries: List[str],
    eval_queries: List[str],
    few_shot_ids: List[str],
    eval_ids: List[str],
    threshold: float = 0.85
) -> List[Tuple[str, str, float]]:
    """
    Find duplicate pairs between few-shot and evaluation queries.
    
    Args:
        few_shot_queries: List of few-shot example queries
        eval_queries: List of evaluation set queries
        few_shot_ids: List of few-shot example IDs
        eval_ids: List of evaluation set IDs
        threshold: Similarity threshold for flagging duplicates
    
    Returns:
        List of tuples (few_shot_id, eval_id, similarity_score)
    """
    print("Loading sentence transformer model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    print(f"Encoding {len(few_shot_queries)} few-shot queries...")
    few_shot_embeddings = model.encode(few_shot_queries, convert_to_numpy=True)
    
    print(f"Encoding {len(eval_queries)} evaluation queries...")
    eval_embeddings = model.encode(eval_queries, convert_to_numpy=True)
    
    duplicates = []
    
    print(f"\nComputing pairwise similarities (threshold: {threshold})...")
    for i, fs_emb in enumerate(few_shot_embeddings):
        for j, eval_emb in enumerate(eval_embeddings):
            similarity = compute_cosine_similarity(fs_emb, eval_emb)
            
            if similarity > threshold:
                duplicates.append((
                    few_shot_ids[i],
                    eval_ids[j],
                    similarity
                ))
    
    return duplicates


def main():
    """Main execution function."""
    # Define file paths
    script_dir = Path(__file__).parent
    few_shot_path = script_dir / "few_shot_examples.json"
    eval_path = script_dir / "evaluation_set_seed.json"
    
    # Check if files exist
    if not few_shot_path.exists():
        print(f"Error: {few_shot_path} not found")
        sys.exit(1)
    
    if not eval_path.exists():
        print(f"Error: {eval_path} not found")
        sys.exit(1)
    
    # Load data
    print(f"Loading few-shot examples from {few_shot_path}...")
    few_shot_data = load_json(few_shot_path)
    
    print(f"Loading evaluation set from {eval_path}...")
    eval_data = load_json(eval_path)
    
    # Extract queries and IDs
    few_shot_queries = extract_queries(few_shot_data, 'query')
    few_shot_ids = [item.get('id', f'unknown_{i}') for i, item in enumerate(few_shot_data)]
    
    eval_queries = extract_queries(eval_data, 'question')
    eval_ids = [item.get('id', f'unknown_{i}') for i, item in enumerate(eval_data)]
    
    print(f"\nDataset sizes:")
    print(f"  Few-shot examples: {len(few_shot_queries)}")
    print(f"  Evaluation cases: {len(eval_queries)}")
    
    # Find duplicates
    duplicates = find_duplicates(
        few_shot_queries,
        eval_queries,
        few_shot_ids,
        eval_ids,
        threshold=0.85
    )
    
    # Report results
    print("\n" + "="*70)
    if duplicates:
        print(f"⚠️  WARNING: Found {len(duplicates)} potential duplicate(s)!")
        print("="*70)
        
        for fs_id, eval_id, similarity in duplicates:
            print(f"\nFew-shot ID: {fs_id}")
            print(f"Eval ID: {eval_id}")
            print(f"Similarity: {similarity:.4f}")
            
            # Find and print the actual queries
            fs_query = next((q for i, q in enumerate(few_shot_queries) 
                           if few_shot_ids[i] == fs_id), "N/A")
            eval_query = next((q for i, q in enumerate(eval_queries) 
                             if eval_ids[i] == eval_id), "N/A")
            
            print(f"Few-shot query: {fs_query}")
            print(f"Eval query: {eval_query}")
            print("-" * 70)
        
        print("\n⚠️  Action required: Remove or modify the flagged few-shot examples")
        print("   to prevent data leakage between training and evaluation sets.")
        sys.exit(1)
    else:
        print("✓ No duplicates found!")
        print("="*70)
        print("\nAll few-shot examples are sufficiently distinct from the evaluation set.")
        print("Cosine similarity threshold: 0.85")
        sys.exit(0)


if __name__ == "__main__":
    main()
