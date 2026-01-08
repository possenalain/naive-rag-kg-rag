# Technical Architecture

## System Overview

This document details the technical architecture for the RAG benchmarking system comparing Naive RAG, Knowledge Graph RAG, and Hybrid RAG approaches.

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                          │
│  - CLI Interface                                                 │
│  - Jupyter Notebooks                                             │
│  - API Endpoints (Optional)                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION LAYER                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Evaluation Orchestrator (Pydantic AI Agent)      │  │
│  │  - Question loading and distribution                     │  │
│  │  - Parallel RAG variant execution                        │  │
│  │  - Response collection and aggregation                   │  │
│  │  - Metrics tracking                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                           │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐ │
│  │  Naive RAG     │  │   KG-RAG       │  │   Hybrid RAG     │ │
│  │  Pipeline      │  │   Pipeline     │  │   Pipeline       │ │
│  │                │  │                │  │                  │ │
│  │ - Embedding    │  │ - Entity       │  │ - Parallel       │ │
│  │ - Vector       │  │   Extraction   │  │   Retrieval      │ │
│  │   Search       │  │ - Graph        │  │ - Context        │ │
│  │ - Context      │  │   Traversal    │  │   Fusion         │ │
│  │   Assembly     │  │ - Subgraph     │  │ - Unified        │ │
│  │ - Generation   │  │   Extraction   │  │   Generation     │ │
│  └────────────────┘  └────────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        SERVICE LAYER                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │  LLM Service     │  │  Embedding       │  │  Scoring     │ │
│  │  - Generation    │  │  Service         │  │  Service     │ │
│  │  - Streaming     │  │  - Batch         │  │  - LLM-based │ │
│  │  - Provider      │  │    Generation    │  │  - Multi-    │ │
│  │    Switching     │  │  - Caching       │  │    dimension │ │
│  └──────────────────┘  └──────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     DATA ACCESS LAYER                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │  Vector Store    │  │  Graph Store     │  │  Metadata    │ │
│  │  - PostgreSQL    │  │  - Neo4j         │  │  Store       │ │
│  │  - pgvector      │  │  - Graphiti      │  │  - PostgreSQL│ │
│  │  - Similarity    │  │  - Traversal     │  │  - Results   │ │
│  │    Search        │  │  - Relationships │  │  - Scores    │ │
│  └──────────────────┘  └──────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                          │
│  - Docker & Docker Compose                                       │
│  - Volume Management                                             │
│  - Network Configuration                                         │
│  - Environment Management                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Ingestion Pipeline

```python
┌──────────────────────────────────────────────────────────────┐
│                    INGESTION PIPELINE                         │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Document Source                                              │
│       ↓                                                       │
│  Document Loader                                              │
│   - Markdown Parser                                           │
│   - Metadata Extraction                                       │
│       ↓                                                       │
│  Semantic Chunker                                             │
│   - Sentence Splitting                                        │
│   - Token-based Chunking                                      │
│   - Overlap Management                                        │
│       ↓                                                       │
│  ┌─────────────────┐         ┌─────────────────┐           │
│  │  Vector Path    │         │  Graph Path     │           │
│  │                 │         │                 │           │
│  │  Embedding Gen  │         │  Entity Extract │           │
│  │       ↓         │         │       ↓         │           │
│  │  PostgreSQL     │         │  Relationship   │           │
│  │  Storage        │         │  Extraction     │           │
│  │                 │         │       ↓         │           │
│  │                 │         │  Neo4j Storage  │           │
│  └─────────────────┘         └─────────────────┘           │
└──────────────────────────────────────────────────────────────┘
```

**Key Classes**:
```python
class DocumentLoader:
    def load_documents(path: str) -> List[Document]
    def extract_metadata(doc: Document) -> Dict[str, Any]

class SemanticChunker:
    def chunk(text: str, config: ChunkConfig) -> List[Chunk]
    def create_overlaps(chunks: List[Chunk]) -> List[Chunk]

class EmbeddingService:
    async def embed_batch(texts: List[str]) -> List[Vector]
    async def embed_single(text: str) -> Vector

class GraphBuilder:
    async def extract_entities(text: str) -> List[Entity]
    async def extract_relationships(entities: List[Entity]) -> List[Relationship]
    async def insert_to_graph(entities, relationships)
```

---

### 2. Naive RAG Pipeline

