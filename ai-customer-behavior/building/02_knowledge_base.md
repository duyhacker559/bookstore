# 02 - Build Knowledge Base for Consulting

## Objective

Build a Knowledge Base (KB) that supports product consulting and policy Q&A with grounded answers.

## Knowledge sources

1. Internal structured sources
- product catalog (books + clothing)
- inventory and pricing
- shipping options and delivery SLA
- payment and refund policy

2. Internal unstructured sources
- FAQ markdown and docs
- customer support playbooks
- campaign and promotion docs

3. Optional external sources
- publisher descriptions
- size guides for clothing

## KB data model

Each document chunk must contain:
- chunk_id
- source_type
- source_ref
- title
- content
- language
- category
- tags
- updated_at
- validity_start, validity_end

## Processing pipeline

1. Ingestion
- pull from DB exports and markdown files
- keep source version hash

2. Cleaning
- remove html noise
- normalize units and currency

3. Chunking
- 300 to 600 tokens per chunk
- overlap 50 to 80 tokens

4. Embedding
- create vector embedding for each chunk
- store in vector database

5. Indexing
- vector index for semantic search
- metadata index for category and policy filters

## Recommended storage

Option A (quick): PostgreSQL + pgvector
Option B (scalable): Qdrant

## Update strategy

- nightly batch refresh for stable docs
- near real-time update for price, stock, promotion
- soft delete outdated chunks, keep lineage

## Quality checks

- duplicate chunk ratio
- broken source references
- stale document ratio
- retrieval precision on golden questions

## Security and governance

- redact sensitive customer data before indexing
- role-based access for admin ingestion APIs
- audit logs for ingestion and deletion

## Integration endpoints

Create KB APIs under rag-service:
- POST /api/v1/kb/ingest
- GET /api/v1/kb/search
- GET /api/v1/kb/document/{id}
- POST /api/v1/kb/reindex

## Acceptance criteria

- At least 95% FAQ questions have relevant retrieved chunks in Top-5
- All answers can reference source chunks
- KB refresh job runs successfully each day
