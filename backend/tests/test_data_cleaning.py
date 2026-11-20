import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.services.data_cleaning import (
    SOURCES,
    canonical_url,
    clean_text,
    parse_area,
    parse_price,
    prepare_data,
    read_records,
    write_outputs,
)


def write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


@pytest.fixture
def source_root(tmp_path: Path) -> Path:
    for source in SOURCES:
        write_rows(tmp_path / source.path, [])
    return tmp_path


def test_url_normalization_preserves_meaningful_query_and_rejects_untrusted_hosts():
    assert canonical_url("https://wasalt.sa/property/sale/فيلا-100-123?utm_source=x&type=home#part", "Wasalt") == (
        "https://wasalt.sa/property/sale/%D9%81%D9%8A%D9%84%D8%A7-100-123?type=home"
    )
    assert canonical_url("https://wasalt.sa.evil.example/property/sale/villa-123", "Wasalt") is None
    assert canonical_url("https://wasalt.sa/property/sale/%XX-123", "Wasalt") is None


def test_text_cleanup_removes_contacts_and_preserves_information():
    assert clean_text("Amenity\nPool\nPool\nEmail: test@example.com\nCall +966 50 123 4567") == (
        "Amenity\nPool\nEmail: [contact removed]\nCall [number removed]"
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("SAR 1,200,000", (1200000.0, "SAR")),
        ("1200000", (None, None)),
        ("1,20 SAR", (None, None)),
        (None, (None, None)),
    ],
)
def test_price_requires_explicit_currency_and_unambiguous_amount(value, expected):
    assert parse_price(value) == expected


def test_area_requires_a_valid_unit_and_number():
    assert parse_area("450 متر مربع") == 450
    assert parse_area("1,20 sqm") is None
    assert parse_area("450") is None


