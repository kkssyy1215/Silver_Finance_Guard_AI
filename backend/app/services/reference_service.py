from __future__ import annotations

import json
from pathlib import Path

from app.schemas.common import SourceReference
from app.services.rule_loader import load_rule_file


def references_for(*categories: str, application_reason: str = "") -> list[SourceReference]:
    knowledge_base = load_rule_file("knowledge_base.json")
    selected = []
    wanted = set(categories)

    for source in knowledge_base:
        if source["category"] in wanted:
            selected.append(
                SourceReference(
                    source_id=source["source_id"],
                    title=source["title"],
                    publisher=source["publisher"],
                    url=source["url"],
                    summary=source["summary"],
                    published_at=source.get("published_at") or "공식 페이지에 별도 표기 없음",
                    application_reason=application_reason or source.get("application_reason", ""),
                )
            )

    return selected


def official_dataset_reference(dataset_id: str, application_reason: str = "") -> SourceReference | None:
    """Return a traceable reference card for an imported official dataset."""
    # The registry lives beside the normalized data, not in the rules directory.
    path = Path(__file__).resolve().parents[1] / "data" / "official" / "official_dataset_registry.json"
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as registry_file:
        datasets = json.load(registry_file)
    item = next((row for row in datasets if row.get("dataset_id") == dataset_id), None)
    if not item:
        return None
    return SourceReference(
        source_id=item["dataset_id"],
        title=item["title"],
        publisher=item["publisher"],
        url=item.get("url", ""),
        summary=item.get("summary", ""),
        published_at=item.get("modified_at") or "공식 데이터에 별도 표기 없음",
        application_reason=application_reason,
    )
