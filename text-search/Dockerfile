FROM python:3.13-bookworm

RUN pip install --no-cache psycopg pgvector polars tqdm pyarrow

COPY load_text_search.py /load_text_search.py

ENTRYPOINT ["python", "load_text_search.py"]
