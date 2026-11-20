import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.data_cleaning import SOURCES, prepare_data, write_outputs


def main() -> int:
    project = BACKEND.parent
    parser = argparse.ArgumentParser(description="Clean the existing DarGlobal and Wasalt JSONL data.")
    parser.add_argument("--input-root", type=Path, default=project.parent)
    parser.add_argument("--output-dir", type=Path, default=project / "data" / "cleaned")
    args = parser.parse_args()
    try:
        inputs = {(args.input_root / source.path).resolve() for source in SOURCES}
        outputs = {(args.output_dir / name).resolve() for name in ("documents.jsonl", "listings.jsonl", "audit_report.json")}
        if inputs & outputs:
            raise ValueError("Output files must not overwrite source data.")
        documents, listings, report = prepare_data(args.input_root)
        write_outputs(args.output_dir, documents, listings, report)
    except (OSError, ValueError) as exc:
        print(f"Data cleaning failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report["output"], sort_keys=True))
    print(f"Cleaned files and audit report: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
