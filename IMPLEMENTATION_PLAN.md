# Implementation Plan: Naive RAG vs KG-RAG Benchmarking

## Overview

This document outlines the detailed implementation plan for building a comprehensive benchmarking system to compare three RAG approaches. The plan is organized into sequential phases with clear tasks and deliverables.

---

## Phase 1: Foundation & Infrastructure Setup

### 1.1 Project Structure & Configuration
**Duration**: 0.5 days

#### Tasks
- [x] Create project directory structure
- [ ] Set up Python package structure with `__init__.py` files
- [ ] Create configuration management system
- [ ] Set up logging infrastructure
- [ ] Create `.env.example` template
- [ ] Initialize Git repository with `.gitignore`

#### Deliverables
```
naive-rag-kg-rag/
├── config/
│   ├── __init__.py
│   ├── settings.py          # Centralized configuration
│   └── logging.yaml         # Logging configuration
├── src/
│   ├── __init__.py
│   ├── ingestion/           # Document processing
│   ├── rag_variants/        # Three RAG implementations
│   ├── evaluation/          # Benchmarking and scoring
│   ├── analysis/            # Statistical analysis
│   └── utils/               # Shared utilities
├── benchmarks/
│   ├── datasets/            # Question datasets
│   └── results/             # Output results
├── docker/
│   ├── docker-compose.yml
│   ├── postgres/
│   ├── neo4j/
│   └── app/
├── tests/
├── notebooks/               # Jupyter notebooks for analysis
├── requirements.txt
├── .env.example
├── README.md
└── PROJECT_OVERVIEW.md
```

### 1.2 Database Infrastructure
**Duration**: 1 day

#### Tasks
- [ ] Create PostgreSQL Docker configuration
- [ ] Design and implement database schema
  - Documents table
  - Chunks table with vector column
  - Metadata tables
  - Indexes for efficient querying
- [ ] Create Neo4j Docker configuration
- [ ] Set up Graphiti initialization
- [ ] Create database migration scripts
- [ ] Implement connection pooling
- [ ] Add health check endpoints

#### SQL Schema Components
```sql
-- Core tables
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE chunks (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    content TEXT NOT NULL,
    embedding vector(768),  -- Adjust based on model
    chunk_index INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_chunks_embedding ON chunks 
USING ivfflat (embedding vector_cosine_ops);

-- Additional tables for evaluation
CREATE TABLE evaluations (
    id UUID PRIMARY KEY,
    question_id VARCHAR(255),
    question TEXT,
    ground_truth TEXT,
    naive_rag_answer TEXT,
    kg_rag_answer TEXT,
    hybrid_rag_answer TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE scores (
    id UUID PRIMARY KEY,
    evaluation_id UUID REFERENCES evaluations(id),
    rag_variant VARCHAR(50),
    correctness INTEGER CHECK (correctness BETWEEN 1 AND 10),
    completeness INTEGER CHECK (completeness BETWEEN 1 AND 10),
    relevance INTEGER CHECK (relevance BETWEEN 1 AND 10),
    faithfulness INTEGER CHECK (faithfulness BETWEEN 1 AND 10),
    clarity INTEGER CHECK (clarity BETWEEN 1 AND 10),
    justification TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### Neo4j Graph Schema
```
Nodes:
- Document (id, filename, created_at)
- Chunk (id, content, chunk_index)
- Entity (name, type, properties)
- Topic (name, description)

Relationships:
- (Document)-[:CONTAINS]->(Chunk)
- (Chunk)-[:MENTIONS]->(Entity)
- (Entity)-[:RELATED_TO]->(Entity)
- (Entity)-[:BELONGS_TO]->(Topic)
- (Chunk)-[:NEXT]->(Chunk)  # Sequential relationship
- (Entity)-[:OCCURS_IN]->(Chunk)
```

### 1.3 Docker Environment Setup
**Duration**: 0.5 days

#### Tasks
- [ ] Create `docker-compose.yml` with all services
  - PostgreSQL with pgvector
  - Neo4j
  - Application container (optional for API)
- [ ] Create Dockerfiles for custom images
- [ ] Set up volume mounts for persistence
- [ ] Configure networking between containers
- [ ] Create startup scripts and health checks
- [ ] Document Docker setup and commands

#### Docker Compose Structure
```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: rag_benchmark
      POSTGRES_USER: raguser
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
  
  neo4j:
    image: neo4j:5.15
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
      NEO4J_PLUGINS: '["apoc", "graph-data-science"]'
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt

