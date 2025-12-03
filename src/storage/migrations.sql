-- Initial Schema

CREATE TABLE IF NOT EXISTS source_documents (
    id UUID PRIMARY KEY,
    url TEXT,
    source_domain TEXT NOT NULL,
    reliability_score FLOAT NOT NULL,
    ingested_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
    raw_content_hash TEXT
);

CREATE TABLE IF NOT EXISTS claims_audit (
    id UUID PRIMARY KEY,
    source_id UUID NOT NULL,
    subject_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    object_id TEXT NOT NULL,
    confidence_score FLOAT NOT NULL,
    extraction_model TEXT NOT NULL,
    extracted_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

CREATE INDEX IF NOT EXISTS idx_claims_source ON claims_audit(source_id);
CREATE INDEX IF NOT EXISTS idx_claims_subject ON claims_audit(subject_id);
