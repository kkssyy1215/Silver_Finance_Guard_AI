from app.schemas.common import RiskLevel
from app.schemas.incident import ActionPlanResponse, ActionStep, RequiredDocument
from app.services.incident_classifier import _extract_facts
from app.services.incident_evidence_service import build_incident_evidence
from app.services.official_faq_service import default_kdic_mistaken_transfer_faq
from app.services.reference_service import references_for
from app.services.risk_detector import DISCLAIMER
from app.services.rule_loader import load_rule_file


def build_action_plan(incident_type: str, content: str = "") -> ActionPlanResponse:
    rules = load_rule_file("incident_rules.json")
    rule = rules.get(incident_type)
    if rule is None:
        return ActionPlanResponse(
            incident_type="unknown",
            urgency_level=RiskLevel.unknown,
            immediate=[ActionStep(order=1, action="상황을 조금 더 알려주세요.", reason="정확한 안내를 위해 사고 유형 확인이 필요합니다.")],
            within_10min=[],
            today=[],
            follow_up=[],
            required_documents=[],
            related_orgs=[],
            references=[],
            faq_matches=[],
            disclaimer=DISCLAIMER,
        )

    facts = _extract_facts(content)
    evidence, urgency_reasons = build_incident_evidence(incident_type, content, facts)

    return ActionPlanResponse(
        incident_type=incident_type,
        urgency_level=rule["urgency_level"],
        immediate=_steps(rule["immediate"]),
        within_10min=_steps(rule["within_10min"]),
        today=_steps(rule["today"]),
        follow_up=_steps(rule["follow_up"]),
        required_documents=[
            RequiredDocument(document_type=item[0], name=item[1], reason=item[2], alternative=item[3])
            for item in rule["documents"]
        ],
        related_orgs=rule["related_orgs"],
        evidence=evidence,
        urgency_reasons=urgency_reasons,
        references=references_for(incident_type),
        faq_matches=default_kdic_mistaken_transfer_faq() if incident_type == "mistaken_transfer" else [],
        disclaimer=DISCLAIMER,
    )


def _steps(raw_steps: list[list[str]]) -> list[ActionStep]:
    return [
        ActionStep(order=index + 1, action=step[0], reason=step[1])
        for index, step in enumerate(raw_steps)
    ]
