from __future__ import annotations

import re

from app.schemas.common import Confidence, RiskLevel
from app.schemas.incident import ExtractedFacts, IncidentClassifyResponse
from app.services.incident_evidence_service import build_incident_evidence
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
        facts = _extract_facts(content)
        return IncidentClassifyResponse(
            incident_type="unknown",
            urgency_level=RiskLevel.unknown,
            confidence=Confidence.low,
            extracted_facts=facts,
            risk_signals=[],
            first_action_summary="상황을 조금 더 알려주세요.",
            needs_more_info=True,
            follow_up_questions=["돈을 이미 보내셨나요?", "전화나 문자 지시를 받으셨나요?"],
            references=[],
            faq_matches=[],
            disclaimer=DISCLAIMER,
        )

    rule = rules[incident_type]
    facts = _extract_facts(content)
    evidence, urgency_reasons = build_incident_evidence(incident_type, content, facts)
    faq_matches = search_kdic_mistaken_transfer_faq(content) if incident_type == "mistaken_transfer" else []
    return IncidentClassifyResponse(
        incident_type=incident_type,
        urgency_level=rule["urgency_level"],
        confidence=Confidence.high if matched_score >= 2 else Confidence.medium,
        extracted_facts=facts,
        risk_signals=rule["risk_signals"],
        first_action_summary=rule["first_action_summary"],
        needs_more_info=False,
        follow_up_questions=[],
        evidence=evidence,
        urgency_reasons=urgency_reasons,
        references=references_for(incident_type),
        faq_matches=faq_matches,
        disclaimer=DISCLAIMER,
    )


def _extract_facts(content: str) -> ExtractedFacts:
    amount = _extract_amount(content)
    return ExtractedFacts(
        amount=amount,
        transfer_done=_fact_present(content, ["보냈", "송금", "이체"]),
        cash_delivery=_fact_present(content, ["현금", "전달", "만나서"]),
        app_installed=_fact_present(content, ["앱", "설치", "원격"]),
        personal_info_shared=_fact_present(content, ["신분증", "비밀번호", "인증서", "주민등록번호", "개인정보"]),
        counterparty_claim=_claim(content),
        channel="phone" if _contains_any(content, ["전화", "통화"]) else "message" if _contains_any(content, ["문자", "카톡", "메시지"]) else None,
    )


def _fact_present(content: str, keywords: list[str]) -> bool:
    """Detect a fact while ignoring common Korean negation around the keyword."""
    negation = re.compile(r"(?:안|않|못|없|아니|하지\s*않|하지\s*못)")
    for keyword in keywords:
        for match in re.finditer(re.escape(keyword), content):
            before = content[max(0, match.start() - 8) : match.start()]
            after = content[match.end() : match.end() + 32]
            if re.search(r"(제공|공유|전달|알려|수집|요구)\s*(하지\s*않|안)", after):
                continue
            if negation.search(before[-5:]) or negation.search(after):
                continue
            return True
    return False


def _extract_amount(content: str) -> int | None:
    match = re.search(r"(\d[\d,]*)\s*(억|천만원|만원|원)", content)
    if not match:
        return None
    value = int(match.group(1).replace(",", ""))
    unit = match.group(2)
    if unit == "억":
        return value * 100_000_000
    if unit == "천만원":
        return value * 10_000_000
    return value * 10_000 if unit == "만원" else value


def _claim(content: str) -> str | None:
    for claim in ["검찰", "경찰", "금감원", "은행"]:
        if re.search(rf"{claim}(?:이라고|라며|을?\s*사칭|에서\s*전화|이라고\s*전화)", content):
            return f"{claim} 사칭 의심"
    return None
