FROM python:3.13-bookworm

RUN pip install --no-cache psycopg pgvector polars tqdm pyarrow

COPY load_embeddings.py /load_embeddings.py

ENTRYPOINT ["python", "load_embeddings.py"]
