# Naive RAG vs KG-RAG Benchmarking Project

## Project Vision

A comprehensive benchmarking system to compare and evaluate three Retrieval-Augmented Generation (RAG) approaches for multi-hop question answering:

1. **Naive RAG**: Traditional vector-based retrieval using PostgreSQL with pgvector
2. **KG-RAG**: Knowledge Graph-based retrieval using Neo4j with Graphiti
3. **Hybrid RAG**: Combined approach leveraging both vector similarity and graph relationships

## Core Objectives

### Primary Goals
- **Quantitative Comparison**: Establish empirical performance metrics across three RAG architectures
- **Multi-hop Reasoning Analysis**: Evaluate how different retrieval strategies handle complex, multi-step reasoning tasks
- **Reproducible Experiments**: Create a fully containerized, configurable system for repeatable benchmarking
- **Cost-Effective Evaluation**: Support both cloud LLMs (Gemini) and local models (Ollama) for flexible experimentation

### Success Criteria
- Successfully run evaluation on 50-100 multi-hop questions from standard benchmarks
- Generate comprehensive metrics across 5 evaluation dimensions
- Produce actionable insights on when to use each RAG approach
- Complete local execution within reasonable time/resource constraints

## System Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                    BENCHMARKING SYSTEM                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Evaluation Orchestrator Agent              │    │
│  │  - Loads benchmark dataset                         │    │
│  │  - Routes questions to all 3 RAG variants         │    │
│  │  - Collects and saves responses                   │    │
│  └────────────────────────────────────────────────────┘    │
│                         ↓                                    │
│  ┌──────────────┬──────────────┬──────────────────────┐   │
│  │  Naive RAG   │   KG-RAG     │   Hybrid RAG         │   │
│  │  Pipeline    │   Pipeline   │   Pipeline           │   │
│  └──────────────┴──────────────┴──────────────────────┘   │
│         ↓               ↓                   ↓               │
│  ┌──────────────┬──────────────┬──────────────────────┐   │
│  │  PostgreSQL  │   Neo4j      │   Both Combined      │   │
│  │  + pgvector  │   + Graphiti │                      │   │
│  └──────────────┴──────────────┴──────────────────────┘   │
│                                                              │
│  ┌────────────────────────────────────────────────────┐   │
│  │         LLM Evaluation Service (Gemini)            │   │
│  │  - Scores answers across 5 dimensions              │   │
│  │  - Generates comparative analysis                  │   │
│  │  - Outputs structured scoring data                 │   │
│  └────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌────────────────────────────────────────────────────┐   │
│  │         Analysis & Visualization Module            │   │
│  │  - Statistical analysis of results                 │   │
│  │  - Comparative plots and charts                    │   │
│  │  - Summary report generation                       │   │
│  └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Ingestion Phase**:
   - Documents → Chunking → Embeddings → PostgreSQL (vector storage)
   - Documents → Chunking → Entity Extraction → Neo4j (knowledge graph)
   
2. **Evaluation Phase**:
   - Benchmark Questions → Orchestrator Agent
   - Orchestrator → Parallel execution on 3 RAG variants
   - Each variant retrieves context → Generates answer
   - Responses collected in structured JSON format

3. **Scoring Phase**:
   - Answers JSON → LLM Evaluator (Gemini)
   - LLM scores each answer on 5 dimensions (1-10 scale)
   - Scores saved with justifications

4. **Analysis Phase**:
   - Score aggregation and statistical analysis
   - Comparative visualizations (box plots, radar charts, etc.)
   - Insight generation and reporting

## Evaluation Dimensions

All answers will be scored on a 1-10 scale across these dimensions:

| Dimension | Description | Key Focus |
|-----------|-------------|-----------|
| **Correctness** | Factual accuracy of the answer | Is the answer factually correct? |
| **Completeness** | Full coverage of all aspects | Does it address all parts of the question? |
| **Relevance** | Alignment with the question | Is the answer on-topic and relevant? |
| **Faithfulness** | No hallucinated information | Does it add facts not in retrieved context? |
| **Clarity** | Clear, understandable expression | Is the answer well-structured and clear? |

## Technology Stack

### Core Infrastructure
- **PostgreSQL 16** with pgvector extension (vector similarity search)
- **Neo4j 5.x** with Graphiti library (knowledge graph storage)
- **Docker & Docker Compose** (containerization and orchestration)

