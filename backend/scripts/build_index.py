import argparse
import json
import os
import sys
from pathlib import Path

os.environ["LANGSMITH_TRACING"] = "false"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.index_store import PROJECT_ROOT, index_root
from app.services.indexing import build_index


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a local Chroma index and listing database.")
    parser.add_argument("--cleaned-dir", type=Path, default=PROJECT_ROOT / "data" / "cleaned")
    parser.add_argument("--index-root", type=Path, default=index_root())
    args = parser.parse_args()
    try:
        manifest = build_index(args.cleaned_dir, args.index_root)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Index build failed: {exc}. Existing active index was not replaced.", file=sys.stderr)
        return 1
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
