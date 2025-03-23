--Full text search column
ALTER TABLE @cdmDatabaseSchema.concept
  ADD COLUMN concept_name_tsv tsvector
  GENERATED ALWAYS AS (to_tsvector('english', concept_name)) STORED;
--Full text search index
CREATE INDEX idx_concept_fts ON @cdmDatabaseSchema.concept USING GIN (concept_fts);

