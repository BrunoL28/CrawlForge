-- ═══════════════════════════════════════════════════════
-- CrawlForge — Initial Schema Migration
-- Creates core tables for documents and embeddings
-- ═══════════════════════════════════════════════════════

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ── Documents table ─────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url         TEXT NOT NULL,
    url_hash    TEXT NOT NULL,
    title       TEXT,
    content     TEXT,
    raw_html    TEXT,
    metadata    JSONB DEFAULT '{}',
    links       JSONB DEFAULT '{}',
    media       JSONB DEFAULT '{}',
    status_code INTEGER,
    session_id  TEXT,
    crawled_at  TIMESTAMPTZ DEFAULT NOW(),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_url_hash ON documents (url_hash);
CREATE INDEX IF NOT EXISTS idx_documents_session_id ON documents (session_id);
CREATE INDEX IF NOT EXISTS idx_documents_crawled_at ON documents (crawled_at DESC);

-- ── Embeddings table ────────────────────────────────
CREATE TABLE IF NOT EXISTS embeddings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL DEFAULT 0,
    chunk_text  TEXT NOT NULL,
    embedding   vector(1536),          -- text-embedding-3-small dimension
    model       TEXT NOT NULL DEFAULT 'text-embedding-3-small',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_document_id ON embeddings (document_id);

-- HNSW index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
