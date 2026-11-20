import hashlib
import json
import logging
import os
import shutil
import sqlite3
import tempfile
import time
import uuid
from importlib.metadata import version
from pathlib import Path
from typing import Any

from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from transformers import AutoTokenizer

from app.services.data_cleaning import read_records
from app.services.index_store import (
    COLLECTION_NAME,
    EMBEDDING_DIMENSION,
    INDEX_FORMAT,
    MODEL_ID,
    MODEL_REVISION,
    verify_build,
)

MAX_INPUT_TOKENS = 120
TITLE_TOKENS = 20
CHUNK_OVERLAP = 20
logger = logging.getLogger(__name__)


def make_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=MODEL_ID,
        model_kwargs={"device": "cpu", "revision": MODEL_REVISION, "trust_remote_code": False},
        encode_kwargs={"normalize_embeddings": True, "batch_size": 32},
        query_encode_kwargs={"normalize_embeddings": True},
    )


def make_tokenizer() -> Any:
    return AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION, trust_remote_code=False)


def chunks_for_document(record: dict[str, Any], tokenizer: Any) -> list[Document]:
    title = record.get("title") or ""
    text = record.get("text")
    if not isinstance(title, str) or not isinstance(text, str) or not text.strip():
        raise ValueError("Each document must have a string title and non-empty text.")
    if not all(isinstance(record.get(key), str) and record[key] for key in ("url", "source", "type")):
        raise ValueError("Each document must have a source, URL and type.")
    title_ids = tokenizer.encode(title, add_special_tokens=False)
    short_title = tokenizer.decode(title_ids[:TITLE_TOKENS], skip_special_tokens=True).strip()
    prefix = f"{short_title}\n\n" if short_title else ""
    prefix_length = len(tokenizer.encode(prefix, add_special_tokens=True))
    budget = min(100, MAX_INPUT_TOKENS - prefix_length - 5)
    if budget < 1:
        raise ValueError("Document title leaves no room for content.")
    while budget > 0:
        splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ". ", "؟ ", " ", ""],
            chunk_size=budget,
            chunk_overlap=min(CHUNK_OVERLAP, budget - 1),
            length_function=lambda value: len(tokenizer.encode(value, add_special_tokens=False)),
        )
        chunks = splitter.split_text(text)
        if chunks and all(len(tokenizer.encode(prefix + chunk, add_special_tokens=True)) <= MAX_INPUT_TOKENS for chunk in chunks):
            break
        budget -= 1
    else:
        raise ValueError("Could not split document within the embedding token limit.")
    result = []
    for position, chunk in enumerate(chunks):
        content = prefix + chunk
        key = json.dumps([record["source"], record["url"], position, content], ensure_ascii=False)
        metadata = {
            "id": hashlib.sha256(key.encode("utf-8")).hexdigest(),
            "source": record["source"],
            "url": record["url"],
            "title": title,
            "type": record["type"],
            "chunk_index": position,
            "title_shortened_for_embedding": len(title_ids) > TITLE_TOKENS,
        }
        if isinstance(record.get("scraped_at"), str) and record["scraped_at"]:
            metadata["scraped_at"] = record["scraped_at"]
        result.append(Document(page_content=content, metadata=metadata))
    return result


def write_listings(path: Path, listings: list[dict[str, Any]], build_id: str) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE listings (
                url TEXT PRIMARY KEY, property_id TEXT NOT NULL, source TEXT NOT NULL,
                title TEXT NOT NULL, city TEXT, purpose TEXT NOT NULL, property_type TEXT,
                price REAL, currency TEXT, area_sqm REAL, scraped_at TEXT
            );
            CREATE INDEX listings_filters ON listings (city, purpose, property_type, price);
            """
        )
        connection.execute("INSERT INTO metadata VALUES ('build_id', ?)", (build_id,))
        keys = ("url", "property_id", "source", "title", "city", "purpose", "property_type", "price", "currency", "area_sqm", "scraped_at")
        connection.executemany(
            "INSERT INTO listings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [tuple(record.get(key) for key in keys) for record in listings],
        )


def build_index(cleaned_dir: Path, root: Path) -> dict[str, Any]:
    document_file = cleaned_dir / "documents.jsonl"
    listing_file = cleaned_dir / "listings.jsonl"
    records = read_records(document_file)
    listings = read_records(listing_file)
    if not records or not listings:
        raise ValueError("Cleaned documents and listings must both be non-empty.")
    data_hash = hashlib.sha256(document_file.read_bytes() + b"\0" + listing_file.read_bytes()).hexdigest()
    root.mkdir(parents=True, exist_ok=True)
    lock = root / "build.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RuntimeError(f"Another build may be running; inspect {lock} before removing a stale lock.") from exc
    stage: Path | None = None
    published = False
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(str(os.getpid()))
        started = time.monotonic()
        build_id = uuid.uuid4().hex
        build_dir = root / "versions" / build_id
        build_dir.mkdir(parents=True)
        stage = build_dir
        tokenizer = make_tokenizer()
        model = make_embeddings()
        if len(model.embed_query("test")) != EMBEDDING_DIMENSION:
            raise ValueError("Unexpected embedding dimension.")
        documents = [chunk for record in records for chunk in chunks_for_document(record, tokenizer)]
        ids = [doc.metadata["id"] for doc in documents]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate chunk IDs detected.")
        store = Chroma(
            collection_name=COLLECTION_NAME,
            persist_directory=str(build_dir / "chroma"),
            embedding_function=model,
            client_settings=Settings(anonymized_telemetry=False),
            collection_metadata={
                "hnsw:space": "cosine", "model_id": MODEL_ID, "model_revision": MODEL_REVISION,
                "build_id": build_id, "data_sha256": data_hash, "embedding_dimension": EMBEDDING_DIMENSION,
            },
        )
        for start in range(0, len(documents), 64):
            batch = documents[start:start + 64]
            store.add_documents(batch, ids=ids[start:start + 64])
            print(f"Indexed {start + len(batch)}/{len(documents)} chunks", flush=True)
        write_listings(build_dir / "listings.sqlite3", listings, build_id)
        manifest = {
            "build_id": build_id,
            "index_format": INDEX_FORMAT,
            "model_id": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "embedding_dimension": EMBEDDING_DIMENSION,
            "data_sha256": data_hash,
            "document_count": len(records),
            "listing_count": len(listings),
            "chunk_count": len(documents),
            "max_input_tokens": MAX_INPUT_TOKENS,
            "shortened_titles": sum(len(tokenizer.encode(record.get("title") or "", add_special_tokens=False)) > TITLE_TOKENS for record in records),
            "packages": {name: version(name) for name in ("chromadb", "langchain-chroma", "langchain-huggingface", "langchain-text-splitters", "sentence-transformers", "transformers")},
            "build_seconds": round(time.monotonic() - started, 2),
        }
        (build_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        verify_build(build_dir, manifest)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=root, delete=False) as file:
                temporary = Path(file.name)
                json.dump({"build_id": build_id}, file)
                file.write("\n")
            temporary.replace(root / "current.json")
            published = True
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return manifest
    finally:
        if stage is not None and not published:
            try:
                shutil.rmtree(stage)
            except OSError as exc:
                logger.warning("Could not remove incomplete build %s: %s", stage, exc)
        lock.unlink(missing_ok=True)
