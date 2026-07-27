from enum import Enum
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
