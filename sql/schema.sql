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
    document_id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    source_path VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    ingestion_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes
    CONSTRAINT unique_source_path UNIQUE(source_path)
);

CREATE INDEX idx_documents_title ON documents(title);
CREATE INDEX idx_documents_source_path ON documents(source_path);
CREATE INDEX idx_documents_ingestion_date ON documents(ingestion_date DESC);
CREATE INDEX idx_documents_metadata ON documents USING gin(metadata);

-- =============================================================================
-- CHUNKS TABLE
-- Stores document chunks with vector embeddings
-- =============================================================================
CREATE TABLE chunks (
    chunk_id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    
    -- Content
    chunk_text TEXT NOT NULL,
    embedding vector(768),  -- 768 for text-embedding-004
    
    -- Chunk metadata
    chunk_index INTEGER NOT NULL,
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
CREATE INDEX idx_chunks_embedding ON chunks 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);

-- Full-text search index
CREATE INDEX idx_chunks_content_trgm ON chunks USING gin(chunk_text gin_trgm_ops);

-- =============================================================================
-- BENCHMARK QUESTIONS TABLE (OPTIONAL - evaluation now uses JSON files)
-- Stores questions from benchmark datasets
-- NOTE: The evaluation pipeline now loads questions from JSON files in 
--       benchmarks/datasets/ and saves results locally instead of using the database.
--       These tables are kept for backwards compatibility and optional database storage.
-- =============================================================================
CREATE TABLE benchmark_questions (
    id SERIAL PRIMARY KEY,
    dataset_name VARCHAR(100) NOT NULL,
    question_id VARCHAR(255) NOT NULL,
    question_text TEXT NOT NULL,
    ground_truth TEXT,
    context TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Unique constraint on dataset_name + question_id
    CONSTRAINT unique_dataset_question UNIQUE(dataset_name, question_id)
);

CREATE INDEX idx_benchmark_questions_dataset ON benchmark_questions(dataset_name);
CREATE INDEX idx_benchmark_questions_question_id ON benchmark_questions(question_id);

-- =============================================================================
-- EVALUATIONS TABLE (OPTIONAL - results now saved to JSON files)
-- Stores answers from all three RAG variants
-- NOTE: Evaluation results are now saved to local JSON files in 
--       benchmarks/results/ with format: eval_{timestamp}_{benchmark}.json
-- =============================================================================
CREATE TABLE evaluations (
    evaluation_id SERIAL PRIMARY KEY,
    rag_variant VARCHAR(50) NOT NULL,
    question_id INTEGER NOT NULL,
    generated_answer TEXT,
    retrieved_chunks INTEGER[],
    latency_ms FLOAT,
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_evaluations_question_id ON evaluations(question_id);
CREATE INDEX idx_evaluations_rag_variant ON evaluations(rag_variant);
CREATE INDEX idx_evaluations_timestamp ON evaluations(timestamp DESC);

-- =============================================================================
-- SCORES TABLE (OPTIONAL - results now saved to JSON files)
-- Stores LLM-based scores for each answer
-- =============================================================================
CREATE TABLE scores (
    score_id SERIAL PRIMARY KEY,
    evaluation_id INTEGER NOT NULL REFERENCES evaluations(evaluation_id) ON DELETE CASCADE,
    
    -- Score dimensions (0-10 scale)
    correctness FLOAT CHECK (correctness >= 0 AND correctness <= 10),
    completeness FLOAT CHECK (completeness >= 0 AND completeness <= 10),
    relevance FLOAT CHECK (relevance >= 0 AND relevance <= 10),
    faithfulness FLOAT CHECK (faithfulness >= 0 AND faithfulness <= 10),
    clarity FLOAT CHECK (clarity >= 0 AND clarity <= 10),
    
    -- Explanation metadata
    explanation JSONB DEFAULT '{}',
    
    -- Overall score (average of dimensions)
    overall_score FLOAT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_scores_evaluation_id ON scores(evaluation_id);
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

-- View for RAG variant performance comparison
CREATE OR REPLACE VIEW score_summary AS
SELECT 
    e.rag_variant,
    COUNT(*) as evaluation_count,
    ROUND(AVG(s.correctness)::NUMERIC, 2) as avg_correctness,
    ROUND(AVG(s.completeness)::NUMERIC, 2) as avg_completeness,
    ROUND(AVG(s.relevance)::NUMERIC, 2) as avg_relevance,
    ROUND(AVG(s.faithfulness)::NUMERIC, 2) as avg_faithfulness,
    ROUND(AVG(s.clarity)::NUMERIC, 2) as avg_clarity,
    ROUND(AVG(s.overall_score)::NUMERIC, 2) as avg_overall_score,
    ROUND(STDDEV(s.overall_score)::NUMERIC, 2) as std_overall_score
FROM evaluations e
LEFT JOIN scores s ON e.evaluation_id = s.evaluation_id
GROUP BY e.rag_variant;

-- View for document statistics
CREATE OR REPLACE VIEW document_stats AS
SELECT 
    COUNT(*) as total_documents,
    (SELECT COUNT(*) FROM chunks) as total_chunks,
    ROUND((SELECT COUNT(*) FROM chunks)::NUMERIC / NULLIF(COUNT(*), 0), 2) as avg_chunks_per_document
FROM documents;

-- View for evaluation statistics
CREATE OR REPLACE VIEW evaluation_stats AS
SELECT 
    COUNT(DISTINCT e.evaluation_id) as total_evaluations,
    COUNT(DISTINCT e.question_id) as unique_questions,
    COUNT(DISTINCT e.rag_variant) as variants_tested,
    COUNT(s.score_id) as total_scores,
    ROUND(AVG(s.overall_score)::NUMERIC, 2) as avg_overall_score
FROM evaluations e
LEFT JOIN scores s ON e.evaluation_id = s.evaluation_id;

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
