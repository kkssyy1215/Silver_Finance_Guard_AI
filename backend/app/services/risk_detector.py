from app.schemas.analysis import ContractRiskResponse, RiskItem, TextAnalysisRequest
from app.schemas.common import EasyExplanation, RiskLevel
from app.services.reference_service import references_for
from app.services.rule_loader import load_rule_file

DISCLAIMER = "이 결과는 법적 판단이 아니라 소비자 보호를 위한 확인 보조 정보입니다."


def _contains_any(text: str, keywords: list[str]) -> bool:
    normalized = text.lower()
    return any(keyword.lower() in normalized for keyword in keywords)


def analyze_contract_risk(request: TextAnalysisRequest) -> ContractRiskResponse:
    labels = load_rule_file("contract_risk_labels.json")
    matched_items: list[RiskItem] = []

    for rule in labels:
        if _contains_any(request.content, rule["keywords"]):
            matched_items.append(
                RiskItem(
                    label=rule["label"],
                    severity=rule["severity"],
                    confidence="high",
                    original_text=_find_context(request.content, rule["keywords"]),
                    simplified_text=rule["simplified_text"],
                    why_it_matters=rule["why_it_matters"],
                    must_ask_question=rule["must_ask_question"],
                )
            )

    overall_risk = _overall_risk(matched_items)
    questions = [item.must_ask_question for item in matched_items[:5]]

    if matched_items:
        summary = EasyExplanation(
            one_line=f"확인할 내용이 {len(matched_items)}개 있습니다.",
            easy_summary="가입 전 다시 물어봐야 할 조건이 보입니다.",
            next_action="아래 질문을 상담사에게 먼저 물어보세요.",
        )
    else:
        summary = EasyExplanation(
            one_line="큰 위험 문구는 찾지 못했습니다.",
            easy_summary="현재 입력에서 주요 위험 패턴은 보이지 않습니다.",
            next_action="그래도 가입 전 수수료, 해지, 원금 손실 여부를 확인하세요.",
        )

    return ContractRiskResponse(
        overall_risk=overall_risk,
        document_summary=summary,
        risk_items=matched_items,
        must_ask_questions=questions,
        references=references_for("consumer_protection"),
        disclaimer=DISCLAIMER,
    )


def _find_context(content: str, keywords: list[str]) -> str:
    sentences = [part.strip() for part in content.replace("\n", " ").split(".")]
    for sentence in sentences:
        if _contains_any(sentence, keywords):
            return sentence[:240]
    return content[:240]


def _overall_risk(items: list[RiskItem]) -> RiskLevel:
    if any(item.severity == RiskLevel.high for item in items):
        return RiskLevel.high
    if any(item.severity == RiskLevel.medium for item in items):
        return RiskLevel.medium
    if items:
        return RiskLevel.low
    return RiskLevel.low
