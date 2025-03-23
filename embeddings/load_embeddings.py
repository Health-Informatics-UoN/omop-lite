from os import getenv
import pyarrow.parquet as pq
import polars as pl
from pgvector.psycopg import register_vector
import psycopg

uri = f"postgresql://{getenv('DB_USER')}:{getenv('DB_PASSWORD')}@{getenv('DB_HOST')}:{getenv('DB_PORT')}/{getenv('DB_NAME')}"

vector_length = (
    pl.scan_parquet("embeddings/embeddings.parquet")
    .first()
    .collect()
    .get_column("embeddings")[0]
    .shape[0]
)

conn = psycopg.connect(uri)
print("Connected to database\n")
register_vector(conn)
print("Registered vector type")
cursor = conn.cursor()

# This drops the table, then creates a new one to fill with embeddings,
# so it should only be run when you're building the database for the first time
# or if you want to replace your embeddings
# if we want to load multiple embeddings datasets, we can make the table name configurable from the environment

print("Loading pgvector extension")
cursor.execute(
    """
        CREATE EXTENSION vector;
        """
)

cursor.execute(
    """
        DROP TABLE IF EXISTS cdm.embeddings;
        """
)
print(f"Creating a table for {vector_length} dimensional vectors")
cursor.execute(
    f"""
        CREATE TABLE cdm.embeddings (
            concept_id  int
            embeddings  vector({vector_length})
        );
        """
)

conn.commit()

# Open the Parquet file in streaming mode
parquet_file = pq.ParquetFile("embeddings/embeddings.parquet")

# Each row will occupy 8514-ish bytes at the end
# To keep the memory usage below 4 Gb, setting the batch size to 200_000
print("Copying in vectors")
for batch in parquet_file.iter_batches(batch_size=200000):
    with cursor.copy(
        "COPY cdm.embeddings (concept_id, embedding) FROM STDIN WITH (FORMAT BINARY)"
    ) as copy:
        # use set_types for binary copy
        # https://www.psycopg.org/psycopg3/docs/basic/copy.html#binary-copy
        copy.set_types(["int4", "vector"])

        for entry in zip(batch[0], batch[2]):
            copy.write_row((entry[0].as_py(), entry[1].as_py()))
print("Vectors in!")
