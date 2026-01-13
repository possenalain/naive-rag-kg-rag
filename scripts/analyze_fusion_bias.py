"""
Analyze potential bias in hybrid fusion scoring.
Examines score distributions for vector vs KG chunks.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
import statistics

def analyze_fusion_scores(eval_file: Path) -> None:
    """Analyze fusion scores to detect bias."""
    
    with open(eval_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    hybrid_results = data.get('results', {}).get('hybrid', [])
    
    if not hybrid_results:
        print("No hybrid results found")
        return
    
    # Collect scores by source
    vector_only_scores = []
    kg_only_scores = []
    both_scores = []
    
    # Collect raw component scores
    vector_raw_similarities = []
    kg_raw_relevances = []
    
    for result in hybrid_results:
        retrieved_chunks = result.get('retrieved_chunks', [])
        
        for chunk in retrieved_chunks:
            fusion_score = chunk.get('fusion_score', 0)
            sources = chunk.get('retrieval_sources', [])
            
            # Categorize by source
            if len(sources) == 2 or 'both' in sources:
                both_scores.append(fusion_score)
            elif 'vector' in sources:
                vector_only_scores.append(fusion_score)
            elif 'kg' in sources:
                kg_only_scores.append(fusion_score)
            
            # Collect raw scores
            if 'similarity_score' in chunk:
                vector_raw_similarities.append(chunk['similarity_score'])
            if 'relevance_score' in chunk:
                kg_raw_relevances.append(chunk['relevance_score'])
    
    # Analysis
    print("=" * 80)
    print("FUSION SCORE ANALYSIS")
    print("=" * 80)
    
    print(f"\n📊 Distribution by Source:")
    print(f"  Vector-only chunks: {len(vector_only_scores)}")
    print(f"  KG-only chunks:     {len(kg_only_scores)}")
    print(f"  Both sources:       {len(both_scores)}")
    
    if vector_only_scores:
        print(f"\n🔵 Vector-Only Scores:")
        print(f"  Mean:   {statistics.mean(vector_only_scores):.4f}")
        print(f"  Median: {statistics.median(vector_only_scores):.4f}")
        print(f"  Min:    {min(vector_only_scores):.4f}")
        print(f"  Max:    {max(vector_only_scores):.4f}")
        if len(vector_only_scores) > 1:
            print(f"  StdDev: {statistics.stdev(vector_only_scores):.4f}")
    
    if kg_only_scores:
        print(f"\n🟢 KG-Only Scores:")
        print(f"  Mean:   {statistics.mean(kg_only_scores):.4f}")
        print(f"  Median: {statistics.median(kg_only_scores):.4f}")
        print(f"  Min:    {min(kg_only_scores):.4f}")
        print(f"  Max:    {max(kg_only_scores):.4f}")
        if len(kg_only_scores) > 1:
            print(f"  StdDev: {statistics.stdev(kg_only_scores):.4f}")
    
    if both_scores:
        print(f"\n🟣 Both Sources:")
        print(f"  Mean:   {statistics.mean(both_scores):.4f}")
        print(f"  Median: {statistics.median(both_scores):.4f}")
        print(f"  Min:    {min(both_scores):.4f}")
        print(f"  Max:    {max(both_scores):.4f}")
        if len(both_scores) > 1:
            print(f"  StdDev: {statistics.stdev(both_scores):.4f}")
    
    # Compare means
    if vector_only_scores and kg_only_scores:
        vector_mean = statistics.mean(vector_only_scores)
        kg_mean = statistics.mean(kg_only_scores)
        diff_pct = ((vector_mean - kg_mean) / kg_mean) * 100 if kg_mean > 0 else 0
        
        print(f"\n⚖️  Score Comparison:")
        print(f"  Vector mean: {vector_mean:.4f}")
        print(f"  KG mean:     {kg_mean:.4f}")
        print(f"  Difference:  {diff_pct:+.1f}%")
        
        if abs(diff_pct) > 20:
            print(f"  ⚠️  WARNING: {abs(diff_pct):.1f}% difference suggests potential bias!")
    
    # Raw score analysis
    print(f"\n📈 Raw Score Analysis:")
    if vector_raw_similarities:
        print(f"\n  Vector Similarity Scores (0-1 range):")
        print(f"    Mean:   {statistics.mean(vector_raw_similarities):.4f}")
        print(f"    Median: {statistics.median(vector_raw_similarities):.4f}")
        print(f"    Range:  [{min(vector_raw_similarities):.4f}, {max(vector_raw_similarities):.4f}]")
    
    if kg_raw_relevances:
        print(f"\n  KG Relevance Scores (weighted_count² × recall × boost):")
        print(f"    Mean:   {statistics.mean(kg_raw_relevances):.4f}")
        print(f"    Median: {statistics.median(kg_raw_relevances):.4f}")
        print(f"    Range:  [{min(kg_raw_relevances):.4f}, {max(kg_raw_relevances):.4f}]")
    
    # Normalization analysis
    if vector_raw_similarities and kg_raw_relevances:
        print(f"\n🔧 Normalization Analysis:")
        print(f"  Vector scores are already normalized (0-1)")
        print(f"  KG scores normalized by dividing by 100 (assumes max ~100)")
        
        kg_normalized_mean = statistics.mean([min(s/100.0, 1.0) for s in kg_raw_relevances])
        vector_normalized_mean = statistics.mean(vector_raw_similarities)
        
        print(f"\n  After normalization:")
        print(f"    Vector mean:     {vector_normalized_mean:.4f}")
        print(f"    KG mean:         {kg_normalized_mean:.4f}")
        print(f"    KG/Vector ratio: {kg_normalized_mean/vector_normalized_mean:.2f}" if vector_normalized_mean > 0 else "N/A")
        
        # Check if KG normalization is appropriate
        max_kg_raw = max(kg_raw_relevances)
        if max_kg_raw > 100:
            print(f"\n  ⚠️  WARNING: Max KG score ({max_kg_raw:.1f}) exceeds assumed max (100)!")
            print(f"      This will be clipped to 1.0, potentially under-valuing high KG scores.")
        elif max_kg_raw < 50:
            print(f"\n  ⚠️  WARNING: Max KG score ({max_kg_raw:.1f}) is much lower than assumed max (100)!")
            print(f"      KG scores may be under-weighted relative to vector scores.")
    
    # Examine top-ranked chunks
    print(f"\n🏆 Top 10 Chunks by Fusion Score:")
    all_chunks = []
    for result in hybrid_results[:5]:  # Sample first 5 questions
        for chunk in result.get('retrieved_chunks', []):
            all_chunks.append({
                'score': chunk.get('fusion_score', 0),
                'sources': chunk.get('retrieval_sources', []),
                'similarity': chunk.get('similarity_score'),
                'relevance': chunk.get('relevance_score'),
                'rrf': chunk.get('rrf_component'),
                'weighted': chunk.get('weighted_component')
            })
    
    all_chunks.sort(key=lambda x: x['score'], reverse=True)
    
    for i, chunk in enumerate(all_chunks[:10], 1):
        sources_str = '+'.join(chunk['sources'])
        print(f"  {i:2d}. Score: {chunk['score']:.4f} | Sources: {sources_str:10s}", end='')
        if chunk['rrf'] is not None and chunk['weighted'] is not None:
            print(f" | RRF: {chunk['rrf']:.4f} | Weighted: {chunk['weighted']:.4f}")
        else:
            print()

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_fusion_bias.py <eval_json_file>")
        print("\nExample:")
        print("  python scripts/analyze_fusion_bias.py benchmarks/multihop_part3_results_v7/eval_*.json")
        sys.exit(1)
    
    eval_file = Path(sys.argv[1])
    
    if not eval_file.exists():
        print(f"Error: File not found: {eval_file}")
        sys.exit(1)
    
    analyze_fusion_scores(eval_file)

if __name__ == "__main__":
    main()
