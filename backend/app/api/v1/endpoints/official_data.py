from typing import Optional

from fastapi import APIRouter

from app.schemas.official_data import OfficialDatasetListResponse
from app.services.official_dataset_service import find_official_datasets

router = APIRouter()


@router.get("/datasets", response_model=OfficialDatasetListResponse)
def list_datasets(query: str = "", status: Optional[str] = None, use_case: Optional[str] = None) -> OfficialDatasetListResponse:
    return OfficialDatasetListResponse(
        datasets=find_official_datasets(query=query, status=status, use_case=use_case)
    )
