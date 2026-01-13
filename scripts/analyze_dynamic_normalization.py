"""
Analyze the dynamic normalization approach vs fixed normalization.
Tests edge cases and compares behavior across different scenarios.
"""

def fixed_normalization(kg_raw):
    """Original fixed range normalization [10, 80] -> [0.7, 1.0]"""
    return 0.7 + (min(max(kg_raw, 10), 80) - 10) / 70 * 0.3

def dynamic_normalization(kg_raw, kg_min, kg_max, vector_min, vector_max):
    """New dynamic range normalization"""
    kg_range = kg_max - kg_min if kg_max > kg_min else 1.0
    kg_normalized = vector_min + ((kg_raw - kg_min) / kg_range) * (vector_max - vector_min)
    return max(min(kg_normalized, 1.0), 0.0)

# Test scenarios based on real log data
scenarios = [
    {
        "name": "Typical Query",
        "vector_scores": [0.75, 0.78, 0.82, 0.85, 0.89],
        "kg_scores": [20.79, 23.98, 35.64, 41.40, 65.32],
    },
    {
        "name": "High Vector Threshold (0.7+)",
        "vector_scores": [0.72, 0.75, 0.78, 0.83, 0.91],
        "kg_scores": [13.84, 16.12, 42.71, 43.32, 68.95],
    },
    {
        "name": "Low KG Scores",
        "vector_scores": [0.70, 0.75, 0.80, 0.85, 0.90],
        "kg_scores": [5.0, 8.0, 12.0, 15.0, 18.0],
    },
    {
        "name": "High KG Scores",
        "vector_scores": [0.70, 0.75, 0.80, 0.85, 0.90],
        "kg_scores": [60.0, 70.0, 80.0, 90.0, 100.0],
    },
    {
        "name": "Narrow Vector Range",
        "vector_scores": [0.85, 0.86, 0.87, 0.88, 0.89],
        "kg_scores": [20.0, 30.0, 40.0, 50.0, 60.0],
    },
    {
        "name": "Narrow KG Range",
        "vector_scores": [0.70, 0.75, 0.80, 0.85, 0.90],
        "kg_scores": [38.0, 39.0, 40.0, 41.0, 42.0],
    },
    {
        "name": "Edge Case: Single KG Score",
        "vector_scores": [0.70, 0.75, 0.80, 0.85, 0.90],
        "kg_scores": [35.0],
    },
    {
        "name": "Edge Case: All KG Same",
        "vector_scores": [0.70, 0.75, 0.80, 0.85, 0.90],
        "kg_scores": [40.0, 40.0, 40.0, 40.0, 40.0],
    },
]

print("=" * 100)
print("DYNAMIC vs FIXED NORMALIZATION ANALYSIS")
print("=" * 100)

for scenario in scenarios:
    print(f"\n{'='*100}")
    print(f"Scenario: {scenario['name']}")
    print(f"{'='*100}")
    
    vector_scores = scenario['vector_scores']
    kg_scores = scenario['kg_scores']
    
    vector_min = min(vector_scores)
    vector_max = max(vector_scores)
    kg_min = min(kg_scores)
    kg_max = max(kg_scores)
    
    print(f"\n📊 Input Ranges:")
    print(f"  Vector: [{vector_min:.2f}, {vector_max:.2f}] (range: {vector_max - vector_min:.2f})")
    print(f"  KG:     [{kg_min:.2f}, {kg_max:.2f}] (range: {kg_max - kg_min:.2f})")
    
    print(f"\n🔢 Normalized Scores:")
    print(f"  {'KG Raw':>10} | {'Fixed':>10} | {'Dynamic':>10} | {'Diff':>10} | {'Vector Ref':>12}")
    print(f"  {'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*12}")
    
    for i, kg_raw in enumerate(kg_scores):
        fixed = fixed_normalization(kg_raw)
        dynamic = dynamic_normalization(kg_raw, kg_min, kg_max, vector_min, vector_max)
        diff = dynamic - fixed
        vector_ref = vector_scores[min(i, len(vector_scores)-1)]
        
        print(f"  {kg_raw:10.2f} | {fixed:10.4f} | {dynamic:10.4f} | {diff:+10.4f} | {vector_ref:12.4f}")
    
    # Calculate statistics
    fixed_normalized = [fixed_normalization(kg) for kg in kg_scores]
    dynamic_normalized = [
        dynamic_normalization(kg, kg_min, kg_max, vector_min, vector_max) 
        for kg in kg_scores
    ]
    
    fixed_mean = sum(fixed_normalized) / len(fixed_normalized)
    dynamic_mean = sum(dynamic_normalized) / len(dynamic_normalized)
    vector_mean = sum(vector_scores) / len(vector_scores)
    
    print(f"\n📈 Statistics:")
    print(f"  Vector mean:  {vector_mean:.4f}")
    print(f"  Fixed mean:   {fixed_mean:.4f} (ratio to vector: {fixed_mean/vector_mean:.2%})")
    print(f"  Dynamic mean: {dynamic_mean:.4f} (ratio to vector: {dynamic_mean/vector_mean:.2%})")
    
    # Weighted fusion comparison (weight=0.5 for both)
    vector_weighted = vector_mean * 0.5
    fixed_weighted = fixed_mean * 0.5
    dynamic_weighted = dynamic_mean * 0.5
    
    print(f"\n⚖️  Weighted Fusion Impact (weight=0.5):")
    print(f"  Vector contribution:  {vector_weighted:.4f}")
    print(f"  Fixed KG:             {fixed_weighted:.4f} ({fixed_weighted/vector_weighted:.1%} of vector)")
    print(f"  Dynamic KG:           {dynamic_weighted:.4f} ({dynamic_weighted/vector_weighted:.1%} of vector)")
    
    # Identify issues
    issues = []
    
    if any(d > 1.0 or d < 0.0 for d in dynamic_normalized):
        issues.append("⚠️  Dynamic normalization produces out-of-bounds values!")
    
    if abs(dynamic_mean - vector_mean) / vector_mean > 0.15:
        issues.append(f"⚠️  Dynamic mean differs from vector mean by {abs(dynamic_mean - vector_mean) / vector_mean:.1%}")
    
    if kg_max == kg_min:
        issues.append("⚠️  Zero KG range - all scores collapse to vector_min!")
    
    if len(kg_scores) == 1:
        issues.append("ℹ️  Single KG score - maps to vector_min (rank 1 analogy)")
    
    if issues:
        print(f"\n🔍 Issues/Notes:")
        for issue in issues:
            print(f"  {issue}")