def test_jsonl_uses_physical_lines_and_reports_invalid_input(tmp_path):
    path = tmp_path / "input.jsonl"
    path.write_text('{"text":"a\u2028b"}\n', encoding="utf-8")
    assert read_records(path) == [{"text": "a\u2028b"}]
    path.write_text('{"text":\n', encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON at line 1"):
        read_records(path)
    with pytest.raises(FileNotFoundError, match="Required input not found"):
        read_records(tmp_path / "missing.jsonl")


def test_pipeline_deduplicates_and_only_keeps_verified_property_details(source_root, tmp_path):
    property_url = "https://wasalt.sa/property/sale/villa-450-sqm-123"
    write_rows(source_root / "dar_global/all_pages.jsonl", [
        {"url": "https://darglobal.co.uk/empty", "text": ""},
        {"url": "https://darglobal.co.uk/project?utm_source=x", "title": "Project", "text": "Pool\nGarden"},
        {"url": "https://darglobal.co.uk/project", "title": "Project", "text": "Pool\nGarden"},
        {"url": "https://evil.example/project", "text": "untrusted"},
    ])
    write_rows(source_root / "wasalt_data/listings.jsonl", [
        {"url": property_url, "city": "Riyadh", "purpose": "sale", "price": None, "area": "450 sqm", "card_text": "Villa in Riyadh"},
        {"url": "https://wasalt.sa/sale/search?type=residential", "purpose": "sale", "card_text": "search"},
    ])
    write_rows(source_root / "wasalt_data/listing_details.jsonl", [
        {
            "url": property_url,
            "title": "villa 450 sqm",
            "text": "villa 450 sqm in Riyadh\nPool\nوصف العقار\nPrivate description\nRecommended other property",
            "scraped_at_utc": "2026-11-19T00:00:00Z",
        },
        {"url": "https://wasalt.sa/sale/search?type=residential", "text": "not a property"},
    ])

    documents, listings, report = prepare_data(source_root)
    assert len(documents) == 2
    assert len(listings) == 1
    assert listings[0]["city"] == "Riyadh"
    assert listings[0]["price"] is None and listings[0]["currency"] is None
    assert listings[0]["area_sqm"] == 450
    listing_document = next(item for item in documents if item["type"] == "listing_detail")
    assert "Pool" in listing_document["text"]
    assert "Recommended other property" not in listing_document["text"]
    assert "Private description" not in listing_document["text"]
    assert report["rejected_or_deduplicated"]["page:empty_text"] == 1
    assert report["rejected_or_deduplicated"]["page:invalid_url"] == 1
    assert report["rejected_or_deduplicated"]["narrative:duplicate_url"] == 1
    assert report["rejected_or_deduplicated"]["listing_card:not_property_url"] == 1

    output = tmp_path / "output"
    write_outputs(output, documents, listings, report)
    first = {p.name: p.read_bytes() for p in output.iterdir()}
    write_outputs(output, *prepare_data(source_root))
    assert first == {p.name: p.read_bytes() for p in output.iterdir()}


def test_pipeline_rejects_mismatched_page_and_missing_description_boundary(source_root):
    url = "https://wasalt.sa/property/sale/villa-450-sqm-123"
    write_rows(source_root / "wasalt_data/listings.jsonl", [
        {"url": url, "city": "Riyadh", "purpose": "sale", "card_text": "Riyadh"},
    ])
    write_rows(source_root / "wasalt_data/listing_details.jsonl", [
        {"url": url, "title": "Other property", "text": "Other property\nوصف العقار\nvilla 450 sqm"},
    ])
    documents, listings, report = prepare_data(source_root)
    assert not documents and not listings
    assert report["rejected_or_deduplicated"]["listing:identity_unverified"] == 1


def test_pipeline_rejects_wrong_title_even_when_main_text_matches(source_root):
    url = "https://wasalt.sa/property/sale/villa-450-sqm-123"
    write_rows(source_root / "wasalt_data/listings.jsonl", [
        {"url": url, "purpose": "sale", "card_text": "Riyadh"},
    ])
    write_rows(source_root / "wasalt_data/listing_details.jsonl", [
        {"url": url, "title": "different property", "text": "villa 450 sqm\nوصف العقار\nDetails"},
    ])
    _, listings, report = prepare_data(source_root)
    assert not listings
    assert report["rejected_or_deduplicated"]["listing:identity_unverified"] == 1


def test_auction_classification_takes_priority_over_company_duplicate(source_root):
    url = "https://auction.wasalt.sa/auction/123"
    write_rows(source_root / "wasalt_company_data/company_pages.jsonl", [
        {"url": url, "title": "Auction", "text": "Generic auction page"},
    ])
    write_rows(source_root / "wasalt_data/auctions.jsonl", [
        {"url": url, "title": "Auction", "text": "Auction information", "record_type": "auction_detail"},
    ])
    documents, _, report = prepare_data(source_root)
    assert len(documents) == 1
    assert documents[0]["type"] == "auction_detail"
    assert report["rejected_or_deduplicated"]["narrative:duplicate_url"] == 1


def test_listing_price_must_be_confirmed_by_detail(source_root):
    url = "https://wasalt.sa/property/sale/villa-450-sqm-123"
    write_rows(source_root / "wasalt_data/listings.jsonl", [
        {"url": url, "purpose": "sale", "price": "SAR 1,000", "card_text": "Riyadh"},
    ])
    write_rows(source_root / "wasalt_data/listing_details.jsonl", [
        {"url": url, "title": "villa 450 sqm", "text": "villa 450 sqm\nوصف العقار\nDetails"},
    ])
    _, listings, report = prepare_data(source_root)
    assert listings[0]["price"] is None
    assert report["rejected_or_deduplicated"]["listing:unverified_price"] == 1


def test_listing_area_and_city_must_match_detail(source_root):
    url = "https://wasalt.sa/property/sale/villa-450-sqm-123"
    write_rows(source_root / "wasalt_data/listings.jsonl", [
        {"url": url, "city": "Riyadh", "purpose": "sale", "area": "500 sqm", "card_text": "Riyadh"},
    ])
    write_rows(source_root / "wasalt_data/listing_details.jsonl", [
        {"url": url, "title": "villa 450 sqm", "text": "villa 450 sqm in Makkah\nوصف العقار\nDetails"},
    ])
    _, listings, report = prepare_data(source_root)
    assert listings[0]["area_sqm"] is None and listings[0]["city"] is None
    assert report["rejected_or_deduplicated"]["listing:unverified_area"] == 1
    assert report["rejected_or_deduplicated"]["listing:unverified_city"] == 1


def test_cli_refuses_to_overwrite_source_data(source_root):
    script = Path(__file__).resolve().parents[1] / "scripts" / "clean_data.py"
    result = subprocess.run(
        [sys.executable, str(script), "--input-root", str(source_root), "--output-dir", str(source_root / "wasalt_data")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "must not overwrite source data" in result.stderr
