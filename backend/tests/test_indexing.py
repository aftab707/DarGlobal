import json
import os
import sqlite3
import subprocess
import sys

import pytest
from langchain_core.embeddings import Embeddings

from app.services import indexing
from app.services.health import get_health
from app.services.index_store import active_build, verify_build


class CharacterTokenizer:
    def encode(self, text, add_special_tokens=False):
        return (["<s>"] + list(text) + ["</s>"]) if add_special_tokens else list(text)

    def decode(self, tokens, skip_special_tokens=True):
        return "".join(tokens)


class FakeEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return [[1.0] + [0.0] * 383 for _ in texts]

    def embed_query(self, text):
        return self.embed_documents([text])[0]


def write_jsonl(path, records):
    path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records), encoding="utf-8")


def test_recursive_chunks_obey_full_token_budget_and_keep_metadata():
    tokenizer = CharacterTokenizer()
    record = {
        "title": "A very long title that must stay complete in metadata",
        "source": "DarGlobal",
        "url": "https://darglobal.co.uk/example",
        "type": "project_detail",
        "text": "Arabic العربية and English. " * 25,
        "scraped_at": None,
    }
    chunks = indexing.chunks_for_document(record, tokenizer)
    assert len(chunks) > 1
    assert all(len(tokenizer.encode(chunk.page_content, add_special_tokens=True)) <= 120 for chunk in chunks)
    assert all(chunk.metadata["title"] == record["title"] for chunk in chunks)
    assert all(chunk.metadata["title_shortened_for_embedding"] for chunk in chunks)
    assert len({chunk.metadata["id"] for chunk in chunks}) == len(chunks)
    assert [chunk.metadata["id"] for chunk in chunks] == [
        chunk.metadata["id"] for chunk in indexing.chunks_for_document(record, tokenizer)
    ]


def test_build_persists_both_indexes_and_failed_rebuild_keeps_previous(tmp_path, monkeypatch):
    cleaned = tmp_path / "cleaned"
    cleaned.mkdir()
    record = {
        "title": "Example", "source": "DarGlobal", "url": "https://darglobal.co.uk/example",
        "type": "general", "text": "Example property information.", "scraped_at": None,
    }
    listing = {
        "url": "https://wasalt.sa/property/sale/villa-1", "property_id": "1",
        "source": "Wasalt", "title": "Villa", "city": "Riyadh", "purpose": "sale",
        "property_type": "villa", "price": None, "currency": None, "area_sqm": 100,
        "scraped_at": None,
    }
    write_jsonl(cleaned / "documents.jsonl", [record])
    write_jsonl(cleaned / "listings.jsonl", [listing])
    monkeypatch.setattr(indexing, "make_tokenizer", CharacterTokenizer)
    monkeypatch.setattr(indexing, "make_embeddings", FakeEmbeddings)
    root = tmp_path / "index"

    manifest = indexing.build_index(cleaned, root)
    path, loaded = active_build(root)
    assert manifest == loaded
    verify_build(path, loaded)
    with sqlite3.connect(path / "listings.sqlite3") as connection:
        assert connection.execute("SELECT price, city FROM listings").fetchone() == (None, "Riyadh")
    monkeypatch.setenv("INDEX_ROOT", str(root))
    assert get_health().index_ready
    result = subprocess.run(
        [sys.executable, "-c", "from app.services.index_store import active_build,verify_build,index_root; p,m=active_build(index_root()); verify_build(p,m); print(m['chunk_count'])"],
        env={**os.environ, "INDEX_ROOT": str(root)}, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(manifest["chunk_count"])

    def fail():
        raise ValueError("simulated failure")

    monkeypatch.setattr(indexing, "make_tokenizer", fail)
    with pytest.raises(ValueError, match="simulated failure"):
        indexing.build_index(cleaned, root)
    assert active_build(root)[1]["build_id"] == manifest["build_id"]
    assert not (root / "build.lock").exists()
    assert [item.name for item in (root / "versions").iterdir()] == [manifest["build_id"]]


def test_existing_build_lock_is_not_removed(tmp_path):
    cleaned = tmp_path / "cleaned"
    cleaned.mkdir()
    write_jsonl(cleaned / "documents.jsonl", [{"text": "example"}])
    write_jsonl(cleaned / "listings.jsonl", [{"url": "example"}])
    root = tmp_path / "index"
    root.mkdir()
    (root / "build.lock").write_text("another process", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Another build may be running"):
        indexing.build_index(cleaned, root)
    assert (root / "build.lock").read_text(encoding="utf-8") == "another process"


def test_health_reports_incompatible_index(monkeypatch, tmp_path):
    monkeypatch.setenv("INDEX_ROOT", str(tmp_path))
    (tmp_path / "current.json").write_text('{"build_id":"../bad"}', encoding="utf-8")
    result = get_health()
    assert result.status == "not_ready"
    assert not result.index_ready
