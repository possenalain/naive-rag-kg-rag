-- PostgreSQL Schema for RAG Benchmarking System
-- Version: 1.0
-- Date: 2026-01-08

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For text similarity

-- Drop existing tables (for clean setup)
DROP TABLE IF EXISTS scores CASCADE;
DROP TABLE IF EXISTS evaluations CASCADE;
DROP TABLE IF EXISTS chunks CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS benchmark_questions CASCADE;

-- =============================================================================
-- DOCUMENTS TABLE
-- Stores original documents before chunking
-- =============================================================================
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(255),
    document_type VARCHAR(50) DEFAULT 'markdown',
    metadata JSONB DEFAULT '{}',
    
    -- Statistics
    character_count INTEGER,
    word_count INTEGER,
    chunk_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes
    CONSTRAINT unique_filename UNIQUE(filename)
);

CREATE INDEX idx_documents_filename ON documents(filename);
CREATE INDEX idx_documents_source ON documents(source);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX idx_documents_metadata ON documents USING gin(metadata);

-- =============================================================================
-- CHUNKS TABLE
-- Stores document chunks with vector embeddings
-- =============================================================================
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Content
    content TEXT NOT NULL,
    embedding vector(768),  -- Adjust dimension based on your embedding model
                           -- 768 for text-embedding-004, nomic-embed-text
                           -- 1536 for text-embedding-3-small
                           -- 3072 for text-embedding-3-large
    
    -- Chunk metadata
    chunk_index INTEGER NOT NULL,
    start_char INTEGER,
    end_char INTEGER,
    token_count INTEGER,
    
    -- Additional metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_document_chunk UNIQUE(document_id, chunk_index)
);

-- Indexes for chunks
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
CREATE INDEX idx_chunks_chunk_index ON chunks(chunk_index);
CREATE INDEX idx_chunks_created_at ON chunks(created_at DESC);

-- Vector similarity search index
-- IVFFlat index for approximate nearest neighbor search
-- Lists parameter: sqrt(number_of_rows) is a good starting point
CREATE INDEX idx_chunks_embedding ON chunks 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);

-- Alternative: HNSW index (requires pgvector 0.5.0+)
-- CREATE INDEX idx_chunks_embedding_hnsw ON chunks 
--     USING hnsw (embedding vector_cosine_ops)
--     WITH (m = 16, ef_construction = 64);

-- Full-text search index
CREATE INDEX idx_chunks_content_trgm ON chunks USING gin(content gin_trgm_ops);

-- =============================================================================
-- BENCHMARK QUESTIONS TABLE
-- Stores questions from benchmark datasets
-- =============================================================================
CREATE TABLE benchmark_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_id VARCHAR(255) NOT NULL UNIQUE,
    
    -- Question content
    question TEXT NOT NULL,
    answer TEXT,  -- Ground truth answer
    
    -- Question metadata
    dataset_name VARCHAR(100) NOT NULL,  -- hotpotqa, wikimultihopqa, etc.
    question_type VARCHAR(50),  -- bridge, comparison, temporal, etc.
    difficulty VARCHAR(20),  -- easy, medium, hard
    hop_count INTEGER,  -- Number of reasoning hops required
    
    -- Supporting facts (for HotpotQA)
    supporting_facts JSONB,
    
    -- Context passages
    context JSONB,
    
    -- Additional metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_benchmark_questions_dataset ON benchmark_questions(dataset_name);
CREATE INDEX idx_benchmark_questions_type ON benchmark_questions(question_type);
CREATE INDEX idx_benchmark_questions_difficulty ON benchmark_questions(difficulty);
CREATE INDEX idx_benchmark_questions_question_id ON benchmark_questions(question_id);

-- =============================================================================
-- EVALUATIONS TABLE
-- Stores answers from all three RAG variants
-- =============================================================================
CREATE TABLE evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_id VARCHAR(255) NOT NULL,
    
    -- Question and ground truth
    question TEXT NOT NULL,
    ground_truth TEXT,
    
    -- Answers from each RAG variant
    naive_rag_answer TEXT,
    kg_rag_answer TEXT,
    hybrid_rag_answer TEXT,
    
    -- Retrieved context for each variant
    naive_rag_context JSONB,  -- Array of chunk IDs and content
    kg_rag_context JSONB,     -- Graph traversal result
    hybrid_rag_context JSONB, -- Combined context
    
    -- Performance metrics for each variant
    naive_rag_metrics JSONB DEFAULT '{}',
    kg_rag_metrics JSONB DEFAULT '{}',
    hybrid_rag_metrics JSONB DEFAULT '{}',
    
    -- Evaluation metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT fk_question FOREIGN KEY (question_id) 
        REFERENCES benchmark_questions(question_id) ON DELETE CASCADE
);

CREATE INDEX idx_evaluations_question_id ON evaluations(question_id);
CREATE INDEX idx_evaluations_created_at ON evaluations(created_at DESC);

-- =============================================================================
-- SCORES TABLE
-- Stores LLM-based scores for each answer
-- =============================================================================
CREATE TABLE scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_id UUID NOT NULL REFERENCES evaluations(id) ON DELETE CASCADE,
    
    -- RAG variant
    rag_variant VARCHAR(50) NOT NULL CHECK (rag_variant IN ('naive_rag', 'kg_rag', 'hybrid_rag')),
    
    -- Score dimensions (1-10 scale)
    correctness INTEGER CHECK (correctness BETWEEN 1 AND 10),
    completeness INTEGER CHECK (completeness BETWEEN 1 AND 10),
    relevance INTEGER CHECK (relevance BETWEEN 1 AND 10),
    faithfulness INTEGER CHECK (faithfulness BETWEEN 1 AND 10),
    clarity INTEGER CHECK (clarity BETWEEN 1 AND 10),
    
    -- Justifications for each dimension
    correctness_justification TEXT,
    completeness_justification TEXT,
    relevance_justification TEXT,
    faithfulness_justification TEXT,
    clarity_justification TEXT,
    
    -- Overall score (average of dimensions)
    overall_score DECIMAL(3, 1),
    
    -- Scoring metadata
    scorer_model VARCHAR(100),
    scorer_temperature DECIMAL(3, 2),
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_evaluation_variant UNIQUE(evaluation_id, rag_variant)
);