```python
┌────────────────────────────────────────────────────────┐
│              NAIVE RAG ARCHITECTURE                     │
├────────────────────────────────────────────────────────┤
│                                                         │
│  User Query                                             │
│       ↓                                                 │
│  Query Processing                                       │
│   - Normalization                                       │
│   - Embedding Generation                                │
│       ↓                                                 │
│  Vector Search (PostgreSQL + pgvector)                  │
│   - Cosine Similarity                                   │
│   - Top-K Retrieval                                     │
│       ↓                                                 │
│  Optional: Re-ranking                                   │
│   - Cross-encoder Scoring                               │
│   - MMR (Maximal Marginal Relevance)                    │
│       ↓                                                 │
│  Context Assembly                                       │
│   - Chunk Ordering                                      │
│   - Deduplication                                       │
│   - Formatting                                          │
│       ↓                                                 │
│  LLM Generation                                         │
│   - Prompt Construction                                 │
│   - Answer Generation                                   │
│       ↓                                                 │
│  Response + Metadata                                    │
│   - Answer Text                                         │
│   - Retrieved Chunks                                    │
│   - Retrieval Metrics                                   │
│                                                         │
└────────────────────────────────────────────────────────┘
```

**Implementation**:
```python
class NaiveRAG:
    def __init__(self, vector_store, llm_client, embedding_service):
        self.vector_store = vector_store
        self.llm = llm_client
        self.embedder = embedding_service
        
    async def retrieve(self, query: str, top_k: int = 5) -> List[Chunk]:
        # Generate query embedding
        query_vector = await self.embedder.embed_single(query)
        
        # Vector similarity search
        chunks = await self.vector_store.similarity_search(
            query_vector, 
            top_k=top_k
        )
        
        # Optional: Re-rank
        if self.use_reranking:
            chunks = await self.rerank(query, chunks)
            
        return chunks
    
    async def generate(self, query: str, chunks: List[Chunk]) -> str:
        # Assemble context
        context = self._format_context(chunks)
        
        # Create prompt
        prompt = self._build_prompt(query, context)
        
        # Generate answer
        answer = await self.llm.generate(prompt)
        
        return answer
    
    async def run(self, question: str) -> RAGResponse:
        chunks = await self.retrieve(question)
        answer = await self.generate(question, chunks)
        
        return RAGResponse(
            question=question,
            answer=answer,
            chunks=chunks,
            metrics=self._collect_metrics()
        )
```

---

### 3. Knowledge Graph RAG Pipeline

```python
┌────────────────────────────────────────────────────────┐
│           KNOWLEDGE GRAPH RAG ARCHITECTURE              │
├────────────────────────────────────────────────────────┤
│                                                         │
│  User Query                                             │
│       ↓                                                 │
│  Query Analysis                                         │
│   - Entity Extraction (NER)                             │
│   - Intent Classification                               │
│       ↓                                                 │
│  Graph Traversal Strategy                               │
│   ┌─────────────┬──────────────┬─────────────────┐    │
│   │   BFS       │  Path Find   │   Temporal      │    │
│   │   Multi-hop │  Entity-to-  │   Time-based    │    │
│   │             │  Entity      │   Filtering     │    │
│   └─────────────┴──────────────┴─────────────────┘    │
│       ↓                                                 │
│  Subgraph Extraction                                    │
│   - Relevant Nodes                                      │
│   - Relationships                                       │
│   - Hop Limit (e.g., max 3 hops)                        │
│       ↓                                                 │
│  Context Serialization                                  │
│   - Graph-to-Text Conversion                            │
│   - Triple Formatting                                   │
│   - Structured Representation                           │
│       ↓                                                 │
│  LLM Generation                                         │
│   - Graph-aware Prompting                               │
│   - Structured Context                                  │
│       ↓                                                 │
│  Response + Graph Metadata                              │
│   - Answer Text                                         │
│   - Entities Traversed                                  │
│   - Relationship Paths                                  │
│                                                         │
└────────────────────────────────────────────────────────┘
```

**Cypher Query Examples**:
```cypher
// Find entities mentioned in query
MATCH (e:Entity)
WHERE e.name IN $query_entities
RETURN e

// Multi-hop traversal (2-hop example)
MATCH (start:Entity)-[r1:RELATED_TO*1..2]-(end:Entity)
WHERE start.name IN $query_entities
RETURN start, r1, end
LIMIT 50

// Path finding between entities
MATCH path = shortestPath(
  (a:Entity {name: $entity_a})-[*..5]-(b:Entity {name: $entity_b})
)
RETURN path

// Temporal query
MATCH (e:Entity)-[r:RELATED_TO]-(related:Entity)
WHERE e.name IN $query_entities
  AND r.timestamp >= $start_date
  AND r.timestamp <= $end_date
RETURN e, r, related
```

