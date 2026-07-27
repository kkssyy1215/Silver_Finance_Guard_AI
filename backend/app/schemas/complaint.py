from pydantic import BaseModel, Field


class ComplaintDraftRequest(BaseModel):
    user_statement: str = Field(min_length=1)
    incident_type: str = "general_complaint"


class SimilarComplaintCase(BaseModel):
    title: str
    case_no: str
    relevance_reason: str
    answer_summary: str


class ComplaintDraftResponse(BaseModel):
    complaint_type: str
    title: str
    summary: str
    draft_body: str
    recommended_attachments: list[str]
    editable_fields: list[str]
    similar_cases: list[SimilarComplaintCase] = Field(default_factory=list)
    claim_points: list[str] = Field(default_factory=list)
    submission_checklist: list[str] = Field(default_factory=list)
    disclaimer: str
