from fastapi import APIRouter

from app.schemas.incident import (
    ActionPlanRequest,
    ActionPlanResponse,
    IncidentClassifyRequest,
    IncidentClassifyResponse,
)
from app.services.action_plan_service import build_action_plan
from app.services.incident_classifier import classify_incident

router = APIRouter()


@router.post("/classify", response_model=IncidentClassifyResponse)
def classify(request: IncidentClassifyRequest) -> IncidentClassifyResponse:
    return classify_incident(request.content)


@router.post("/action-plan", response_model=ActionPlanResponse)
def action_plan(request: ActionPlanRequest) -> ActionPlanResponse:
    return build_action_plan(request.incident_type)