volumes:
  postgres_data:
  neo4j_data:
  neo4j_logs:
```

### 1.4 Configuration Management
**Duration**: 0.5 days

#### Tasks
- [ ] Create `settings.py` using Pydantic Settings
- [ ] Implement environment variable loading
- [ ] Add validation for required configurations
- [ ] Create provider configurations (OpenAI, Gemini, Ollama)
- [ ] Document all configuration options

#### Configuration Classes
```python
from pydantic_settings import BaseSettings

class DatabaseSettings(BaseSettings):
    postgres_url: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str

class LLMSettings(BaseSettings):
    provider: str = "gemini"  # gemini, openai, ollama
    model_name: str
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.7

class EmbeddingSettings(BaseSettings):
    provider: str = "gemini"
    model_name: str = "text-embedding-004"
    dimensions: int = 768

class BenchmarkSettings(BaseSettings):
    dataset_name: str = "hotpotqa"
    num_questions: int = 50
    batch_size: int = 10
```

---

## Phase 2: Document Ingestion Pipeline

### 2.1 Core Ingestion Components
**Duration**: 1.5 days

#### Tasks
- [ ] Implement document loader (markdown, txt, JSON)
- [ ] Create semantic chunking strategy
  - Sentence-based splitting
  - Token-based splitting
  - Semantic similarity grouping
- [ ] Implement embedding generation
  - Support Gemini embeddings API
  - Support Ollama local embeddings
  - Batch processing for efficiency
- [ ] Create PostgreSQL insertion logic
  - Bulk insert optimization
  - Transaction management
  - Error handling and rollback

#### Key Classes
```python
class DocumentLoader:
    def load_documents(self, path: str) -> List[Document]
    def load_benchmark_dataset(self, dataset_name: str) -> List[Question]

class SemanticChunker:
    def chunk_document(self, document: Document) -> List[Chunk]
    def chunk_with_overlap(self, text: str, chunk_size: int, overlap: int)

class EmbeddingGenerator:
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]
    async def generate_embedding(self, text: str) -> List[float]

class VectorStore:
    async def insert_chunks(self, chunks: List[Chunk])
    async def search(self, query_embedding: List[float], top_k: int)
```

### 2.2 Knowledge Graph Building
**Duration**: 1.5 days

#### Tasks
- [ ] Integrate Graphiti library
- [ ] Implement entity extraction
  - Named entity recognition
  - Relationship extraction
  - Temporal information extraction
- [ ] Create graph insertion logic
- [ ] Implement graph indexing strategies
- [ ] Add graph traversal utilities

#### Graph Building Pipeline
```python
class GraphBuilder:
    async def initialize(self)
    async def process_document(self, document: Document)
    async def extract_entities(self, text: str) -> List[Entity]
    async def extract_relationships(self, entities: List[Entity]) -> List[Relationship]
    async def add_to_graph(self, entities: List[Entity], relationships: List[Relationship])
    async def build_temporal_index(self)
```

### 2.3 End-to-End Ingestion Script
**Duration**: 0.5 days

#### Tasks
- [ ] Create CLI for ingestion
- [ ] Implement progress tracking
- [ ] Add parallel processing
- [ ] Create ingestion report generation
- [ ] Add resume capability for interrupted ingestion

#### CLI Interface
```bash
# Ingest documents
python -m src.ingestion.ingest \
    --input-dir ./data/documents \
    --embedding-provider gemini \
    --build-graph \
    --clean

# Ingest benchmark dataset
python -m src.ingestion.ingest_benchmark \
    --dataset hotpotqa \
    --num-questions 50
