--Full text search column
ALTER TABLE @cdmDatabaseSchema.concept
  ADD COLUMN concept_name_tsv tsvector
  GENERATED ALWAYS AS (to_tsvector('english', concept_name)) STORED;
