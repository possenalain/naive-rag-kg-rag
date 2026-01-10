# Big Tech Curated Benchmark Dataset

## Overview
A comprehensive benchmark dataset for evaluating RAG (Retrieval-Augmented Generation) systems, curated from 21 documents covering the AI industry landscape including investments, company strategies, executive movements, technology developments, and market dynamics.

## Dataset Statistics
- **Total Questions**: 255
- **Factual Questions**: 90 (35%)
- **Multi-hop Questions**: 140 (55%)
- **Analytical Questions**: 25 (10%)
- **Source Documents**: 21 markdown files in `data/big_tech_docs/`
- **Format**: JSON
- **File**: `benchmarks/datasets/big_tech_curated.json`

## Question Types

### 1. Factual Questions (90 questions)
Single-hop questions requiring precise information retrieval from a single document.

**Characteristics:**
- Clear, factual answers (dates, amounts, names, percentages, etc.)
- Test precise recall of specific facts
- Difficulty: Easy to Medium
- Answer type examples: funding amounts, valuations, executive names, market share percentages, revenue metrics

**Example:**
```json
{
  "question_id": "fact_001",
  "question_text": "How much funding did OpenAI raise in their latest funding round?",
  "ground_truth": "OpenAI raised $6.6 billion in their latest funding round.",
  "source_documents": ["doc1_openai_funding.md"],
  "difficulty": "easy"
}
```

### 2. Multi-hop Questions (140 questions)
Questions requiring information synthesis across 2-4 documents with relationship understanding and inference.

**Characteristics:**
- Require connecting facts across multiple documents
- Test temporal reasoning and cause-effect relationships
- Require aggregation, comparison, and cross-document synthesis
- Difficulty: Medium to Hard
- Reasoning hops: 2-4

**Example:**
```json
{
  "question_id": "multi_001",
  "question_text": "Compare the total investments Microsoft made in OpenAI versus Amazon's investments in Anthropic.",
  "ground_truth": "Microsoft invested $13 billion total in OpenAI... Amazon invested $8 billion total in Anthropic...",
  "source_documents": ["doc1_openai_funding.md", "doc2_anthropic_amazon.md", "doc5_microsoft_openai_tensions.md"],
  "difficulty": "medium",
  "reasoning_hops": 2
}
```

### 3. Analytical Questions (25 questions)
Questions requiring comparison, trend analysis, and synthesis across 3-5 documents with deep reasoning.

**Characteristics:**
- Require strategic analysis and pattern identification
- Test understanding of implications and causation
- Synthesize information for high-level insights
- Difficulty: Expert
- Reasoning hops: 4-6

**Example:**
```json
{
  "question_id": "analysis_001",
  "question_text": "Compare and contrast the AI partnership strategies of Microsoft, Amazon, and Google...",
  "ground_truth": "Microsoft pursues an exclusive partnership strategy... Amazon takes a multi-provider marketplace approach... Google employs a hybrid strategy...",
  "source_documents": ["doc5_microsoft_openai_tensions.md", "doc2_anthropic_amazon.md", "doc6_google_ai_strategy.md", "doc17_cloud_wars.md"],
  "difficulty": "expert",
  "reasoning_hops": 5
}
```

## Schema Structure

Each question in the dataset follows this structure:

```json
{
  "question_id": "string (unique identifier, e.g., 'fact_001', 'multi_001', 'analysis_001')",
  "question_text": "string (the question to be answered)",
  "ground_truth": "string (the complete, correct answer)",
  "source_documents": ["array of source document filenames"],
  "difficulty": "string (easy|medium|hard|expert)",
  "reasoning_hops": "number (for multi-hop and analytical questions)",
  "metadata": {
    "topic": "string (categorization of question topic)",
    "entities": ["array of key entities mentioned"],
    "answer_type": "string (for factual questions)",
    "reasoning_type": "string (for multi-hop and analytical questions)"
  }
}
```

## Source Documents Coverage

The benchmark covers 21 documents from `data/big_tech_docs/`:

