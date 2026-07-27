from fastapi import APIRouter

from app.schemas.complaint import ComplaintDraftRequest, ComplaintDraftResponse
from app.services.complaint_service import draft_complaint

router = APIRouter()


@router.post("/draft", response_model=ComplaintDraftResponse)
def draft(request: ComplaintDraftRequest) -> ComplaintDraftResponse:
    return draft_complaint(request.user_statement, request.incident_type)

