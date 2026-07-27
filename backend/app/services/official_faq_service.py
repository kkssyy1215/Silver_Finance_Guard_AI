import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.schemas.common import OfficialFaqItem

OFFICIAL_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "official"


@lru_cache
def _load_kdic_faq_payload() -> dict[str, Any]:
    path = OFFICIAL_DATA_DIR / "kdic_mistaken_transfer_faq.json"
    with path.open(encoding="utf-8") as faq_file:
        return json.load(faq_file)


def search_kdic_mistaken_transfer_faq(query: str, limit: int = 3) -> list[OfficialFaqItem]:
    payload = _load_kdic_faq_payload()
    source = payload["source"]
    scored_items: list[tuple[int, dict[str, Any]]] = []
    query_terms = _terms(query)

    for item in payload["items"]:
        haystack = f"{item['category']} {item['question']} {item['answer']}"
        score = sum(1 for term in query_terms if term and term in haystack)
        score += _domain_boost(query, haystack)
        if score > 0:
            scored_items.append((score, item))

    scored_items.sort(key=lambda pair: (-pair[0], pair[1]["number"]))
    selected = [item for _, item in scored_items[:limit]]

    if not selected:
        selected = payload["items"][:limit]

    return [
        OfficialFaqItem(
            faq_id=item["faq_id"],
            category=item["category"],
            question=item["question"],
            answer=item["answer"],
            source_title=source["title"],
            source_url=source["source_url"],
        )
        for item in selected
    ]


def default_kdic_mistaken_transfer_faq(limit: int = 3) -> list[OfficialFaqItem]:
    return search_kdic_mistaken_transfer_faq("신청 기간 대상 금액 금융회사 반환절차", limit=limit)


def _terms(query: str) -> set[str]:
    base_terms = {term.strip() for term in query.replace(",", " ").replace(".", " ").split()}
    domain_terms = {
        "착오송금",
        "반환지원",
        "신청",
        "금액",
        "기간",
        "금융회사",
        "반환절차",
        "간편송금",
        "사기",
        "압류",
        "분쟁",
        "온라인",
        "방문",
    }
    return base_terms | {term for term in domain_terms if term in query}


def _domain_boost(query: str, haystack: str) -> int:
    boost = 0
    if any(term in query for term in ["언제", "기간", "1년"]) and any(term in haystack for term in ["언제", "1년"]):
        boost += 3
    if any(term in query for term in ["얼마", "금액", "만원"]) and any(term in haystack for term in ["금액", "5만원", "5천만원"]):
        boost += 3
    if any(term in query for term in ["은행", "금융회사", "먼저"]) and "금융회사" in haystack:
        boost += 3
    if any(term in query for term in ["사기", "보이스피싱"]) and "사기" in haystack:
        boost += 3
    return boost
