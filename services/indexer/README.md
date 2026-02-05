# Indexer Service (Phase 2-3)

## Embedding backends
- `hash` (default): no external model, deterministic.
- `sentence-transformers`: requires installing `sentence-transformers` and model download.

Set with env:
- `RAG_EMBEDDING_BACKEND=hash|sentence-transformers`
- `RAG_EMBEDDING_DIM=384`

## Qdrant/OpenSearch
- Qdrant collection: `RAG_QDRANT_COLLECTION` (default `rag_chunks`)
- OpenSearch index: `RAG_OPENSEARCH_INDEX` (default `rag_chunks`)
