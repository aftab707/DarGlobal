import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
EMBEDDING_DIMENSION = 384
COLLECTION_NAME = "real_estate"
INDEX_FORMAT = 1
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def index_root() -> Path:
    return Path(os.environ.get("INDEX_ROOT", PROJECT_ROOT / "data" / "index"))


def active_build(root: Path) -> tuple[Path, dict[str, Any]]:
    pointer = json.loads((root / "current.json").read_text(encoding="utf-8"))
    build_id = pointer["build_id"]
    if not isinstance(build_id, str) or not re.fullmatch(r"[a-f0-9]{32}", build_id):
        raise ValueError("Invalid index build identifier.")
    path = root / "versions" / build_id
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    if (
        manifest.get("build_id") != build_id
        or manifest.get("index_format") != INDEX_FORMAT
        or manifest.get("model_id") != MODEL_ID
        or manifest.get("model_revision") != MODEL_REVISION
        or manifest.get("embedding_dimension") != EMBEDDING_DIMENSION
    ):
        raise ValueError("Index manifest is incompatible with the configured embedding model.")
    return path, manifest


def verify_build(path: Path, manifest: dict[str, Any]) -> None:
    chroma_dir = path / "chroma"
    chroma_file = chroma_dir / "chroma.sqlite3"
    listing_file = path / "listings.sqlite3"
    if not chroma_file.is_file() or not listing_file.is_file():
        raise ValueError("Index files are missing.")
    with sqlite3.connect(f"{listing_file.resolve().as_uri()}?mode=ro", uri=True) as connection:
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("Listing database integrity check failed.")
        count = connection.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
        build_id = connection.execute("SELECT value FROM metadata WHERE key = 'build_id'").fetchone()
        if count != manifest["listing_count"] or not build_id or build_id[0] != manifest["build_id"]:
            raise ValueError("Listing database does not match the index manifest.")
    client = chromadb.PersistentClient(path=str(chroma_dir), settings=Settings(anonymized_telemetry=False))
    collection = client.get_collection(COLLECTION_NAME)
    if collection.count() != manifest["chunk_count"] or manifest["chunk_count"] <= 0:
        raise ValueError("Chroma collection does not match the index manifest.")
    metadata = collection.metadata or {}
    if any(metadata.get(key) != manifest[key] for key in ("build_id", "data_sha256", "model_id", "model_revision", "embedding_dimension")):
        raise ValueError("Chroma collection metadata does not match the index manifest.")
    sample = collection.get(limit=1, include=["embeddings"])
    if sample["embeddings"] is None or len(sample["embeddings"][0]) != EMBEDDING_DIMENSION:
        raise ValueError("Chroma collection has an unexpected embedding dimension.")
