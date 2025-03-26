--Full text search index
CREATE INDEX idx_concept_fts ON @cdmDatabaseSchema.concept USING GIN (concept_name_tsv);
