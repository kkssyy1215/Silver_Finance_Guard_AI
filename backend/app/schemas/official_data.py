from typing import Optional

from pydantic import BaseModel


class OfficialDataset(BaseModel):
    dataset_id: str
    title: str
    publisher: str
    portal: str
    url: str
    format: str
    row_count: Optional[int] = None
    license: str
    fee: str
    modified_at: Optional[str] = None
    status: str
    local_path: Optional[str] = None
    tags: list[str]
    use_cases: list[str]
    summary: str


class OfficialDatasetListResponse(BaseModel):
    datasets: list[OfficialDataset]
