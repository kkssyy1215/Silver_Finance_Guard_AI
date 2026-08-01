import re

from app.schemas.analysis import ContractRiskResponse, RiskItem, TextAnalysisRequest
from app.schemas.common import Confidence, EasyExplanation, RiskLevel
from app.services.reference_service import references_for
from app.services.rule_loader import load_rule_file

DISCLAIMER = "이 결과는 법적 판단이 아니라 소비자 보호를 위한 확인 보조 정보입니다."
STANDARD_CHECK_REFERENCES = {
    "auto_renewal": "점검 기준: 자동 연장 여부, 사전 통지 방법, 해지 절차를 계약 전에 확인합니다.",
    "excessive_penalty": "점검 기준: 중도 해지 시 실제 부담액과 산정 방법을 계약 전에 확인합니다.",
    "third_party_data": "점검 기준: 개인정보 제공 동의가 필수인지 선택인지, 거부할 수 있는지 확인합니다.",
    "principal_guarantee_misleading": "점검 기준: 원금 손실 가능성과 예금자보호 대상 여부를 따로 확인합니다.",
    "pressure_sales": "점검 기준: 충분한 설명과 판단 시간을 받았는지 확인합니다.",
    "unclear_fee": "점검 기준: 가입·유지·해지 과정의 모든 비용과 산정 방법을 확인합니다.",
    "termination_limit": "점검 기준: 해지 가능한 시점, 방법, 제한 조건을 확인합니다.",
}

SENIOR_ACTIONS = {
    "auto_renewal": "상담사에게 '자동으로 계속되는지'를 큰 소리로 다시 설명해 달라고 요청하세요.",
    "excessive_penalty": "해지하면 실제로 얼마를 내는지 숫자로 적어 달라고 요청하세요.",
    "third_party_data": "광고 전화가 올 수 있는 동의인지, 거절해도 가입 가능한지 먼저 확인하세요.",
    "principal_guarantee_misleading": "예금자보호 대상인지, 원금을 잃을 수 있는지 둘 다 물어보세요.",
    "pressure_sales": "오늘 결정하지 말고 가족이나 지인에게 보여준 뒤 다시 판단하세요.",
    "unclear_fee": "가입비, 유지비, 중도해지비를 한 장 표로 달라고 요청하세요.",
    "termination_limit": "언제, 어디서, 어떤 서류로 해지할 수 있는지 적어 달라고 요청하세요.",
}

REFERENCE_REASONS = {
    "auto_renewal": "자동 연장·해지 조건을 가입 전에 다시 확인하는 기준으로 사용했습니다.",
    "excessive_penalty": "해지 비용과 거래 비용을 계약 전에 확인하는 기준으로 사용했습니다.",
    "third_party_data": "개인정보 제공 동의가 필수인지 선택인지 확인하는 기준으로 사용했습니다.",
    "principal_guarantee_misleading": "원금 손실과 예금자보호 여부를 구분해 확인하는 기준으로 사용했습니다.",
    "pressure_sales": "충분한 설명과 판단 시간을 받았는지 확인하는 기준으로 사용했습니다.",
    "unclear_fee": "가입·유지·해지 비용을 확인하는 기준으로 사용했습니다.",
    "termination_limit": "해지 방법과 제한 조건을 확인하는 기준으로 사용했습니다.",
}


def _contains_any(text: str, keywords: list[str]) -> bool:
    normalized = text.lower()
    return any(keyword.lower() in normalized for keyword in keywords)


def _keyword_is_active(text: str, keyword: str) -> bool:
    """Treat explicit negative wording as evidence against a risk candidate."""
    before_negation = re.compile(r"(안|않|못|아니|제외|거부)\s*$")
    after_negation = re.compile(r"^\s*(?:(?:가|이|은|는|을|를|도|하지|되지)\s*)?(?:없(?!이)|아니|않|못|제외|미제공|거부|하지\s*(?:않|못))")
    for match in re.finditer(re.escape(keyword), text, flags=re.IGNORECASE):
        context = text[max(0, match.start() - 12) : min(len(text), match.end() + 14)]
        before = text[max(0, match.start() - 6) : match.start()]
        after = text[match.end() : match.end() + 14]
        if before_negation.search(before) or after_negation.search(after):
            continue
        return True
    return False


def _matched_keywords(text: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if _keyword_is_active(text, keyword)]