1. **doc1_openai_funding.md** - OpenAI's $6.6B funding round
2. **doc2_anthropic_amazon.md** - Amazon's $8B Anthropic investment
3. **doc3_meta_scale_acquisition.md** - Meta's $14.8B Scale AI acquisition
4. **doc4_databricks_funding.md** - Databricks' $10B Series J
5. **doc5_microsoft_openai_tensions.md** - Microsoft-OpenAI competitive dynamics
6. **doc6_google_ai_strategy.md** - Google's multi-front AI strategy
7. **doc7_sam_altman_profile.md** - Sam Altman leadership profile
8. **doc8_nvidia_dominance.md** - NVIDIA's market dominance
9. **doc9_ai_market_analysis.md** - Global AI market analysis
10. **doc10_apple_ai_struggles.md** - Apple's AI challenges
11. **doc11_investment_funding_trends.md** - AI investment trends 2024
12. **doc12_executive_moves.md** - Executive talent movements
13. **doc13_regulatory_landscape.md** - Global AI regulation
14. **doc14_patent_innovation.md** - AI patent filing trends
15. **doc15_competitive_analysis.md** - AI competitive dynamics
16. **doc16_startup_ecosystem.md** - AI startup ecosystem
17. **doc17_cloud_wars.md** - Cloud AI platform competition
18. **doc18_future_predictions.md** - AI industry predictions 2025-2030
19. **doc19_acquisition_targets.md** - AI M&A landscape
20. **doc20_international_competition.md** - Global AI race
21. **doc21_enterprise_adoption.md** - Enterprise AI adoption patterns

## Topic Coverage

The benchmark questions cover diverse AI industry topics:

- **Funding & Investments**: Venture capital, valuations, mega-rounds, investor patterns
- **Company Strategy**: Partnership approaches, competitive positioning, market strategies
- **Executive Movements**: Leadership changes, compensation, talent acquisition
- **Technology**: Foundation models, infrastructure, patents, innovation
- **Market Dynamics**: Market share, growth rates, competitive analysis
- **Regulation**: EU AI Act, US policy, international governance
- **Enterprise Adoption**: Use cases, ROI metrics, implementation patterns
- **Geopolitics**: US-China-EU competition, national AI strategies

## Usage for RAG Evaluation

This benchmark is designed to evaluate three RAG implementations:

1. **Naive RAG**: Simple vector similarity retrieval
2. **Knowledge Graph RAG**: Graph-based entity and relationship retrieval
3. **Hybrid RAG**: Combined approach

### Evaluation Workflow

1. **Question Loading**: Load questions from `big_tech_curated.json`
2. **RAG Processing**: Each system generates answers for all questions
3. **Answer Storage**: Store generated answers with retrieval metadata
4. **LLM Scoring**: Use LLM scorer to evaluate against ground truth
5. **Analysis**: Compare performance across question types and RAG variants

### Expected Performance Patterns

- **Naive RAG**: Should perform well on factual questions, struggle with multi-hop
- **Knowledge Graph RAG**: Should excel at multi-hop relationship questions
- **Hybrid RAG**: Should balance both capabilities

### Metrics to Track

- **Correctness**: Factual accuracy of generated answers
- **Completeness**: Coverage of all required information
- **Relevance**: Retrieved chunks contain answer information
- **Faithfulness**: Answer supported by retrieved content
- **Clarity**: Answer quality and readability

## Files Generated

- `benchmarks/datasets/big_tech_curated.json` - Main benchmark dataset (255 questions)
- `benchmarks/datasets/factual_questions.json` - Factual questions subset (90)
- `benchmarks/datasets/multihop_part1.json` - Multi-hop questions part 1 (30)
- `benchmarks/datasets/multihop_part2.json` - Multi-hop questions part 2 (30)
- `benchmarks/datasets/multihop_part3.json` - Multi-hop questions part 3 (25)
- `benchmarks/datasets/multihop_questions_part1.json` - Multi-hop questions part 4 (55)
- `benchmarks/datasets/analytical_questions.json` - Analytical questions (25)
- `benchmarks/merge_datasets.py` - Script to merge all datasets

## Next Steps

1. **Database Loading**: Load benchmark into PostgreSQL via CLI
2. **RAG Evaluation**: Run evaluation orchestrator on all three RAG variants
3. **Results Analysis**: Compare performance metrics across question types
4. **Iterative Improvement**: Use insights to tune RAG implementations

## Notes

- All ground truth answers are factually accurate based on source documents
- Questions are designed to test different retrieval and reasoning capabilities
- Dataset is balanced across difficulty levels and question types
- Source documents were ingested into the system before benchmark creation