**Implementation**:
```python
class KnowledgeGraphRAG:
    def __init__(self, graph_store, llm_client, entity_extractor):
        self.graph = graph_store
        self.llm = llm_client
        self.entity_extractor = entity_extractor
        
    async def extract_query_entities(self, query: str) -> List[str]:
        # Use LLM or NER to extract entities
        entities = await self.entity_extractor.extract(query)
        return [e.name for e in entities]
    
    async def traverse_graph(
        self, 
        start_entities: List[str], 
        max_hops: int = 3
    ) -> Subgraph:
        # Multi-hop BFS traversal
        cypher = """
        MATCH (start:Entity)-[r:RELATED_TO*1..{max_hops}]-(end:Entity)
        WHERE start.name IN $entities
        RETURN start, r, end
        LIMIT 100
        """
        
        results = await self.graph.query(
            cypher, 
            entities=start_entities, 
            max_hops=max_hops
        )
        
        return Subgraph.from_results(results)
    
    def serialize_context(self, subgraph: Subgraph) -> str:
        # Convert graph to textual representation
        context_parts = []
        
        for entity in subgraph.entities:
            context_parts.append(f"Entity: {entity.name} ({entity.type})")
            
        for rel in subgraph.relationships:
            context_parts.append(
                f"{rel.source} --[{rel.type}]--> {rel.target}"
            )
            
        return "\n".join(context_parts)
    
    async def run(self, question: str) -> RAGResponse:
        # Extract entities from question
        entities = await self.extract_query_entities(question)
        
        # Traverse graph
        subgraph = await self.traverse_graph(entities)
        
        # Serialize to text
        context = self.serialize_context(subgraph)
        
        # Generate answer
        prompt = self._build_prompt(question, context)
        answer = await self.llm.generate(prompt)
        
        return RAGResponse(
            question=question,
            answer=answer,
            subgraph=subgraph,
            entities=entities,
            metrics=self._collect_metrics()
        )
```

---

### 4. Hybrid RAG Pipeline

```python
┌────────────────────────────────────────────────────────┐
│              HYBRID RAG ARCHITECTURE                    │
├────────────────────────────────────────────────────────┤
│                                                         │
│  User Query                                             │
│       ↓                                                 │
│  ┌──────────────────┬───────────────────────┐         │
│  │  Vector Path     │    Graph Path         │         │
│  │                  │                        │         │
│  │  Query Embedding │   Entity Extraction   │         │
│  │       ↓          │         ↓              │         │
│  │  Vector Search   │   Graph Traversal     │         │
│  │  (Top-K chunks)  │   (Subgraph)          │         │
│  └──────────────────┴───────────────────────┘         │
│       ↓                      ↓                          │
│  ┌─────────────────────────────────────────────┐      │
│  │         FUSION STRATEGY                      │      │
│  │                                              │      │
│  │  Option 1: Reciprocal Rank Fusion (RRF)     │      │
│  │    score = Σ 1/(k + rank_i)                 │      │
│  │                                              │      │
│  │  Option 2: Score-based Fusion               │      │
│  │    weighted_score = w1*vec_score +          │      │
│  │                     w2*graph_score           │      │
│  │                                              │      │
│  │  Option 3: Deduplication + Concatenation    │      │
│  │    context = unique(vector_chunks +         │      │
│  │                     graph_context)           │      │
│  └─────────────────────────────────────────────┘      │
│       ↓                                                 │
│  Unified Context Assembly                              │
│       ↓                                                 │
│  LLM Generation                                         │
│       ↓                                                 │
│  Response + Combined Metadata                          │
│                                                         │
└────────────────────────────────────────────────────────┘
```

