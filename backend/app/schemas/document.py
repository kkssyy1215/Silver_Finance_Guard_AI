from pydantic import BaseModel, Field


class DocumentExportRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=50_000)
    attachments: list[str] = []
    export_format: str = "txt"


class DocumentExportResponse(BaseModel):
    filename: str
    media_type: str
    content: str
