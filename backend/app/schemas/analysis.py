from pydantic import BaseModel, Field

from app.schemas.common import Confidence, EasyExplanation, RiskLevel, SourceReference


class TextAnalysisRequest(BaseModel):
    content: str = Field(min_length=1, max_length=50_000)
    content_type: str = "text"
    user_age_group: str = "senior"
    product_type: str = "unknown"


class ExtractedDocumentText(BaseModel):
    source_type: str
    text: str
    quality_message: str


class RiskItem(BaseModel):
    label: str
    severity: RiskLevel
    confidence: Confidence
    review_status: str = "주의 후보"
    original_text: str
    detected_keywords: list[str] = Field(default_factory=list)
    simplified_text: str
    why_it_matters: str
    must_ask_question: str
    senior_action: str = ""
    standard_references: list[str] = Field(default_factory=list)
    comparison_result: str = ""
    official_references: list[SourceReference] = Field(default_factory=list)


class ContractRiskResponse(BaseModel):
    overall_risk: RiskLevel
    document_summary: EasyExplanation
    risk_items: list[RiskItem]
    must_ask_questions: list[str]
    standard_comparison_summary: list[str] = Field(default_factory=list)
    references: list[SourceReference]
    disclaimer: str


class SuspiciousPoint(BaseModel):
    label: str
    severity: RiskLevel
    review_status: str = "주의 후보"
    detected_text: str
    detected_keywords: list[str] = Field(default_factory=list)
    reason: str
    easy_explanation: str
    must_ask_question: str
    official_references: list[SourceReference] = Field(default_factory=list)


class AudioTranscriptionResponse(BaseModel):
    text: str = ""
    available: bool = False
    message: str


class ExplanationRiskResponse(BaseModel):
    risk_level: RiskLevel
    confidence: Confidence
    summary: EasyExplanation
    suspicious_points: list[SuspiciousPoint]
    missing_explanations: list[str]
    must_ask_questions: list[str]
    recommended_next_step: str
    references: list[SourceReference]
    disclaimer: str