```

---

## Phase 3: RAG Variant Implementations

### 3.1 Naive RAG (Vector-based)
**Duration**: 1 day

#### Tasks
- [ ] Implement query embedding generation
- [ ] Create vector similarity search
- [ ] Implement retrieval ranking
- [ ] Add re-ranking (optional)
- [ ] Create context assembly
- [ ] Implement answer generation
- [ ] Add retrieval metrics logging

#### Core Pipeline
```python
class NaiveRAG:
    async def retrieve(self, query: str, top_k: int = 5) -> List[Chunk]:
        """Vector similarity search"""
        
    async def generate_answer(self, query: str, context: List[Chunk]) -> str:
        """LLM-based answer generation"""
        
    async def run(self, question: str) -> RAGResponse:
        """End-to-end pipeline"""
        chunks = await self.retrieve(question)
        answer = await self.generate_answer(question, chunks)
        return RAGResponse(
            question=question,
            answer=answer,
            retrieved_chunks=chunks,
            metrics=self._collect_metrics()
        )
```

### 3.2 KG-RAG (Knowledge Graph-based)
**Duration**: 1.5 days

#### Tasks
- [ ] Implement entity extraction from query
- [ ] Create graph traversal strategies
  - BFS for multi-hop
  - Path finding between entities
  - Temporal traversal
- [ ] Implement subgraph extraction
- [ ] Create graph context serialization
- [ ] Implement answer generation with graph context
- [ ] Add graph traversal metrics

#### Graph Traversal
```python
class KnowledgeGraphRAG:
    async def extract_query_entities(self, query: str) -> List[str]:
        """Extract entities mentioned in query"""
        
    async def traverse_graph(self, start_entities: List[str], max_hops: int = 3) -> Subgraph:
        """Multi-hop graph traversal"""
        
    async def serialize_context(self, subgraph: Subgraph) -> str:
        """Convert graph to textual context"""
        
    async def run(self, question: str) -> RAGResponse:
        """End-to-end pipeline"""
```

### 3.3 Hybrid RAG (Combined Approach)
**Duration**: 1 day

#### Tasks
- [ ] Implement parallel retrieval
  - Vector search
  - Graph traversal
- [ ] Create fusion strategies
  - Score-based fusion
  - Reciprocal Rank Fusion
  - Context deduplication
- [ ] Implement unified context assembly
- [ ] Add weighting strategies
- [ ] Implement answer generation with mixed context

#### Hybrid Strategy
```python
class HybridRAG:
    async def retrieve_hybrid(self, query: str) -> CombinedContext:
        """Parallel retrieval from both sources"""
        vector_chunks, graph_context = await asyncio.gather(
            self.naive_rag.retrieve(query),
            self.kg_rag.traverse_graph(query)
        )
        return self.fuse_contexts(vector_chunks, graph_context)
    
    def fuse_contexts(self, vector_results, graph_results) -> CombinedContext:
        """Reciprocal Rank Fusion or score-based fusion"""
        
    async def run(self, question: str) -> RAGResponse:
        """End-to-end pipeline"""
```

---

## Phase 4: Evaluation Infrastructure

### 4.1 Orchestrator Agent
**Duration**: 1 day

#### Tasks
- [ ] Create Pydantic AI agent for orchestration
- [ ] Implement question loading from benchmark
- [ ] Create parallel execution of all 3 variants
- [ ] Implement response collection
- [ ] Add timeout handling
- [ ] Create progress tracking
- [ ] Implement JSON output formatting

#### Orchestrator Structure
```python
class EvaluationOrchestrator:
    def __init__(self, benchmark_dataset: str, output_path: str):
        self.naive_rag = NaiveRAG()
        self.kg_rag = KnowledgeGraphRAG()
        self.hybrid_rag = HybridRAG()
        
    async def run_evaluation(self, questions: List[Question]) -> EvaluationResults:
        """Run all questions through all variants"""
        results = []
        for question in tqdm(questions):
            result = await self.evaluate_question(question)
            results.append(result)
        return EvaluationResults(results)
    
    async def evaluate_question(self, question: Question) -> QuestionResult:
        """Run single question through all variants"""
        naive_answer, kg_answer, hybrid_answer = await asyncio.gather(
            self.naive_rag.run(question.text),
            self.kg_rag.run(question.text),
            self.hybrid_rag.run(question.text)
        )
        return QuestionResult(
            question=question.text,
            ground_truth=question.answer,
            naive_rag=naive_answer.answer,
            kg_rag=kg_answer.answer,
            hybrid_rag=hybrid_answer.answer,
            metadata={
                "naive_chunks": len(naive_answer.retrieved_chunks),
                "kg_entities": len(kg_answer.entities),
                ...
            }
        )
