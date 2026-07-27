from typing import Optional

from pydantic import BaseModel, Field


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


class OfficialRecord(BaseModel):
    dataset_id: str
    title: str
    body: str
    source_title: str
    source_url: Optional[str] = None
    metadata: dict[str, str] = Field(default_factory=dict)


class OfficialRecordSearchResponse(BaseModel):
    query: str
    total_matches: int
    records: list[OfficialRecord]


class FinancialTermExplanation(BaseModel):
    term: str
    official_definition: str
    easy_explanation: str
    action_tip: str
    source_title: str
    source_url: Optional[str] = None


class FinancialTermSearchResponse(BaseModel):
    query: str
    total_matches: int
    terms: list[FinancialTermExplanation]
