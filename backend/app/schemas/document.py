from pydantic import BaseModel, Field


class DocumentExportRequest(BaseModel):
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    attachments: list[str] = []
    export_format: str = "txt"


class DocumentExportResponse(BaseModel):
    filename: str
    media_type: str
    content: str