```

### 4.2 LLM-based Scoring Service
**Duration**: 1.5 days

#### Tasks
- [ ] Create scoring prompt templates
- [ ] Implement Gemini API integration for scoring
- [ ] Create structured output parsing
- [ ] Implement batch scoring
- [ ] Add retry logic and error handling
- [ ] Create scoring report generation
- [ ] Add justification extraction

#### Scoring System
```python
class LLMEvaluator:
    DIMENSIONS = ["correctness", "completeness", "relevance", "faithfulness", "clarity"]
    
    async def score_answer(self, question: str, ground_truth: str, 
                          answer: str, context: str) -> DimensionScores:
        """Score single answer on all dimensions"""
        prompt = self._build_scoring_prompt(question, ground_truth, answer, context)
        response = await self.llm_client.generate(prompt)
        return self._parse_scores(response)
    
    async def score_evaluation(self, evaluation: QuestionResult) -> ScoringResult:
        """Score all 3 variants for a question"""
        naive_scores, kg_scores, hybrid_scores = await asyncio.gather(
            self.score_answer(evaluation.question, evaluation.ground_truth, 
                            evaluation.naive_rag, evaluation.naive_context),
            self.score_answer(evaluation.question, evaluation.ground_truth,
                            evaluation.kg_rag, evaluation.kg_context),
            self.score_answer(evaluation.question, evaluation.ground_truth,
                            evaluation.hybrid_rag, evaluation.hybrid_context)
        )
        return ScoringResult(naive=naive_scores, kg=kg_scores, hybrid=hybrid_scores)
```

#### Scoring Prompt Template
```
You are an expert evaluator for question-answering systems. 
Evaluate the following answer on these dimensions (scale 1-10):

Question: {question}
Ground Truth: {ground_truth}
Answer: {answer}
Retrieved Context: {context}

Provide scores for:
1. Correctness: Factual accuracy compared to ground truth
2. Completeness: Does it cover all aspects of the question?
3. Relevance: Is it directly addressing the question?
4. Faithfulness: Does it only use information from the context?
5. Clarity: Is it well-structured and easy to understand?

Output format (JSON):
{
    "correctness": <1-10>,
    "correctness_justification": "<reasoning>",
    "completeness": <1-10>,
    ...
}
```

### 4.3 Results Persistence
**Duration**: 0.5 days

#### Tasks
- [ ] Create JSON output formatters
- [ ] Implement database persistence
- [ ] Add CSV export functionality
- [ ] Create results versioning
- [ ] Add metadata tracking

---

## Phase 5: Analysis & Visualization

### 5.1 Statistical Analysis Module
**Duration**: 1 day

#### Tasks
- [ ] Implement score aggregation
- [ ] Calculate summary statistics (mean, median, std dev)
- [ ] Perform statistical significance tests
  - Paired t-tests between variants
  - Wilcoxon signed-rank test
- [ ] Calculate correlation analysis
- [ ] Generate comparative metrics

#### Analysis Functions
```python
class StatisticalAnalyzer:
    def aggregate_scores(self, results: ScoringResults) -> AggregatedMetrics
    def compare_variants(self, variant_a: str, variant_b: str) -> ComparisonResult
    def perform_significance_test(self, scores_a, scores_b) -> TestResult
    def generate_summary_report(self) -> SummaryStatistics
```

### 5.2 Visualization Generation
**Duration**: 1 day

#### Tasks
- [ ] Create box plots for dimension scores
- [ ] Generate radar charts for comparative analysis
- [ ] Create distribution plots
- [ ] Generate correlation heatmaps
- [ ] Create performance comparison charts
- [ ] Add question-type breakdown visualizations

#### Visualizations to Generate
```python
class VisualizationGenerator:
    def plot_dimension_comparison(self, dimension: str)
    def plot_radar_chart(self, variants: List[str])
    def plot_score_distributions(self)
    def plot_performance_metrics(self)  # Latency, token usage
    def plot_question_type_analysis(self)
    def generate_all_figures(self, output_dir: str)
