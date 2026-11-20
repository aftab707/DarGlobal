import hashlib
import json
import math
import re
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit


@dataclass(frozen=True)
class Source:
    path: str
    source: str
    kind: str


SOURCES = (
    Source("dar_global/all_pages.jsonl", "DarGlobal", "page"),
    Source("wasalt_company_data/company_pages.jsonl", "Wasalt", "company"),
    Source("wasalt_data/company.jsonl", "Wasalt", "company"),
    Source("wasalt_data/categories.jsonl", "Wasalt", "category"),
    Source("wasalt_data/auctions.jsonl", "Wasalt", "auction"),
    Source("wasalt_data/listings.jsonl", "Wasalt", "listing_card"),
    Source("wasalt_data/listing_details.jsonl", "Wasalt", "listing_detail"),
)
HOSTS = {
    "DarGlobal": {"darglobal.co.uk", "www.darglobal.co.uk"},
    "Wasalt": {"wasalt.sa", "www.wasalt.sa", "auction.wasalt.sa"},
}
TRACKING_KEYS = {"gclid", "fbclid", "sfmc_activityid", "sfmc_journey_id"}
EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", re.I)
PHONE = re.compile(r"(?<![\w\d])(?:\+|00)?[0-9٠-٩۰-۹][0-9٠-٩۰-۹ \t().-]{7,}[0-9٠-٩۰-۹](?![\w\d])")
PROPERTY_PATH = re.compile(r"^/property/(sale|rent)/[^/]+-(\d+)/?$", re.I)
NUMBER_TRANSLATION = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
CITY_VARIANTS = {
    "Riyadh": ("الرياض", "riyadh"),
    "Makkah": ("مكة", "makkah", "mecca"),
    "Madinah": ("المدينة", "madinah", "medina"),
}


def canonical_url(value: Any, source: str) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parts = urlsplit(value.strip())
        host = parts.hostname
        if (
            parts.scheme.lower() not in {"http", "https"}
            or host not in HOSTS[source]
            or parts.username is not None
            or parts.password is not None
            or parts.port is not None
            or re.search(r"%(?![0-9A-Fa-f]{2})", parts.path)
        ):
            return None
    except ValueError:
        return None
    path = quote(parts.path or "/", safe="/%:@!$&'()*+,;=-._~")
    path = re.sub(r"%[0-9a-fA-F]{2}", lambda match: match.group().upper(), path)
    if path != "/":
        path = path.rstrip("/")
    query = [
        (key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_KEYS
    ]
    return urlunsplit((parts.scheme.lower(), host, path, urlencode(query, doseq=True), ""))


def clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = EMAIL.sub("[contact removed]", value)
    value = PHONE.sub("[number removed]", value)
    lines: list[str] = []
    for raw in value.replace("\xa0", " ").split("\n"):
        line = re.sub(r"[ \t\r\f\v]+", " ", raw).strip()
        if line and (not lines or line != lines[-1]):
            lines.append(line)
    return "\n".join(lines)


def read_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as file:
            for number, line in enumerate(file, 1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}: invalid JSON at line {number}: {exc.msg}") from exc
                if not isinstance(value, dict):
                    raise ValueError(f"{path}: expected an object at line {number}")
                records.append(value)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Required input not found: {path}") from exc
    return records


def property_match(url: str) -> re.Match[str] | None:
    parts = urlsplit(url)
    if parts.hostname not in {"wasalt.sa", "www.wasalt.sa"}:
        return None
    return PROPERTY_PATH.fullmatch(unquote(parts.path))


def detail_matches_url(url: str, record: dict[str, Any]) -> bool:
    match = property_match(url)
    if not match:
        return False
    slug = unquote(urlsplit(url).path).rsplit("/", 1)[-1].rsplit("-", 1)[0]
    tokens = [token.casefold() for token in re.findall(r"[^\W_]+", slug) if len(token) > 1]
    text = record.get("text")
    if not isinstance(text, str) or not tokens:
        return False
    # Only the main property section can establish identity, not recommendations.
    if "وصف العقار" not in text:
        return False
    main = text.split("وصف العقار", 1)[0]
    words = set(re.findall(r"[^\W_]+", main.casefold()))
    title = record.get("title")
    if not isinstance(title, str):
        return False
    title_words = set(re.findall(r"[^\W_]+", title.casefold()))
    return (
        sum(token in words for token in tokens) / len(tokens) >= 0.6
        and sum(token in title_words for token in tokens) / len(tokens) >= 0.6
    )


def parse_area(value: Any) -> float | None:
    if not isinstance(value, str):
        return None
    normalized = value.translate(NUMBER_TRANSLATION).strip()
    match = re.fullmatch(r"(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s*(?:متر مربع|م²|م2|sqm|m²)", normalized, re.I)
    if not match:
        return None
    number = float(match.group(1).replace(",", "") + (match.group(2) or ""))
    return number if math.isfinite(number) and number > 0 else None


def parse_price(value: Any) -> tuple[float | None, str | None]:
    if not isinstance(value, str):
        return None, None
    normalized = value.translate(NUMBER_TRANSLATION).strip()
    match = re.fullmatch(
        r"(?:(SAR|ر\.س\.?)\s*((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)|((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*(SAR|ر\.س\.?))",
        normalized,
        re.I,
    )
    if not match:
        return None, None
    number = float((match.group(2) or match.group(3)).replace(",", ""))
    return (number, "SAR") if math.isfinite(number) and number > 0 else (None, None)


def listing_city(card: dict[str, Any]) -> str | None:
    city = card.get("city")
    if not isinstance(city, str) or city not in CITY_VARIANTS:
        return None
    text = str(card.get("card_text") or "").casefold()
    present = {name for name, names in CITY_VARIANTS.items() if any(item in text for item in names)}
    return city if present == {city} else None


def property_type(title: str) -> str | None:
    options = {
        "villa": ("فيلا", "villa"),
        "apartment": ("شقة", "apartment"),
        "land": ("أرض", "ارض", "land"),
    }
    text = title.casefold()
    found = [
        kind for kind, terms in options.items()
        if any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) for term in terms)
    ]
    return found[0] if len(found) == 1 else None


