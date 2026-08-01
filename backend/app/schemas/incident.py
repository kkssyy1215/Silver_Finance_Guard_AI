from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import Confidence, OfficialFaqItem, RiskLevel, SourceReference


class IncidentClassifyRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)


class ExtractedFacts(BaseModel):
    amount: Optional[int] = None
    transfer_done: Optional[bool] = None
    cash_delivery: Optional[bool] = None
    app_installed: Optional[bool] = None
    personal_info_shared: Optional[bool] = None
    counterparty_claim: Optional[str] = None
    channel: Optional[str] = None


class IncidentEvidence(BaseModel):
    title: str
    summary: str
    source_title: str
    matched_fields: list[str] = Field(default_factory=list)


class IncidentClassifyResponse(BaseModel):
    incident_type: str
    urgency_level: RiskLevel
    confidence: Confidence
    extracted_facts: ExtractedFacts
    risk_signals: list[str]
    first_action_summary: str
    needs_more_info: bool
    follow_up_questions: list[str]
    evidence: list[IncidentEvidence] = Field(default_factory=list)
    urgency_reasons: list[str] = Field(default_factory=list)
    references: list[SourceReference]
    faq_matches: list[OfficialFaqItem]
    disclaimer: str


class ActionPlanRequest(BaseModel):
    incident_type: str
    content: str = Field(default="", max_length=20_000)


class ActionStep(BaseModel):
    order: int
    action: str
    reason: str


class RequiredDocument(BaseModel):
    document_type: str
    name: str
    reason: str
    alternative: Optional[str] = None


class ActionPlanResponse(BaseModel):
    incident_type: str
    urgency_level: RiskLevel
    immediate: list[ActionStep]
    within_10min: list[ActionStep]
    today: list[ActionStep]
    follow_up: list[ActionStep]
    required_documents: list[RequiredDocument]
    related_orgs: list[str]
    evidence: list[IncidentEvidence] = Field(default_factory=list)
    urgency_reasons: list[str] = Field(default_factory=list)
    references: list[SourceReference]
    faq_matches: list[OfficialFaqItem]
    disclaimer: str
