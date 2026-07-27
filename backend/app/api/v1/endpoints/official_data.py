from typing import Optional

from fastapi import APIRouter

from app.schemas.official_data import OfficialDatasetListResponse, OfficialRecordSearchResponse
from app.services.official_dataset_service import find_official_datasets, search_official_records

router = APIRouter()


@router.get("/datasets", response_model=OfficialDatasetListResponse)
def list_datasets(query: str = "", status: Optional[str] = None, use_case: Optional[str] = None) -> OfficialDatasetListResponse:
    return OfficialDatasetListResponse(
        datasets=find_official_datasets(query=query, status=status, use_case=use_case)
    )


@router.get("/records/search", response_model=OfficialRecordSearchResponse)
def search_records(query: str, dataset_id: Optional[str] = None, limit: int = 10) -> OfficialRecordSearchResponse:
    safe_limit = min(max(limit, 1), 30)
    records = search_official_records(query=query, dataset_id=dataset_id, limit=safe_limit)
    return OfficialRecordSearchResponse(query=query, total_matches=len(records), records=records)
