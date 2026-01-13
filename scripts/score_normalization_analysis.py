"""
Quick calculation of KG relevance scores vs vector similarity scores
to understand the normalization mismatch.
"""

# From logs - typical values
weighted_counts = [7.6, 9.1, 7.3, 8.2, 11.3, 6.2, 10.8, 9.6, 10.5, 6.6, 8.3]
direct_recalls = [0.36, 0.50, 0.45, 0.53, 0.54, 0.36, 0.56, 0.47, 0.59, 0.37, 0.62]
boost = 1.0

print("=" * 80)
print("KG RELEVANCE SCORE CALCULATION")
print("=" * 80)
print(f"\nFormula: (weighted_count^2) × direct_recall × boost")
print(f"Boost = {boost}")

kg_scores = []
for wc, dr in zip(weighted_counts, direct_recalls):
    score = (wc ** 2) * dr * boost
    kg_scores.append(score)
    print(f"  ({wc:.1f}^2) × {dr:.2f} × {boost} = {score:.2f}")

avg_kg_score = sum(kg_scores) / len(kg_scores)
min_kg_score = min(kg_scores)
max_kg_score = max(kg_scores)

print(f"\n📊 KG Score Distribution:")
print(f"  Min:  {min_kg_score:.2f}")
print(f"  Avg:  {avg_kg_score:.2f}")
print(f"  Max:  {max_kg_score:.2f}")

# Vector similarity scores typically 0.7-0.9
print(f"\n" + "=" * 80)
print("VECTOR SIMILARITY SCORES")
print("=" * 80)
print(f"Range: 0.7 - 1.0 (after threshold filtering)")
print(f"Typical: ~0.8")

# Fusion normalization
print(f"\n" + "=" * 80)
print("NORMALIZATION IN FUSION")
print("=" * 80)

print(f"\n🔵 Vector (weighted fusion):")
print(f"  Raw similarity:     0.8 (typical)")
print(f"  After weight (0.5): 0.8 × 0.5 = 0.4")

print(f"\n🟢 KG (weighted fusion):")
print(f"  Raw relevance:      {avg_kg_score:.2f} (typical)")
print(f"  Normalized (/100):  {avg_kg_score:.2f} / 100 = {avg_kg_score/100:.4f}")
print(f"  After weight (0.5): {avg_kg_score/100:.4f} × 0.5 = {(avg_kg_score/100)*0.5:.4f}")

ratio = ((avg_kg_score/100)*0.5) / 0.4 if 0.4 > 0 else 0
print(f"\n⚖️  KG/Vector weighted score ratio: {ratio:.2f}")
print(f"  KG scores are {ratio:.1%} of vector scores!")

# Check with adaptive fusion (RRF + weighted)
print(f"\n" + "=" * 80)
print("ADAPTIVE FUSION ANALYSIS")
print("=" * 80)

rrf_k = 60
print(f"\n📐 RRF Component (k={rrf_k}):")
print(f"  Rank 1: 1/(60+1) = {1/(rrf_k+1):.4f}")
print(f"  Rank 3: 1/(60+3) = {1/(rrf_k+3):.4f}")
print(f"  Rank 5: 1/(60+5) = {1/(rrf_k+5):.4f}")

alpha = 0.3
vector_rrf = 1/(rrf_k+1)  # rank 1
vector_weighted = 0.4  # from above
vector_adaptive = vector_rrf + (vector_weighted * alpha)

kg_rrf = 1/(rrf_k+1)  # rank 1
kg_weighted = (avg_kg_score/100)*0.5  # from above
kg_adaptive = kg_rrf + (kg_weighted * alpha)

print(f"\n🔵 Vector (rank 1, adaptive):")
print(f"  RRF:      {vector_rrf:.4f}")
print(f"  Weighted: {vector_weighted:.4f}")
print(f"  Adaptive: {vector_rrf:.4f} + ({vector_weighted:.4f} × {alpha}) = {vector_adaptive:.4f}")

print(f"\n🟢 KG (rank 1, adaptive):")
print(f"  RRF:      {kg_rrf:.4f}")
print(f"  Weighted: {kg_weighted:.4f}")
print(f"  Adaptive: {kg_rrf:.4f} + ({kg_weighted:.4f} × {alpha}) = {kg_adaptive:.4f}")

print(f"\n⚖️  In adaptive fusion:")
print(f"  Vector: {vector_adaptive:.4f}")
print(f"  KG:     {kg_adaptive:.4f}")
print(f"  Ratio:  {kg_adaptive/vector_adaptive:.2f} ({(kg_adaptive/vector_adaptive)*100:.1f}%)")

# Recommendations
print(f"\n" + "=" * 80)
print("🔧 RECOMMENDATIONS")
print("=" * 80)

print(f"\n1. KG Normalization Issue:")
print(f"   Current: Divide by 100 (assumes max ~100)")
print(f"   Actual max observed: {max_kg_score:.1f}")
print(f"   → Should normalize by ~{max_kg_score*2:.0f} to allow headroom")

print(f"\n2. Alternative: Adjust KG weight:")
print(f"   Current KG weight: 0.5")
print(f"   To match vector scores, use: {0.5 * (0.4 / kg_weighted):.2f}")

print(f"\n3. Alternative: Dynamic normalization:")
print(f"   Instead of fixed /100, use percentile-based or max-observed normalization")

print(f"\n4. Check if boost should be higher:")
print(f"   Current boost: {boost}")
print(f"   If boost were 2.0, avg KG score would be: {avg_kg_score*2:.2f}")
print(f"   After normalization: {(avg_kg_score*2)/100:.4f} (still low!)")
