from pydantic import BaseModel, Field


class ComplaintDraftRequest(BaseModel):
    user_statement: str = Field(min_length=1)
    incident_type: str = "general_complaint"


class ComplaintDraftResponse(BaseModel):
    complaint_type: str
    title: str
    summary: str
    draft_body: str
    recommended_attachments: list[str]
    editable_fields: list[str]
    disclaimer: str