CREATE INDEX idx_scores_evaluation_id ON scores(evaluation_id);
CREATE INDEX idx_scores_rag_variant ON scores(rag_variant);
CREATE INDEX idx_scores_overall_score ON scores(overall_score DESC);
CREATE INDEX idx_scores_created_at ON scores(created_at DESC);

-- Indexes for individual dimensions
CREATE INDEX idx_scores_correctness ON scores(correctness);
CREATE INDEX idx_scores_completeness ON scores(completeness);
CREATE INDEX idx_scores_relevance ON scores(relevance);
CREATE INDEX idx_scores_faithfulness ON scores(faithfulness);
CREATE INDEX idx_scores_clarity ON scores(clarity);

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Function to update document updated_at timestamp
CREATE OR REPLACE FUNCTION update_document_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_document_timestamp
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_document_timestamp();

-- Function to update chunk count in documents
CREATE OR REPLACE FUNCTION update_document_chunk_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE documents 
        SET chunk_count = chunk_count + 1 
        WHERE id = NEW.document_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE documents 
        SET chunk_count = GREATEST(0, chunk_count - 1) 
        WHERE id = OLD.document_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_chunk_count
    AFTER INSERT OR DELETE ON chunks
    FOR EACH ROW
    EXECUTE FUNCTION update_document_chunk_count();

-- Function to calculate overall score
CREATE OR REPLACE FUNCTION calculate_overall_score()
RETURNS TRIGGER AS $$
BEGIN
    NEW.overall_score = (
        COALESCE(NEW.correctness, 0) + 
        COALESCE(NEW.completeness, 0) + 
        COALESCE(NEW.relevance, 0) + 
        COALESCE(NEW.faithfulness, 0) + 
        COALESCE(NEW.clarity, 0)
    )::DECIMAL / 5.0;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_calculate_overall_score
    BEFORE INSERT OR UPDATE ON scores
    FOR EACH ROW
    EXECUTE FUNCTION calculate_overall_score();

-- =============================================================================
-- VIEWS FOR ANALYSIS
-- =============================================================================

-- View for score summary by RAG variant
CREATE OR REPLACE VIEW score_summary AS
SELECT 
    rag_variant,
    COUNT(*) as total_evaluations,
    ROUND(AVG(correctness)::NUMERIC, 2) as avg_correctness,
    ROUND(AVG(completeness)::NUMERIC, 2) as avg_completeness,
    ROUND(AVG(relevance)::NUMERIC, 2) as avg_relevance,
    ROUND(AVG(faithfulness)::NUMERIC, 2) as avg_faithfulness,
    ROUND(AVG(clarity)::NUMERIC, 2) as avg_clarity,
    ROUND(AVG(overall_score)::NUMERIC, 2) as avg_overall_score,
    ROUND(STDDEV(overall_score)::NUMERIC, 2) as std_overall_score
FROM scores
GROUP BY rag_variant;

-- View for document statistics
CREATE OR REPLACE VIEW document_stats AS
SELECT 
    COUNT(*) as total_documents,
    SUM(chunk_count) as total_chunks,
    ROUND(AVG(chunk_count)::NUMERIC, 2) as avg_chunks_per_document,
    ROUND(AVG(character_count)::NUMERIC, 2) as avg_characters,
    ROUND(AVG(word_count)::NUMERIC, 2) as avg_words
FROM documents;

-- View for evaluation statistics
CREATE OR REPLACE VIEW evaluation_stats AS
SELECT 
    COUNT(DISTINCT e.id) as total_evaluations,
    COUNT(DISTINCT e.question_id) as unique_questions,
    COUNT(DISTINCT bq.dataset_name) as datasets_used,
    COUNT(s.id) as total_scores,
    ROUND(AVG(s.overall_score)::NUMERIC, 2) as avg_overall_score
FROM evaluations e
LEFT JOIN benchmark_questions bq ON e.question_id = bq.question_id
LEFT JOIN scores s ON e.id = s.evaluation_id;

-- =============================================================================
-- SAMPLE QUERIES
-- =============================================================================

-- Vector similarity search (example)
-- SELECT id, content, 1 - (embedding <=> '[0.1, 0.2, ...]'::vector) AS similarity
-- FROM chunks
-- ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
-- LIMIT 5;

-- Compare RAG variants
-- SELECT * FROM score_summary;

-- Find best performing questions
-- SELECT 
--     e.question,
--     s.rag_variant,
--     s.overall_score
-- FROM evaluations e
-- JOIN scores s ON e.id = s.evaluation_id
-- ORDER BY s.overall_score DESC
-- LIMIT 10;

-- =============================================================================
-- GRANTS (adjust as needed)
-- =============================================================================

-- Grant permissions to application user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO raguser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO raguser;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO raguser;

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================

-- Log schema creation
DO $$
BEGIN
    RAISE NOTICE 'RAG Benchmarking Schema created successfully!';
    RAISE NOTICE 'Tables: documents, chunks, benchmark_questions, evaluations, scores';
    RAISE NOTICE 'Views: score_summary, document_stats, evaluation_stats';
END $$;