**Implementation**:
```python
class HybridRAG:
    def __init__(self, naive_rag, kg_rag, fusion_strategy="rrf"):
        self.naive_rag = naive_rag
        self.kg_rag = kg_rag
        self.fusion_strategy = fusion_strategy
        
    async def retrieve_hybrid(self, query: str) -> CombinedContext:
        # Parallel retrieval
        vector_results, graph_results = await asyncio.gather(
            self.naive_rag.retrieve(query),
            self.kg_rag.traverse_graph(await self.kg_rag.extract_query_entities(query))
        )
        
        # Fuse results
        if self.fusion_strategy == "rrf":
            combined = self._reciprocal_rank_fusion(vector_results, graph_results)
        elif self.fusion_strategy == "weighted":
            combined = self._weighted_fusion(vector_results, graph_results)
        else:  # concatenation
            combined = self._concatenate_contexts(vector_results, graph_results)
            
        return combined
    
    def _reciprocal_rank_fusion(self, vec_results, graph_results, k=60):
        """RRF fusion algorithm"""
        scores = defaultdict(float)
        
        for rank, item in enumerate(vec_results):
            scores[item.id] += 1 / (k + rank + 1)
            
        for rank, item in enumerate(graph_results.to_chunks()):
            scores[item.id] += 1 / (k + rank + 1)
            
        # Sort by score and return top results
        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return self._assemble_context(sorted_items)
    
    async def run(self, question: str) -> RAGResponse:
        # Hybrid retrieval
        combined_context = await self.retrieve_hybrid(question)
        
        # Generate answer
        prompt = self._build_prompt(question, combined_context)
        answer = await self.llm.generate(prompt)
        
        return RAGResponse(
            question=question,
            answer=answer,
            context=combined_context,
            metrics=self._collect_metrics()
        )
```

---

### 5. Evaluation Architecture

```python
┌────────────────────────────────────────────────────────┐
│           EVALUATION ORCHESTRATOR                       │
├────────────────────────────────────────────────────────┤
│                                                         │
│  Benchmark Dataset Loader                               │
│       ↓                                                 │
│  Question Queue (50-100 questions)                      │
│       ↓                                                 │
│  ┌─────────────────────────────────────────────────┐  │
│  │  For each question in parallel:                 │  │
│  │                                                  │  │
│  │  ┌──────────┬──────────┬──────────────┐        │  │
│  │  │ Naive    │  KG      │  Hybrid      │        │  │
│  │  │ RAG      │  RAG     │  RAG         │        │  │
│  │  └──────────┴──────────┴──────────────┘        │  │
│  │       ↓           ↓           ↓                 │  │
│  │  ┌────────────────────────────────────┐        │  │
│  │  │  Collect Responses                 │        │  │
│  │  │  - Answer text                     │        │  │
│  │  │  - Retrieved context               │        │  │
│  │  │  - Metrics (latency, tokens)       │        │  │
│  │  └────────────────────────────────────┘        │  │
│  └─────────────────────────────────────────────────┘  │
│       ↓                                                 │
│  Aggregate Results                                      │
│   - Save to answers.json                                │
│   - Store in database                                   │
│       ↓                                                 │
│  ┌─────────────────────────────────────────────────┐  │
│  │           LLM SCORING SERVICE                   │  │
│  │                                                  │  │
│  │  For each (question, answer) pair:              │  │
│  │    - Score Correctness (1-10)                   │  │
│  │    - Score Completeness (1-10)                  │  │
│  │    - Score Relevance (1-10)                     │  │
│  │    - Score Faithfulness (1-10)                  │  │
│  │    - Score Clarity (1-10)                       │  │
│  │    - Extract justifications                     │  │
│  └─────────────────────────────────────────────────┘  │
│       ↓                                                 │
│  Save scores.json                                       │
│       ↓                                                 │
│  ┌─────────────────────────────────────────────────┐  │
│  │        STATISTICAL ANALYSIS                     │  │
│  │  - Aggregate scores                             │  │
│  │  - Compute statistics                           │  │
│  │  - Significance testing                         │  │
│  │  - Generate visualizations                      │  │
│  └─────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

---

## Data Models

### Core Models
```python
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class Document(BaseModel):
    id: str
    filename: str
    content: str
    metadata: Dict[str, Any]
    created_at: datetime

class Chunk(BaseModel):
    id: str
    document_id: str
    content: str
    embedding: Optional[List[float]]
    chunk_index: int
    metadata: Dict[str, Any]

class Entity(BaseModel):
    name: str
    type: str
    properties: Dict[str, Any]

class Relationship(BaseModel):
    source: str
    target: str
    type: str
    properties: Dict[str, Any]

class Question(BaseModel):
    id: str
    text: str
    answer: str  # Ground truth
    context: Optional[List[str]]
    question_type: Optional[str]
    difficulty: Optional[str]

class RAGResponse(BaseModel):
    question: str
    answer: str
    retrieved_chunks: List[Chunk]
    entities: Optional[List[Entity]]
    metrics: Dict[str, Any]
    timestamp: datetime

class DimensionScore(BaseModel):
    dimension: str
    score: int  # 1-10
    justification: str