def _confidence_for(keywords: list[str], matched_keywords: list[str]) -> Confidence:
    if len(matched_keywords) >= 2 or any(len(keyword.replace(" ", "")) >= 5 for keyword in matched_keywords):
        return Confidence.high
    return Confidence.medium


def _references_for_risk(label: str):
    reason = REFERENCE_REASONS.get(label, "공식 소비자보호 자료를 확인 기준으로 사용했습니다.")
    return references_for("consumer_protection", application_reason=reason)


def analyze_contract_risk(request: TextAnalysisRequest) -> ContractRiskResponse:
    labels = load_rule_file("contract_risk_labels.json")
    matched_items: list[RiskItem] = []
    comparison_summaries: list[str] = []

    for rule in labels:
        if any(_contains_any(request.content, [excluded]) for excluded in rule.get("exclude_keywords", [])):
            continue
        if any(_keyword_is_active(request.content, keyword) for keyword in rule["keywords"]):
            context = _find_context(request.content, rule["keywords"])
            detected_keywords = _matched_keywords(context, rule["keywords"])
            confidence = _confidence_for(rule["keywords"], detected_keywords)
            standard_refs = find_standard_clause_references(rule["label"], context)
            comparison = compare_with_standard_terms(rule["label"], context, standard_refs)
            comparison_summaries.append(comparison)
            matched_items.append(
                RiskItem(
                    label=rule["label"],
                    severity=rule["severity"],
                    confidence=confidence,
                    review_status="주의 후보" if confidence == Confidence.high else "확인 필요",
                    original_text=context,
                    detected_keywords=detected_keywords,
                    simplified_text=rule["simplified_text"],
                    why_it_matters=rule["why_it_matters"],
                    must_ask_question=rule["must_ask_question"],
                    senior_action=SENIOR_ACTIONS.get(rule["label"], "중요한 조건은 서면으로 받아 가족이나 신뢰할 수 있는 사람과 함께 확인하세요."),
                    standard_references=standard_refs,
                    comparison_result=comparison,
                    official_references=_references_for_risk(rule["label"]),
                )
            )

    overall_risk = _overall_risk(matched_items)
    questions = [item.must_ask_question for item in matched_items[:5]]

    if matched_items:
        summary = EasyExplanation(
            one_line=f"확인할 내용이 {len(matched_items)}개 있습니다.",
            easy_summary="가입 전 다시 물어봐야 할 조건이 보입니다. 공식 소비자보호 기준과 함께 확인하세요.",
            next_action="아래 질문을 상담사에게 묻고, 답변을 문자나 서류로 남겨두세요.",
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
        standard_comparison_summary=comparison_summaries[:5],
        references=references_for("consumer_protection"),
        disclaimer=DISCLAIMER,
    )


def find_standard_clause_references(label: str, context: str, limit: int = 2) -> list[str]:
    del context, limit
    reference = STANDARD_CHECK_REFERENCES.get(label)
    return [reference] if reference else []


def compare_with_standard_terms(label: str, context: str, standard_refs: list[str]) -> str:
    del context, standard_refs

    warning = {
        "auto_renewal": "자동 연장 조건은 소비자가 쉽게 알 수 있게 안내되어야 하므로 해지 방법과 통지 여부를 확인해야 합니다.",
        "excessive_penalty": "해지 비용이나 위약금은 실제 손해보다 과도한지 확인해야 합니다.",
        "third_party_data": "개인정보 제공 동의는 필수인지 선택인지 분리되어야 하며, 거절 가능 여부를 확인해야 합니다.",
        "principal_guarantee_misleading": "예금과 투자상품은 보호 범위가 다르므로 원금 보장 표현을 그대로 믿으면 안 됩니다.",
        "pressure_sales": "충분한 설명과 판단 시간을 주지 않는 권유는 불완전판매 위험 신호입니다.",
        "unclear_fee": "비용·수수료·지연배상금은 소비자가 계약 전 알 수 있어야 합니다.",
        "termination_limit": "해지 제한이나 기한의 이익 상실은 소비자에게 큰 부담이 되므로 발생 조건을 구체적으로 확인해야 합니다.",
    }.get(label, "표준약관과 다른 불리한 조건인지 확인해야 합니다.")

    return warning


def _find_context(content: str, keywords: list[str]) -> str:
    sentences = [part.strip() for part in re.split(r"[.!?。！？\n]+", content)]
    for sentence in sentences:
        if any(_keyword_is_active(sentence, keyword) for keyword in keywords):
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
