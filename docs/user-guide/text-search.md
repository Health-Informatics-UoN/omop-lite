# Text Search

OMOP Lite supports both full-text search and vector search capabilities to enhance query performance and enable semantic search on your OMOP CDM data.

## Full-Text Search

Full-text search adds a `tsvector` column to the concept table and creates an index on that column, making text-based queries on the concept table run much faster.

### Enabling Full-Text Search

Set the `FTS_CREATE` environment variable or use the `--fts-create` flag:

```bash
# Using command line flag
omop-lite --fts-create --synthetic

# Using environment variable
export FTS_CREATE=true
omop-lite --synthetic
```

### How It Works

When full-text search is enabled, OMOP Lite:

1. Adds a `tsvector` column to the `concept` table
2. Populates the column with searchable text from concept names and synonyms
3. Creates a GIN index on the `tsvector` column for fast searching
4. Enables PostgreSQL's full-text search capabilities

### Usage Examples

Once enabled, you can perform fast text searches:

```sql
-- Search for concepts containing "diabetes"
SELECT concept_name, concept_id 
FROM concept 
WHERE to_tsvector('english', concept_name) @@ plainto_tsquery('english', 'diabetes');

-- Search with ranking
SELECT concept_name, concept_id, ts_rank(to_tsvector('english', concept_name), plainto_tsquery('english', 'diabetes')) as rank
FROM concept 
WHERE to_tsvector('english', concept_name) @@ plainto_tsquery('english', 'diabetes')
ORDER BY rank DESC;

-- Search in concept synonyms
SELECT c.concept_name, c.concept_id, cs.concept_synonym_name
FROM concept c
JOIN concept_synonym cs ON c.concept_id = cs.concept_id
WHERE to_tsvector('english', cs.concept_synonym_name) @@ plainto_tsquery('english', 'heart attack');
```

## Vector Search

Vector search uses embeddings to enable semantic search on concepts. This feature requires the `compose-omop-ts.yml` Docker Compose file and embedding data.

### Prerequisites

1. **Embeddings File**: You need `embeddings/embeddings.parquet` containing concept IDs and their embeddings
2. **pgvector Extension**: The database must have the pgvector extension installed

### Setup with Docker Compose

Use the provided Docker Compose file for vector search:

```bash
# Clone the repository if you haven't already
git clone https://github.com/Health-Informatics-UoN/omop-lite.git
cd omop-lite

# Run with vector search support
docker compose -f compose-omop-ts.yml up
```

### Manual Setup

If you want to set up vector search manually:

1. **Install pgvector** in your PostgreSQL database:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

2. **Create embeddings table**:
   ```sql
   CREATE TABLE embeddings (
       concept_id BIGINT PRIMARY KEY,
       embedding vector(384)  -- Adjust dimension as needed
   );
   ```

3. **Load embeddings** from your parquet file

### Usage Examples

Once vector search is set up:

```sql
-- Find similar concepts using cosine similarity
SELECT c.concept_name, e.embedding <=> (SELECT embedding FROM embeddings WHERE concept_id = 201820) as distance
FROM concept c
JOIN embeddings e ON c.concept_id = e.concept_id
WHERE e.concept_id != 201820
ORDER BY distance
LIMIT 10;

-- Semantic search for concepts
SELECT c.concept_name, e.embedding <=> '[0.1, 0.2, ...]'::vector as distance
FROM concept c
JOIN embeddings e ON c.concept_id = e.concept_id
ORDER BY distance
LIMIT 10;
```

## Combined Search

You can combine full-text and vector search for powerful querying:

```sql
-- Combine text search with vector similarity
WITH text_results AS (
    SELECT concept_id, concept_name
    FROM concept 
    WHERE to_tsvector('english', concept_name) @@ plainto_tsquery('english', 'diabetes')
),
vector_results AS (
    SELECT c.concept_id, c.concept_name, e.embedding <=> '[0.1, 0.2, ...]'::vector as distance
    FROM concept c
    JOIN embeddings e ON c.concept_id = e.concept_id
    ORDER BY distance
    LIMIT 20
)
SELECT 
    COALESCE(t.concept_id, v.concept_id) as concept_id,
    COALESCE(t.concept_name, v.concept_name) as concept_name,
    v.distance
FROM text_results t
FULL OUTER JOIN vector_results v ON t.concept_id = v.concept_id
ORDER BY v.distance NULLS LAST;
```

## Performance Considerations

### Full-Text Search
- **Index Size**: The GIN index adds storage overhead but significantly improves query performance
- **Query Optimization**: Use appropriate text search functions for best performance
- **Language Support**: Configure language-specific stemming and stop words

### Vector Search
- **Index Type**: Use HNSW or IVFFlat indexes for better performance on large datasets
- **Dimension**: Optimize vector dimensions for your use case
- **Memory**: Vector operations can be memory-intensive

### Indexing Strategies

```sql
-- Create optimized indexes for vector search
CREATE INDEX ON embeddings USING hnsw (embedding vector_cosine_ops);

-- Create composite indexes for combined queries
CREATE INDEX ON concept (concept_id) WHERE to_tsvector('english', concept_name) IS NOT NULL;
```

## Troubleshooting

### Full-Text Search Issues

1. **Index Not Created**: Check that `FTS_CREATE` is set correctly
2. **Slow Queries**: Ensure the GIN index is being used (check query plan)
3. **No Results**: Verify text search configuration and language settings

### Vector Search Issues

1. **Extension Not Found**: Install pgvector extension
2. **Dimension Mismatch**: Ensure embedding dimensions match table definition
3. **Memory Errors**: Reduce batch size or optimize vector operations

### Common Solutions

```sql
-- Check if full-text search is enabled
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'concept' AND column_name = 'tsvector';

-- Check pgvector extension
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Analyze table statistics
ANALYZE concept;
ANALYZE embeddings;
```

## Best Practices

1. **Use Appropriate Indexes**: Create indexes based on your query patterns
2. **Optimize Embeddings**: Use appropriate vector dimensions and similarity metrics
3. **Monitor Performance**: Track query performance and optimize as needed
4. **Backup Strategy**: Include vector data in your backup strategy
5. **Security**: Ensure proper access controls for search functionality

## Next Steps

- **[CLI Reference](cli-reference.md)** - Learn all available commands
- **[Synthetic Data](synthetic-data.md)** - Set up test data for search
- **[Configuration](../getting-started/configuration.md)** - Configure search options 