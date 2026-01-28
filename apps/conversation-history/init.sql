-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create tables (will also be created by SQLAlchemy)
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_path TEXT UNIQUE NOT NULL,
    project_name VARCHAR(200) NOT NULL,
    feature_name VARCHAR(200),
    doc_type VARCHAR(50) NOT NULL,
    title VARCHAR(500),
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    embedding vector(1536),
    indexed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversation_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536)
);

CREATE TABLE IF NOT EXISTS index_status (
    id SERIAL PRIMARY KEY,
    project_name VARCHAR(200),
    last_index_at TIMESTAMP WITH TIME ZONE,
    files_indexed INTEGER DEFAULT 0,
    files_updated INTEGER DEFAULT 0,
    files_failed INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'idle',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_conversations_project_name ON conversations(project_name);
CREATE INDEX IF NOT EXISTS ix_conversations_doc_type ON conversations(doc_type);
CREATE INDEX IF NOT EXISTS ix_conversations_feature_name ON conversations(feature_name);
CREATE INDEX IF NOT EXISTS ix_conversations_content_hash ON conversations(content_hash);
CREATE INDEX IF NOT EXISTS ix_chunks_conversation_id ON conversation_chunks(conversation_id);

-- Create vector index for similarity search (IVFFlat)
-- Note: Run this after loading some data for better performance
-- CREATE INDEX IF NOT EXISTS ix_conversations_embedding ON conversations
--   USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