### Python Stack
- **Pydantic AI** (agentic framework)
- **FastAPI** (API endpoints for evaluation)
- **asyncpg** (async PostgreSQL driver)
- **neo4j-driver** (Neo4j Python client)
- **LangChain** (for baseline RAG implementation)

### LLM Providers
- **Primary**: Google Gemini (gemini-1.5-pro, gemini-1.5-flash)
- **Secondary**: Ollama (llama3.1, mistral, qwen2.5, etc.)
- **Embeddings**: text-embedding-004 (Gemini) or nomic-embed-text (Ollama)

### Evaluation & Analysis
- **Pandas & NumPy** (data analysis)
- **Matplotlib & Seaborn** (visualization)
- **Jupyter Notebooks** (interactive exploration)

## Benchmark Datasets

### Primary Candidates
1. **HotpotQA** (Bridge & Comparison questions)
   - Well-established multi-hop benchmark
   - Rich supporting facts
   - ~100 carefully selected questions

2. **MultiHop-RAG** 
   - Specifically designed for RAG evaluation
   - Multiple reasoning patterns
   - Smaller, focused dataset

3. **WikiMultiHopQA**
   - Wikipedia-based questions
   - Various hop counts
   - Good for knowledge graph traversal

### Dataset Selection Strategy
- Start with 50-100 questions for local feasibility
- Include diverse question types (bridge, comparison, temporal)
- Ensure questions require multi-hop reasoning
- Balance difficulty levels

## Project Phases

### Phase 1: Foundation Setup
- Project structure and configuration
- Docker environment setup
- Database schema design
- Base ingestion pipeline

### Phase 2: RAG Implementations
- Naive RAG pipeline with vector search
- KG-RAG pipeline with graph traversal
- Hybrid RAG combining both approaches

### Phase 3: Evaluation Infrastructure
- Orchestrator agent for running benchmarks
- Response collection and JSON output
- LLM-based scoring service
- Score persistence

### Phase 4: Analysis & Visualization
- Statistical analysis scripts
- Visualization generation
- Report templates
- Insight extraction

### Phase 5: Testing & Refinement
- End-to-end testing
- Performance optimization
- Documentation
- Final benchmarking runs

## Key Design Principles

1. **Modularity**: Each RAG variant is independently implementable and testable
2. **Configurability**: Easy switching between LLM providers, models, and parameters
3. **Reproducibility**: Containerized environment, version-pinned dependencies, seeded randomness
4. **Observability**: Comprehensive logging, timing metrics, and debugging outputs
5. **Scalability**: Async operations, batch processing, parallel execution where applicable
6. **Cost Awareness**: Support for local models to reduce API costs during development

## Output Artifacts

### During Execution
- `answers.json`: Raw responses from all three RAG variants
- `scores.json`: Detailed scoring with justifications
- `logs/`: Timestamped execution logs
- `metrics/`: Retrieval quality metrics (precision, recall, latency)

### Post-Analysis
- `analysis_report.md`: Comprehensive findings
- `figures/`: Box plots, radar charts, comparison visualizations
- `summary_statistics.csv`: Aggregated metrics
- `insights.md`: Key takeaways and recommendations

## Success Metrics

### Technical Metrics
- **Retrieval Quality**: Precision@K, Recall@K, MRR
- **Answer Quality**: Score distributions across 5 dimensions
- **Performance**: Latency per question, throughput
- **Resource Usage**: Memory, token consumption

### Research Metrics
- **Comparative Insights**: Which approach excels at what question types?
- **Multi-hop Analysis**: How does hop count affect each variant?
- **Trade-offs**: Performance vs. accuracy vs. cost

## Timeline Estimate

- **Planning & Setup**: 1-2 days
- **Implementation**: 5-7 days
- **Testing & Debugging**: 2-3 days
- **Evaluation Runs**: 1 day
- **Analysis & Reporting**: 1-2 days

**Total**: ~2 weeks for complete implementation and initial results

## References

- Cole Medin's Agentic RAG Repository: https://github.com/coleam00
- HotpotQA: https://hotpotqa.github.io/
- Graphiti Documentation: https://github.com/getzep/graphiti
- Pydantic AI: https://ai.pydantic.dev/
