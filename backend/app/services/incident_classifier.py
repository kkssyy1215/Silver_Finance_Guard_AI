from __future__ import annotations

import re

from app.schemas.common import Confidence, RiskLevel
from app.schemas.incident import ExtractedFacts, IncidentClassifyResponse
from app.services.official_faq_service import search_kdic_mistaken_transfer_faq
from app.services.reference_service import references_for
from app.services.risk_detector import DISCLAIMER, _contains_any
from app.services.rule_loader import load_rule_file


def classify_incident(content: str) -> IncidentClassifyResponse:
    rules = load_rule_file("incident_rules.json")
    incident_type = "unknown"
    matched_score = 0

    for candidate, rule in rules.items():
        score = sum(1 for keyword in rule["keywords"] if keyword in content)
        if score > matched_score:
            incident_type = candidate
            matched_score = score

    if incident_type == "unknown":
        return IncidentClassifyResponse(
            incident_type="unknown",
            urgency_level=RiskLevel.unknown,
            confidence=Confidence.low,
            extracted_facts=_extract_facts(content),
            risk_signals=[],
            first_action_summary="상황을 조금 더 알려주세요.",
            needs_more_info=True,
            follow_up_questions=["돈을 이미 보내셨나요?", "전화나 문자 지시를 받으셨나요?"],
            references=[],
            faq_matches=[],
            disclaimer=DISCLAIMER,
        )

    rule = rules[incident_type]
    faq_matches = search_kdic_mistaken_transfer_faq(content) if incident_type == "mistaken_transfer" else []
    return IncidentClassifyResponse(
        incident_type=incident_type,
        urgency_level=rule["urgency_level"],
        confidence=Confidence.high if matched_score >= 2 else Confidence.medium,
        extracted_facts=_extract_facts(content),
        risk_signals=rule["risk_signals"],
        first_action_summary=rule["first_action_summary"],
        needs_more_info=False,
        follow_up_questions=[],
        references=references_for(incident_type),
        faq_matches=faq_matches,
        disclaimer=DISCLAIMER,
    )


def _extract_facts(content: str) -> ExtractedFacts:
    amount = _extract_amount(content)
    return ExtractedFacts(
        amount=amount,
        transfer_done=_contains_any(content, ["보냈", "송금", "이체"]),
        cash_delivery=_contains_any(content, ["현금", "전달", "만나서"]),
        app_installed=_contains_any(content, ["앱", "설치", "원격"]),
        personal_info_shared=_contains_any(content, ["신분증", "비밀번호", "인증서", "주민등록번호", "개인정보"]),
        counterparty_claim=_claim(content),
        channel="phone" if _contains_any(content, ["전화", "통화"]) else "message" if _contains_any(content, ["문자", "카톡", "메시지"]) else None,
    )


def _extract_amount(content: str) -> int | None:
    match = re.search(r"(\d+)\s*(만원|원)", content)
    if not match:
        return None
    value = int(match.group(1).replace(",", ""))
    return value * 10000 if match.group(2) == "만원" else value


def _claim(content: str) -> str | None:
    for claim in ["검찰", "경찰", "금감원", "은행", "가족", "자녀"]:
        if claim in content:
            return f"{claim} 사칭 의심"
    return None
