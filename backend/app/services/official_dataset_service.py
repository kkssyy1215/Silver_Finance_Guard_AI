import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from app.schemas.official_data import OfficialDataset

OFFICIAL_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "official"


@lru_cache
def load_official_dataset_registry() -> list[OfficialDataset]:
    path = OFFICIAL_DATA_DIR / "official_dataset_registry.json"
    with path.open(encoding="utf-8") as registry_file:
        raw_items: list[dict[str, Any]] = json.load(registry_file)
    return [OfficialDataset(**item) for item in raw_items]


def find_official_datasets(query: str = "", status: Optional[str] = None, use_case: Optional[str] = None) -> list[OfficialDataset]:
    datasets = load_official_dataset_registry()
    filtered = []
    normalized_query = query.strip().lower()

    for dataset in datasets:
        if status and dataset.status != status:
            continue
        if use_case and use_case not in dataset.use_cases:
            continue
        if normalized_query:
            haystack = " ".join(
                [
                    dataset.title,
                    dataset.publisher,
                    dataset.portal,
                    dataset.summary,
                    " ".join(dataset.tags),
                    " ".join(dataset.use_cases),
                ]
            ).lower()
            if normalized_query not in haystack:
                continue
        filtered.append(dataset)

    return filtered
