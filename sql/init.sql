CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS repositories (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    path        TEXT NOT NULL,
    indexed_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS repository_languages (
    repo_id     TEXT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    language    TEXT NOT NULL,
    PRIMARY KEY (repo_id, language)
);

CREATE TABLE IF NOT EXISTS code_nodes (
    id              TEXT PRIMARY KEY,
    repo_id         TEXT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    type            TEXT NOT NULL,
    language        TEXT,
    path            TEXT,
    qualified_name  TEXT NOT NULL,
    start_line      INT,
    end_line        INT,
    start_byte      INT,
    end_byte        INT,
    raw_source      TEXT,
    summary         TEXT,
    attributes      JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS code_edges (
    id          TEXT PRIMARY KEY,
    source_id   TEXT NOT NULL REFERENCES code_nodes(id) ON DELETE CASCADE,
    target_id   TEXT REFERENCES code_nodes(id) ON DELETE SET NULL,
    target_ref  TEXT,
    type        TEXT NOT NULL,
    attributes  JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS code_embeddings (
    id          BIGSERIAL PRIMARY KEY,
    node_id     TEXT NOT NULL REFERENCES code_nodes(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL DEFAULT 0,
    chunk_text  TEXT NOT NULL,
    embedding   VECTOR(768),
    UNIQUE (node_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    focus_node_id   TEXT REFERENCES code_nodes(id) ON DELETE SET NULL,
    active_node_ids TEXT[] NOT NULL DEFAULT '{}',
    last_query_type TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL
);

-- indexes
CREATE INDEX IF NOT EXISTS ix_nodes_repo_path
    ON code_nodes (repo_id, path);

CREATE INDEX IF NOT EXISTS ix_nodes_name_trgm
    ON code_nodes USING gin (name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS ix_edges_source_id
    ON code_edges (source_id);

CREATE INDEX IF NOT EXISTS ix_edges_target_id
    ON code_edges (target_id);

CREATE INDEX IF NOT EXISTS ix_edges_source_type
    ON code_edges (source_id, type);

CREATE INDEX IF NOT EXISTS ix_edges_target_ref_trgm
    ON code_edges USING gin (target_ref gin_trgm_ops);

CREATE INDEX IF NOT EXISTS ix_embeddings_node_id
    ON code_embeddings (node_id);

CREATE INDEX IF NOT EXISTS ix_embeddings_vector
    ON code_embeddings USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS ix_sessions_expires_at
    ON sessions (expires_at);