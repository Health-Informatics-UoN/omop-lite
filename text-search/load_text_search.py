from os import getenv
import pyarrow.parquet as pq
import polars as pl
from pgvector.psycopg import register_vector
import psycopg

uri = f"postgresql://{getenv('DB_USER')}:{getenv('DB_PASSWORD')}@{getenv('DB_HOST')}:{getenv('DB_PORT')}/{getenv('DB_NAME')}"

SCHEMA_NAME = getenv("SCHEMA_NAME")

try:
    vector_length = (
        pl.scan_parquet("/text-search/embeddings.parquet")
        .first()
        .collect()
        .get_column("embeddings")[0]
        .shape[0]
    )
except FileNotFoundError as e:
    print(f"Embeddings file missing: {e}")

with psycopg.connect(uri) as conn:
    print("Connected to database\n")
    print("Materialising text-search column")
    conn.execute(
            f"""ALTER TABLE {SCHEMA_NAME}.concept
                ADD COLUMN concept_name_tsv tsvector
                GENERATED ALWAYS AS (to_tsvector('english', concept_name)) STORED;"""
            )
    print("Creating text-search index")
    conn.execute(f"CREATE INDEX idx_concept_fts ON {SCHEMA_NAME}.concept USING GIN (concept_name_tsv);")

with psycopg.connect(uri) as conn:
    print("Connected to database\n")
    print("Loading pgvector extension")
    conn.execute("""
                 CREATE EXTENSION vector;
                 """)
    register_vector(conn)
    print("Registered vector type")
    with conn.cursor() as cursor:
        # This drops the table, then creates a new one to fill with embeddings,
        # so it should only be run when you're building the database for the first time
        # or if you want to replace your embeddings
        # if we want to load multiple embeddings datasets, we can make the table name configurable from the environment

        cursor.execute(
            f"""
                DROP TABLE IF EXISTS {SCHEMA_NAME}.embeddings;
                """
        )
        print(f"Creating a table for {vector_length} dimensional vectors")
        cursor.execute(
            f"""
                CREATE TABLE {SCHEMA_NAME}.embeddings (
                    concept_id  int,
                    embedding  vector({vector_length})
                );
                """
        )

        # Open the Parquet file in streaming mode
        parquet_file = pq.ParquetFile("text-search/embeddings.parquet")

        # Each row will occupy 8514-ish bytes at the end
        # To keep the memory usage below 4 Gb, setting the batch size to 200_000
        print("Copying in vectors")
        for batch in parquet_file.iter_batches(batch_size=200000):
            with cursor.copy(
                f"COPY {SCHEMA_NAME}.embeddings (concept_id, embedding) FROM STDIN WITH (FORMAT BINARY)"
            ) as copy:
                # use set_types for binary copy
                # https://www.psycopg.org/psycopg3/docs/basic/copy.html#binary-copy
                copy.set_types(["int4", "vector"])

                for entry in zip(batch[0], batch[2]):
                    copy.write_row((entry[0].as_py(), entry[1].as_py()))
        print("Vectors in!")
    conn.commit()