# Edge case analysis
print(f"\n\n{'='*100}")
print("EDGE CASE DEEP DIVE")
print(f"{'='*100}")

print("\n1️⃣  Zero KG Range (all scores identical)")
print("-" * 50)
kg_scores = [40.0, 40.0, 40.0]
vector_min, vector_max = 0.70, 0.90
kg_min = kg_max = 40.0
print(f"KG scores: {kg_scores}")
print(f"Vector range: [{vector_min}, {vector_max}]")
print(f"Result: All KG scores map to {vector_min:.2f}")
print("Behavior: Treats all as lowest rank (conservative)")
print("Impact: KG contribution reduced, but prevents division by zero")

print("\n2️⃣  KG Range Much Larger Than Vector Range")
print("-" * 50)
vector_scores = [0.85, 0.86, 0.87]  # Narrow range
kg_scores = [10.0, 50.0, 90.0]     # Wide range
vector_min, vector_max = min(vector_scores), max(vector_scores)
kg_min, kg_max = min(kg_scores), max(kg_scores)
print(f"Vector range: {vector_max - vector_min:.2f}")
print(f"KG range: {kg_max - kg_min:.2f}")
print(f"Ratio: {(kg_max - kg_min) / (vector_max - vector_min):.1f}x larger")
print("\nDynamic normalization:")
for kg in kg_scores:
    norm = dynamic_normalization(kg, kg_min, kg_max, vector_min, vector_max)
    print(f"  {kg:.1f} -> {norm:.4f}")
print("Behavior: Compresses KG differences into narrow vector range")
print("Impact: May reduce KG discriminative power in this query")

print("\n3️⃣  KG Scores Outside Typical Range")
print("-" * 50)
vector_scores = [0.70, 0.80, 0.90]
kg_scores = [150.0, 200.0, 250.0]  # Much higher than expected
vector_min, vector_max = min(vector_scores), max(vector_scores)
kg_min, kg_max = min(kg_scores), max(kg_scores)
print(f"KG scores: {kg_scores} (way above typical 10-80)")
print("\nFixed normalization (clips at 80):")
for kg in kg_scores:
    fixed = fixed_normalization(kg)
    print(f"  {kg:.1f} -> {fixed:.4f} (all clipped to 1.0)")
print("\nDynamic normalization:")
for kg in kg_scores:
    dynamic = dynamic_normalization(kg, kg_min, kg_max, vector_min, vector_max)
    print(f"  {kg:.1f} -> {dynamic:.4f}")
print("Behavior: Dynamic adapts, fixed clips. Dynamic preserves relative differences.")

# Recommendation summary
print(f"\n\n{'='*100}")
print("RECOMMENDATIONS & CONCLUSIONS")
print(f"{'='*100}")

print("""
✅ ADVANTAGES of Dynamic Normalization:
1. Adapts to actual score distributions (no hardcoded assumptions)
2. Preserves relative differences within each query
3. Handles extreme values gracefully (no clipping)
4. Works across different configurations (boost, weights, thresholds)
5. More theoretically sound (min-max scaling)

⚠️  POTENTIAL ISSUES:
1. Zero KG range edge case (all scores identical)
   → Mitigated: Falls back to vector_min (conservative, prevents div/0)
   
2. Narrow vector range with wide KG range
   → May compress KG discriminative power
   → Consider: Add warning when ranges differ by >10x
   
3. Single KG result
   → Maps to vector_min (rank 1 analogy)
   → Acceptable: Similar to RRF rank=1
   
4. Score contribution may vary more between queries
   → This is actually desirable - adapts to data quality!

🎯 FINAL VERDICT:
Dynamic normalization is SUPERIOR for most cases:
- More robust to configuration changes
- Better theoretical foundation
- Adapts to query-specific characteristics
- Only edge case concern is zero range (already handled)

💡 SUGGESTED ENHANCEMENTS:
1. Add debug logging showing normalization ranges
2. Warn if vector/KG range ratio exceeds threshold (e.g., 10x)
3. Consider adaptive weight adjustment based on range ratios
4. Track normalization statistics across queries for monitoring
""")
