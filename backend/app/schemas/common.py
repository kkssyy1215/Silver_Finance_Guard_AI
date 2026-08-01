from enum import Enum
from typing import Optional

from pydantic import BaseModel


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"
    unknown = "unknown"


class Confidence(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class EasyExplanation(BaseModel):
    one_line: str
    easy_summary: str
    next_action: str


class SourceReference(BaseModel):
    source_id: str
    title: str
    publisher: str
    url: str
    summary: str
    published_at: Optional[str] = None
    application_reason: str = ""


class OfficialFaqItem(BaseModel):
    faq_id: str
    category: str
    question: str
    answer: str
    source_title: str
    source_url: str
