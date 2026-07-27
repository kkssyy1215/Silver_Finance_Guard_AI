import json
import re
from functools import lru_cache
from pathlib import Path

from app.schemas.analysis import ContractRiskResponse, RiskItem, TextAnalysisRequest
from app.schemas.common import EasyExplanation, RiskLevel
from app.services.reference_service import references_for
from app.services.rule_loader import load_rule_file

DISCLAIMER = "이 결과는 법적 판단이 아니라 소비자 보호를 위한 확인 보조 정보입니다."
OFFICIAL_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "official"

STANDARD_QUERY_TERMS = {
    "auto_renewal": ["자동", "갱신", "연장", "통지", "해지"],
    "excessive_penalty": ["위약금", "손해배상", "해지", "상환", "비용"],
    "third_party_data": ["동의", "제공", "개인정보", "제3자", "통지"],
    "principal_guarantee_misleading": ["예금", "보호", "원금", "손실", "위험"],
    "pressure_sales": ["설명", "통지", "교부", "열람", "확인"],
    "unclear_fee": ["비용", "수수료", "이자", "지연배상금", "인지세"],
    "termination_limit": ["해지", "기한의 이익", "상실", "상환", "통지"],
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


def _contains_any(text: str, keywords: list[str]) -> bool:
    normalized = text.lower()
    return any(keyword.lower() in normalized for keyword in keywords)


def analyze_contract_risk(request: TextAnalysisRequest) -> ContractRiskResponse:
    labels = load_rule_file("contract_risk_labels.json")
    matched_items: list[RiskItem] = []
    comparison_summaries: list[str] = []

    for rule in labels:
        if _contains_any(request.content, rule["keywords"]):
            context = _find_context(request.content, rule["keywords"])
            standard_refs = find_standard_clause_references(rule["label"], context)
            comparison = compare_with_standard_terms(rule["label"], context, standard_refs)
            comparison_summaries.append(comparison)
            matched_items.append(
                RiskItem(
                    label=rule["label"],
                    severity=rule["severity"],
                    confidence="high",
                    original_text=context,
                    simplified_text=rule["simplified_text"],
                    why_it_matters=rule["why_it_matters"],
                    must_ask_question=rule["must_ask_question"],
                    senior_action=SENIOR_ACTIONS.get(rule["label"], "중요한 조건은 서면으로 받아 가족이나 신뢰할 수 있는 사람과 함께 확인하세요."),
                    standard_references=standard_refs,
                    comparison_result=comparison,
                )
            )

    overall_risk = _overall_risk(matched_items)
    questions = [item.must_ask_question for item in matched_items[:5]]

    if matched_items:
        summary = EasyExplanation(
            one_line=f"확인할 내용이 {len(matched_items)}개 있습니다.",
            easy_summary="가입 전 다시 물어봐야 할 조건이 보입니다. 표준약관 근거와 함께 확인하세요.",
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


@lru_cache
def load_bank_standard_terms() -> list[dict[str, str]]:
    path = OFFICIAL_DATA_DIR / "ftc_bank_standard_terms.json"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as terms_file:
        return json.load(terms_file)


@lru_cache
def load_unfair_terms_briefing_pages() -> list[dict[str, str]]:
    path = OFFICIAL_DATA_DIR / "ftc_financial_unfair_terms_briefing_pages.json"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as briefing_file:
        return json.load(briefing_file)


def find_standard_clause_references(label: str, context: str, limit: int = 2) -> list[str]:
    query_terms = STANDARD_QUERY_TERMS.get(label, []) + _important_words(context)
    candidates: list[tuple[int, str]] = []

    for document in load_bank_standard_terms():
        title = document.get("title", "은행 표준약관")
        for clause in _split_clauses(document.get("text", "")):
            score = _score_text(clause, query_terms)
            if score <= 0:
                continue
            candidates.append((score, f"{title}: {clause[:260]}"))

    candidates.sort(key=lambda item: item[0], reverse=True)
    return [text for _, text in candidates[:limit]]


def compare_with_standard_terms(label: str, context: str, standard_refs: list[str]) -> str:
    briefing_note = _find_unfair_terms_note(label)
    if not standard_refs:
        return "표준약관 직접 비교 근거를 찾지 못했습니다. 상담사에게 표준약관과 다른 내용인지 확인해야 합니다."

    warning = {
        "auto_renewal": "자동 연장 조건은 소비자가 쉽게 알 수 있게 안내되어야 하므로 해지 방법과 통지 여부를 확인해야 합니다.",
        "excessive_penalty": "해지 비용이나 위약금은 실제 손해보다 과도한지 확인해야 합니다.",
        "third_party_data": "개인정보 제공 동의는 필수인지 선택인지 분리되어야 하며, 거절 가능 여부를 확인해야 합니다.",
        "principal_guarantee_misleading": "예금과 투자상품은 보호 범위가 다르므로 원금 보장 표현을 그대로 믿으면 안 됩니다.",
        "pressure_sales": "충분한 설명과 판단 시간을 주지 않는 권유는 불완전판매 위험 신호입니다.",
        "unclear_fee": "비용·수수료·지연배상금은 소비자가 계약 전 알 수 있어야 합니다.",
        "termination_limit": "해지 제한이나 기한의 이익 상실은 소비자에게 큰 부담이 되므로 발생 조건을 구체적으로 확인해야 합니다.",
    }.get(label, "표준약관과 다른 불리한 조건인지 확인해야 합니다.")

    if briefing_note:
        return f"{warning} 공식 설명회 자료도 금융 분야 불공정약관 유형 확인 필요성을 강조합니다."
    return warning


def _find_unfair_terms_note(label: str) -> str:
    query_terms = STANDARD_QUERY_TERMS.get(label, [])
    best_score = 0
    best_text = ""
    for page in load_unfair_terms_briefing_pages():
        text = page.get("text", "")
        score = _score_text(text, query_terms + ["불공정약관", "약관심사", "표준약관"])
        if score > best_score:
            best_score = score
            best_text = text[:260]
    return best_text


def _split_clauses(text: str) -> list[str]:
    parts = re.split(r"(?=제\d+조\s*\()", text)
    return [part.strip() for part in parts if len(part.strip()) > 40]


def _important_words(text: str) -> list[str]:
    tokens = re.findall(r"[가-힣A-Za-z0-9]{2,}", text)
    stopwords = {"경우", "해당", "약관", "계약", "은행", "고객", "합니다", "있는", "없는"}
    return [token for token in tokens if token not in stopwords][:8]


def _score_text(text: str, query_terms: list[str]) -> int:
    normalized = text.lower()
    return sum(1 for term in query_terms if term and term.lower() in normalized)


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
