CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    doc_id        TEXT PRIMARY KEY,
    doc_type      TEXT NOT NULL,          -- invoice | contract | receipt | statement
    mst           TEXT,                   -- MST người bán
    buyer_mst     TEXT,
    issue_date    DATE,
    invoice_no    TEXT,
    source_path   TEXT,
    content_hash  TEXT NOT NULL,
    n_chunks      INT DEFAULT 0,
    indexed_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id            BIGSERIAL PRIMARY KEY,
    doc_id        TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    chunk_index   INT  NOT NULL,
    text          TEXT NOT NULL,
    n_chars       INT,
    embedding     vector(1024),
    doc_type      TEXT,
    mst           TEXT,
    issue_date    DATE,
    invoice_no    TEXT,
    UNIQUE (doc_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS chunks_mst_idx        ON chunks (mst);
CREATE INDEX IF NOT EXISTS chunks_doc_type_idx   ON chunks (doc_type);
CREATE INDEX IF NOT EXISTS chunks_issue_date_idx ON chunks (issue_date);
CREATE INDEX IF NOT EXISTS chunks_invoice_no_idx ON chunks (invoice_no);