class EvaluationResult(BaseModel):
    question_id: str
    question: str
    ground_truth: str
    naive_rag_answer: str
    kg_rag_answer: str
    hybrid_rag_answer: str
    naive_rag_context: List[Chunk]
    kg_rag_context: str
    hybrid_rag_context: str
    timestamp: datetime

class ScoringResult(BaseModel):
    evaluation_id: str
    variant: str  # "naive_rag", "kg_rag", "hybrid_rag"
    scores: List[DimensionScore]
    overall_score: float
    timestamp: datetime
```

---

## Database Schemas

### PostgreSQL Schema
```sql
-- Extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Documents
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Chunks with vector embeddings
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(768),  -- Dimension depends on model
    chunk_index INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
CREATE INDEX idx_chunks_embedding ON chunks 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);

-- Evaluations
CREATE TABLE evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_id VARCHAR(255) NOT NULL,
    question TEXT NOT NULL,
    ground_truth TEXT,
    naive_rag_answer TEXT,
    kg_rag_answer TEXT,
    hybrid_rag_answer TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Scores
CREATE TABLE scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_id UUID REFERENCES evaluations(id) ON DELETE CASCADE,
    rag_variant VARCHAR(50) NOT NULL,
    dimension VARCHAR(50) NOT NULL,
    score INTEGER CHECK (score BETWEEN 1 AND 10),
    justification TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_scores_evaluation_id ON scores(evaluation_id);
CREATE INDEX idx_scores_variant ON scores(rag_variant);
CREATE INDEX idx_scores_dimension ON scores(dimension);
```

### Neo4j Graph Schema
```
// Node Labels
(:Document {id, filename, created_at})
(:Chunk {id, content, chunk_index, document_id})
(:Entity {name, type, properties})
(:Topic {name, description})

// Relationship Types
(:Document)-[:CONTAINS]->(:Chunk)
(:Chunk)-[:MENTIONS]->(:Entity)
(:Chunk)-[:NEXT]->(:Chunk)
(:Entity)-[:RELATED_TO {type, weight, timestamp}]->(:Entity)
(:Entity)-[:BELONGS_TO]->(:Topic)
(:Entity)-[:OCCURS_IN]->(:Chunk)

// Indexes
CREATE INDEX entity_name FOR (e:Entity) ON (e.name);
CREATE INDEX entity_type FOR (e:Entity) ON (e.type);
CREATE INDEX chunk_document_id FOR (c:Chunk) ON (c.document_id);
```

---

## LLM Provider Abstraction

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        pass
    
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        pass

class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        self.api_key = api_key
        self.model = model
        # Initialize Gemini client
    
    async def generate(self, prompt: str, **kwargs) -> str:
        # Gemini API call
        pass
    
    async def embed(self, text: str) -> List[float]:
        # Gemini embedding API
        pass

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", 
                 model: str = "llama3.1"):
        self.base_url = base_url
        self.model = model
        # Initialize Ollama client
    
    async def generate(self, prompt: str, **kwargs) -> str:
        # Ollama API call
        pass
    
    async def embed(self, text: str) -> List[float]:
        # Ollama embedding (nomic-embed-text)
        pass

class LLMFactory:
    @staticmethod
    def create_provider(provider_type: str, **config) -> LLMProvider:
        if provider_type == "gemini":
            return GeminiProvider(**config)
        elif provider_type == "ollama":
            return OllamaProvider(**config)
        elif provider_type == "openai":
            return OpenAIProvider(**config)
        else:
            raise ValueError(f"Unknown provider: {provider_type}")
```

---

## Configuration Management

```python
from pydantic_settings import BaseSettings
from typing import Optional

class DatabaseSettings(BaseSettings):
    postgres_url: str
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str
    
    class Config:
        env_prefix = "DB_"

class LLMSettings(BaseSettings):
    provider: str = "gemini"  # gemini, ollama, openai
    model_name: str = "gemini-1.5-pro"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    
    class Config:
        env_prefix = "LLM_"

class EmbeddingSettings(BaseSettings):
    provider: str = "gemini"
    model_name: str = "text-embedding-004"
    dimensions: int = 768
    batch_size: int = 100
    
    class Config:
        env_prefix = "EMBEDDING_"

class IngestionSettings(BaseSettings):
    chunk_size: int = 512
    chunk_overlap: int = 50
    use_semantic_chunking: bool = True
    max_chunk_size: int = 1024
    
    class Config:
        env_prefix = "INGESTION_"

class BenchmarkSettings(BaseSettings):
    dataset_name: str = "hotpotqa"
    num_questions: int = 50
    batch_size: int = 10
    output_dir: str = "./benchmarks/results"
    
    class Config:
        env_prefix = "BENCHMARK_"

class Settings(BaseSettings):
    database: DatabaseSettings
    llm: LLMSettings
    embedding: EmbeddingSettings
    ingestion: IngestionSettings
    benchmark: BenchmarkSettings
    
    class Config:
        env_file = ".env"

# Global settings instance
settings = Settings()
```