def record_rank(record: dict[str, Any]) -> tuple[str, int, str]:
    timestamp = record.get("scraped_at_utc") or record.get("scraped_at") or ""
    timestamp = timestamp if isinstance(timestamp, str) else ""
    serialized = json.dumps(record, ensure_ascii=False, sort_keys=True)
    return timestamp, len(str(record.get("text") or "")), hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def source_document(source: Source, record: dict[str, Any], url: str) -> dict[str, Any]:
    kind = source.kind
    if source.source == "DarGlobal":
        kind = str(record.get("page_type") or "page")
    elif kind in {"category", "auction"}:
        kind = str(record.get("record_type") or kind)
    timestamp = record.get("scraped_at_utc") or record.get("scraped_at")
    return {
        "source": source.source,
        "url": url,
        "title": clean_text(record.get("title")),
        "type": kind,
        "scraped_at": timestamp if isinstance(timestamp, str) and timestamp else None,
        "text": clean_text(record.get("text")),
    }


def prepare_data(input_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    inputs: dict[str, Any] = {}
    rejected: Counter[str] = Counter()
    records_by_kind: dict[str, list[tuple[Source, dict[str, Any], str]]] = {
        "narrative": [], "listing_card": [], "listing_detail": []
    }
    for spec in SOURCES:
        records = read_records(input_root / spec.path)
        raw_urls: list[str] = []
        valid_urls: list[str] = []
        empty_text = missing_price = missing_area = whitespace_urls = invalid_urls = missing_titles = 0
        for record in records:
            raw_url = record.get("url")
            if isinstance(raw_url, str) and raw_url:
                raw_urls.append(raw_url)
                whitespace_urls += int(any(character.isspace() for character in raw_url))
            missing_titles += int(not clean_text(record.get("title")))
            text_empty = spec.kind != "listing_card" and not clean_text(record.get("text"))
            empty_text += int(text_empty)
            if spec.kind == "listing_card":
                missing_price += int(record.get("price") in (None, ""))
                missing_area += int(record.get("area") in (None, ""))
            url = canonical_url(raw_url, spec.source)
            if not url:
                invalid_urls += 1
                rejected[f"{spec.kind}:invalid_url"] += 1
                continue
            valid_urls.append(url)
            if text_empty:
                rejected[f"{spec.kind}:empty_text"] += 1
                continue
            category = spec.kind if spec.kind in {"listing_card", "listing_detail"} else "narrative"
            records_by_kind[category].append((spec, record, url))
        inputs[spec.path] = {
            "records": len(records),
            "exact_duplicate_url_rows": len(raw_urls) - len(set(raw_urls)),
            "canonical_duplicate_url_rows": len(valid_urls) - len(set(valid_urls)),
            "urls_with_raw_whitespace": whitespace_urls,
            "invalid_or_missing_url": invalid_urls,
            "missing_title": missing_titles,
            "empty_text": empty_text if spec.kind != "listing_card" else None,
            "missing_price": missing_price if spec.kind == "listing_card" else None,
            "missing_area": missing_area if spec.kind == "listing_card" else None,
        }

    narratives: dict[tuple[str, str], tuple[Source, dict[str, Any]]] = {}
    for spec, record, url in records_by_kind["narrative"]:
        key = (spec.source, url)
        previous = narratives.get(key)
        if previous:
            rejected["narrative:duplicate_url"] += 1
            # Specific auction and category records take precedence over generic company pages.
            priority = {"auction": 2, "category": 1}
            rank = (priority.get(spec.kind, 0), spec.path == "wasalt_company_data/company_pages.jsonl", record_rank(record))
            prev_rank = (priority.get(previous[0].kind, 0), previous[0].path == "wasalt_company_data/company_pages.jsonl", record_rank(previous[1]))
            if rank <= prev_rank:
                continue
        narratives[key] = (spec, record)

    grouped: dict[str, dict[str, dict[str, Any]]] = {"listing_card": {}, "listing_detail": {}}
    for kind in grouped:
        for _, record, url in records_by_kind[kind]:
            if not property_match(url):
                rejected[f"{kind}:not_property_url"] += 1
                continue
            previous = grouped[kind].get(url)
            if previous:
                rejected[f"{kind}:duplicate_url"] += 1
                if record_rank(record) <= record_rank(previous):
                    continue
            grouped[kind][url] = record

    documents = [source_document(spec, record, url) for (source, url), (spec, record) in narratives.items()]
    listings: list[dict[str, Any]] = []
    for url, card in grouped["listing_card"].items():
        detail = grouped["listing_detail"].get(url)
        if not detail:
            rejected["listing:missing_detail"] += 1
            continue
        if not detail_matches_url(url, detail):
            rejected["listing:identity_unverified"] += 1
            continue
        match = property_match(url)
        assert match is not None
        if card.get("purpose") != match.group(1).lower():
            rejected["listing:purpose_conflict"] += 1
            continue
        title = clean_text(detail.get("title"))
        main_text = str(detail["text"]).split("وصف العقار", 1)[0]
        normalized_main = re.sub(r"\s+", " ", main_text).casefold()
        city = listing_city(card)
        if city and not any(variant in normalized_main for variant in CITY_VARIANTS[city]):
            city = None
            rejected["listing:unverified_city"] += 1
        area = parse_area(card.get("area"))
        if area is not None:
            card_area = re.sub(r"\s+", " ", str(card["area"])).strip().casefold()
            if card_area not in normalized_main:
                area = None
                rejected["listing:unverified_area"] += 1
        price, currency = parse_price(card.get("price"))
        if price is not None:
            card_price = re.sub(r"\s+", " ", str(card["price"])).strip().casefold()
            if card_price not in normalized_main:
                price, currency = None, None
                rejected["listing:unverified_price"] += 1
        listing = {
            "source": "Wasalt",
            "url": url,
            "property_id": match.group(2),
            "title": title,
            "city": city,
            "purpose": match.group(1).lower(),
            "property_type": property_type(title),
            "price": price,
            "currency": currency,
            "area_sqm": area,
            "scraped_at": detail.get("scraped_at_utc") or None,
        }
        listings.append(listing)
        documents.append({
            "source": "Wasalt",
            "url": url,
            "title": title,
            "type": "listing_detail",
            "scraped_at": listing["scraped_at"],
            "text": clean_text(main_text),
        })
    rejected["listing_detail:without_card"] = len(set(grouped["listing_detail"]) - set(grouped["listing_card"]))
    documents.sort(key=lambda item: (item["source"], item["url"], item["type"]))
    listings.sort(key=lambda item: item["url"])
    report = {
        "inputs": inputs,
        "rejected_or_deduplicated": dict(sorted(rejected.items())),
        "output": {
            "documents": len(documents),
            "listings": len(listings),
            "documents_by_source": dict(sorted(Counter(item["source"] for item in documents).items())),
            "documents_by_type": dict(sorted(Counter(f"{item['source']}:{item['type']}" for item in documents).items())),
            "listings_missing_price": sum(item["price"] is None for item in listings),
            "listings_missing_city": sum(item["city"] is None for item in listings),
            "listings_missing_area": sum(item["area_sqm"] is None for item in listings),
            "listings_missing_property_type": sum(item["property_type"] is None for item in listings),
        },
        "limitations": [
            "Snapshots are not live inventory; verify prices and availability at the source.",
            "Listing descriptions and recommendations are excluded to avoid misattribution and contact details.",
            "Contact redaction is best effort, not a guarantee of anonymization.",
            "The URL/title identity heuristic can exclude valid listings and requires review.",
        ],
    }
    return documents, listings, report


def write_outputs(output_dir: Path, documents: list[dict[str, Any]], listings: list[dict[str, Any]], report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "documents.jsonl": "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in documents),
        "listings.jsonl": "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in listings),
        "audit_report.json": json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    }
    for name, content in outputs.items():
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=output_dir, delete=False) as file:
                temporary = Path(file.name)
                file.write(content)
            temporary.replace(output_dir / name)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
