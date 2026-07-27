from app.schemas.analysis import (
    ExplanationRiskResponse,
    SuspiciousPoint,
    TextAnalysisRequest,
)
from app.schemas.common import Confidence, EasyExplanation, RiskLevel
from app.services.reference_service import references_for
from app.services.risk_detector import DISCLAIMER, _contains_any, _find_context
from app.services.rule_loader import load_rule_file


def analyze_explanation_risk(request: TextAnalysisRequest) -> ExplanationRiskResponse:
    labels = load_rule_file("explanation_risk_labels.json")
    points: list[SuspiciousPoint] = []

    for rule in labels:
        if _contains_any(request.content, rule["keywords"]):
            points.append(
                SuspiciousPoint(
                    label=rule["label"],
                    severity=rule["severity"],
                    detected_text=_find_context(request.content, rule["keywords"]),
                    reason=rule["reason"],
                    easy_explanation=rule["easy_explanation"],
                    must_ask_question=rule["must_ask_question"],
                )
            )

    risk_level = RiskLevel.high if any(p.severity == RiskLevel.high for p in points) else RiskLevel.medium if points else RiskLevel.low
    questions = [point.must_ask_question for point in points[:5]]
    missing = _missing_explanations(request.content)

    if not questions:
        questions = [
            "원금 손실 가능성이 있나요?",
            "수수료와 해지 비용은 얼마인가요?",
            "오늘 가입하지 않아도 같은 조건인가요?",
        ]

    return ExplanationRiskResponse(
        risk_level=risk_level,
        confidence=Confidence.high if points else Confidence.medium,
        summary=EasyExplanation(
            one_line="가입 전 확인이 필요합니다." if points else "큰 위험 표현은 찾지 못했습니다.",
            easy_summary="상담 내용에서 다시 물어봐야 할 표현이 있습니다." if points else "그래도 핵심 비용과 위험은 직접 확인하세요.",
            next_action="오늘 바로 결정하지 말고 설명서와 약관을 받아 확인하세요.",
        ),
        suspicious_points=points,
        missing_explanations=missing,
        must_ask_questions=questions,
        recommended_next_step="상품설명서와 약관을 받아 보호자와 함께 확인하세요.",
        references=references_for("consumer_protection"),
        disclaimer=DISCLAIMER,
    )


def _missing_explanations(content: str) -> list[str]:
    checks = {
        "원금 손실 가능성": ["손실", "원금", "위험"],
        "수수료": ["수수료", "비용"],
        "해지 조건": ["해지", "취소", "청약철회"],
    }
    return [label for label, keywords in checks.items() if not _contains_any(content, keywords)]
