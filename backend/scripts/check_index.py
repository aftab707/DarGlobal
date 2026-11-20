import os
import sys
from pathlib import Path

os.environ["LANGSMITH_TRACING"] = "false"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from chromadb.config import Settings
from langchain_chroma import Chroma

from app.services.index_store import COLLECTION_NAME, active_build, index_root, verify_build
from app.services.indexing import make_embeddings


def main() -> int:
    path, manifest = active_build(index_root())
    verify_build(path, manifest)
    store = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=str(path / "chroma"),
        embedding_function=make_embeddings(),
        client_settings=Settings(anonymized_telemetry=False),
        create_collection_if_not_exists=False,
    )
    cases = [
        ("DarGlobal AIDA 360", "What services does the AIDA 360 concierge provide?", None, "https://darglobal.co.uk/aida-360"),
        ("Wasalt company", "What is Wasalt and how can I buy or rent a property?", {"type": "company"}, "https://wasalt.sa/en"),
        ("Arabic listing", "فيلا 450 متر مربع جنوبية على شارع 18م الرمال الرياض", {"type": "listing_detail"}, "5971799"),
        ("English to Arabic listing", "south facing 450 sqm villa for sale on 18m road in Al Rimal Riyadh", {"type": "listing_detail"}, "5971799"),
    ]
    failed = False
    for label, query, metadata_filter, expected in cases:
        results = store.similarity_search_with_score(query, k=10, filter=metadata_filter)
        hit = any(
            doc.metadata["url"] == expected if expected.startswith("https://") else expected in doc.metadata["url"]
            for doc, _ in results
        )
        print(f"{label}: {'PASS' if hit else 'FAIL'} (expected source within top {len(results)})")
        failed |= not hit
    unrelated = store.similarity_search_with_score("How do I fix a bicycle tire?", k=1)
    print(f"Unrelated-query nearest cosine distance: {unrelated[0][1]:.4f}; no abstention threshold is configured yet.")
    print(f"Verified persistent index: {manifest['chunk_count']} chunks, {manifest['listing_count']} listings.")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