---

## Deployment Architecture

### Docker Compose Services
```yaml
version: '3.8'

services:
  # PostgreSQL with pgvector
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-rag_benchmark}
      POSTGRES_USER: ${POSTGRES_USER:-raguser}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql/schema.sql:/docker-entrypoint-initdb.d/schema.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Neo4j with plugins
  neo4j:
    image: neo4j:5.15
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
      NEO4J_PLUGINS: '["apoc", "graph-data-science"]'
      NEO4J_dbms_memory_pagecache_size: 2G
      NEO4J_dbms_memory_heap_max__size: 2G
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - neo4j_plugins:/plugins
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    healthcheck:
      test: ["CMD-SHELL", "wget -O /dev/null -q http://localhost:7474 || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Optional: Ollama for local LLM
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  postgres_data:
  neo4j_data:
  neo4j_logs:
  neo4j_plugins:
  ollama_data:
```

---

## Performance Considerations

### Optimization Strategies

1. **Embedding Generation**
   - Batch processing (100+ texts at once)
   - Caching for repeated queries
   - Async operations

2. **Vector Search**
   - IVFFlat index for large datasets
   - Proper list parameter tuning
   - Connection pooling

3. **Graph Traversal**
   - Hop limit (max 3-4 hops)
   - Result size limits
   - Indexed properties

4. **LLM Calls**
   - Streaming responses
   - Retry with exponential backoff
   - Rate limiting
   - Context window management

5. **Parallel Execution**
   - async/await for I/O operations
   - Thread pools for CPU-bound tasks
   - Batch processing

---

## Security Considerations

1. **API Keys**: Never commit to version control
2. **Database Credentials**: Environment variables only
3. **Input Validation**: Sanitize all user inputs
4. **SQL Injection**: Use parameterized queries
5. **Cypher Injection**: Use parameter binding
6. **Rate Limiting**: Protect against abuse

---

## Monitoring & Logging

```python
import logging
import time
from functools import wraps

class MetricsCollector:
    def __init__(self):
        self.metrics = {
            "retrieval_latency": [],
            "generation_latency": [],
            "total_latency": [],
            "tokens_used": [],
            "chunks_retrieved": []
        }
    
    def record_latency(self, operation: str, latency: float):
        self.metrics[f"{operation}_latency"].append(latency)
    
    def record_tokens(self, count: int):
        self.metrics["tokens_used"].append(count)
    
    def get_summary(self):
        import numpy as np
        return {
            metric: {
                "mean": np.mean(values),
                "median": np.median(values),
                "std": np.std(values),
                "min": np.min(values),
                "max": np.max(values)
            }
            for metric, values in self.metrics.items()
            if values
        }

def timeit(operation_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            result = await func(*args, **kwargs)
            elapsed = time.time() - start
            logger.info(f"{operation_name} took {elapsed:.3f}s")
            return result
        return wrapper
    return decorator
```

---

## Error Handling Strategy

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class RAGError(Exception):
    """Base exception for RAG errors"""
    pass

class RetrievalError(RAGError):
    """Error during retrieval phase"""
    pass

class GenerationError(RAGError):
    """Error during generation phase"""
    pass

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def robust_llm_call(prompt: str):
    try:
        return await llm.generate(prompt)
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise GenerationError(f"Generation failed: {e}")
```

---

## Testing Strategy

### Unit Tests
- Individual component testing
- Mock external dependencies
- Test edge cases

### Integration Tests
- End-to-end pipeline testing
- Database operations
- API calls

### Performance Tests
- Latency benchmarks
- Memory profiling
- Concurrent request handling

---

## Appendix: Key Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Main language |
| PostgreSQL | 16 | Vector store |
| pgvector | 0.5+ | Vector extension |
| Neo4j | 5.15 | Graph database |
| Graphiti | Latest | Graph library |
| Pydantic AI | Latest | Agent framework |
| asyncpg | Latest | Async PostgreSQL |
| neo4j-driver | Latest | Neo4j Python |
| Docker | Latest | Containerization |