```

### 5.3 Jupyter Notebooks
**Duration**: 0.5 days

#### Tasks
- [ ] Create exploratory analysis notebook
- [ ] Create visualization notebook
- [ ] Create insight generation notebook
- [ ] Add interactive widgets for filtering
- [ ] Document analysis workflow

---

## Phase 6: Testing & Quality Assurance

### 6.1 Unit Tests
**Duration**: 1 day

#### Tasks
- [ ] Test document loading and chunking
- [ ] Test embedding generation
- [ ] Test database operations
- [ ] Test graph operations
- [ ] Test RAG variant implementations
- [ ] Test scoring logic
- [ ] Achieve >80% code coverage

### 6.2 Integration Tests
**Duration**: 1 day

#### Tasks
- [ ] Test end-to-end ingestion pipeline
- [ ] Test full RAG pipeline for each variant
- [ ] Test evaluation orchestration
- [ ] Test scoring pipeline
- [ ] Test Docker environment
- [ ] Create CI/CD pipeline (optional)

### 6.3 Performance Testing
**Duration**: 0.5 days

#### Tasks
- [ ] Benchmark retrieval latency
- [ ] Measure memory usage
- [ ] Profile token consumption
- [ ] Test concurrent request handling
- [ ] Optimize bottlenecks

---

## Phase 7: Documentation & Finalization

### 7.1 Documentation
**Duration**: 1 day

#### Tasks
- [ ] Complete README with setup instructions
- [ ] Document configuration options
- [ ] Create architecture diagrams
- [ ] Write API documentation
- [ ] Create troubleshooting guide
- [ ] Document benchmark results interpretation

### 7.2 Benchmarking Runs
**Duration**: 0.5 days

#### Tasks
- [ ] Run full benchmark on 50 questions
- [ ] Generate all reports and visualizations
- [ ] Validate results quality
- [ ] Create final summary report

### 7.3 Reproducibility Package
**Duration**: 0.5 days

#### Tasks
- [ ] Lock dependency versions
- [ ] Create sample data package
- [ ] Add seed configuration for reproducibility
- [ ] Create Docker image repository
- [ ] Write replication guide

---

## Implementation Priorities

### Critical Path
1. Database setup (Phase 1.2)
2. Ingestion pipeline (Phase 2)
3. RAG implementations (Phase 3)
4. Evaluation orchestrator (Phase 4.1)
5. Scoring service (Phase 4.2)
6. Analysis (Phase 5.1)

### Nice-to-Have
- Advanced re-ranking
- Interactive dashboards
- Real-time streaming evaluation
- Multi-language support
- Distributed evaluation

---

## Risk Mitigation

### Technical Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM API rate limits | High | Implement retry logic, use local models for testing |
| Memory constraints | Medium | Batch processing, streaming where possible |
| Graph traversal complexity | Medium | Limit max hops, implement timeouts |
| Evaluation consistency | High | Use temperature=0, seed LLM calls, multiple runs |

### Resource Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| High API costs | High | Use Ollama for development, Gemini Flash for testing |
| Long execution times | Medium | Parallel processing, smaller initial dataset |
| Storage requirements | Low | Optimize chunk sizes, clean old runs |

---

## Success Criteria

### Minimum Viable Product (MVP)
- [x] All 3 RAG variants implemented and functional
- [ ] Successfully run on 50 benchmark questions
- [ ] Generate scores for all 5 dimensions
- [ ] Produce basic comparison visualizations
- [ ] Complete documentation

### Full Success
- [ ] Run on 100+ questions
- [ ] Statistical significance testing
- [ ] Comprehensive visualizations
- [ ] Insight-rich analysis report
- [ ] Reproducible Docker environment
- [ ] Published results and methodology

---

## Timeline Summary

| Phase | Duration | Priority |
|-------|----------|----------|
| Phase 1: Foundation | 2.5 days | Critical |
| Phase 2: Ingestion | 3.5 days | Critical |
| Phase 3: RAG Variants | 3.5 days | Critical |
| Phase 4: Evaluation | 3 days | Critical |
| Phase 5: Analysis | 2.5 days | High |
| Phase 6: Testing | 2.5 days | High |
| Phase 7: Documentation | 2 days | Medium |
| **Total** | **~19.5 days** | |

With parallel work and optimizations, target completion: **2-3 weeks**

---

## Next Steps

1. Review and refine this plan
2. Set up development environment
3. Create detailed task breakdown in issue tracker
4. Begin Phase 1 implementation
5. Establish code review and quality standards
