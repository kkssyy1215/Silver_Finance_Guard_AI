from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.schemas.incident import ExtractedFacts, IncidentEvidence

OFFICIAL_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "official"


@lru_cache
def load_post_office_fraud_accounts() -> list[dict[str, str]]:
    return _load_json("post_office_financial_fraud_accounts.json")


@lru_cache
def load_police_voice_phishing_stats() -> list[dict[str, str]]:
    return _load_json("police_voice_phishing_stats.json")


@lru_cache
def load_police_regional_damage() -> list[dict[str, str]]:
    return _load_json("police_voice_phishing_regional_damage.json")


def build_incident_evidence(incident_type: str, content: str, facts: ExtractedFacts) -> tuple[list[IncidentEvidence], list[str]]:
    if incident_type != "voice_phishing":
        return [], []

    evidence = [
        _latest_police_trend_evidence(),
        _fraud_pattern_evidence(content=content, facts=facts),
        _regional_damage_evidence(),
    ]
    evidence = [item for item in evidence if item is not None]
    return evidence, _urgency_reasons(content=content, facts=facts)


def _load_json(filename: str) -> list[dict[str, str]]:
    path = OFFICIAL_DATA_DIR / filename
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as data_file:
        return json.load(data_file)


def _latest_police_trend_evidence() -> IncidentEvidence | None:
    stats = load_police_voice_phishing_stats()
    if not stats:
        return None
    latest = max(stats, key=lambda row: row.get("year", ""))
    return IncidentEvidence(
        title=f"{latest.get('year')}년 보이스피싱 공식 통계",
        summary=(
            f"경찰청 통계 기준 기관사칭형은 {latest.get('institution_impersonation_cases')}건, "
            f"피해액 {latest.get('institution_impersonation_damage_억원')}억원입니다. "
            f"대출사기형은 {latest.get('loan_fraud_cases')}건, 피해액 {latest.get('loan_fraud_damage_억원')}억원입니다."
        ),
        source_title=latest.get("source_title", "경찰청_보이스피싱 현황_20251231"),
        matched_fields=["기관사칭형", "대출사기형", "피해액", "발생건수"],
    )


def _fraud_pattern_evidence(content: str, facts: ExtractedFacts) -> IncidentEvidence | None:
    rows = load_post_office_fraud_accounts()
    if not rows:
        return None
    matches: list[dict[str, str]] = []
    for row in rows:
        score = 0
        if facts.channel == "phone" and row.get("access_channel") == "전화":
            score += 2
        if facts.counterparty_claim and _claim_keyword(facts.counterparty_claim) in row.get("impersonated_institution", ""):
            score += 2
        if any(keyword in content for keyword in ["대출", "수수료", "보증료"]) and "대출" in row.get("fraud_type", ""):
            score += 2
        if any(keyword in content for keyword in ["투자", "수익", "코인", "주식"]) and "투자" in row.get("fraud_type", ""):
            score += 2
        if score > 0:
            matches.append({**row, "_score": str(score)})

    if not matches:
        matches = rows[:5]

    matches.sort(key=lambda row: int(row.get("_score", "0")), reverse=True)
    top = matches[:5]
    common_types = _top_counts(row.get("fraud_type", "확인 필요") for row in top)
    common_channels = _top_counts(row.get("access_channel", "확인 필요") for row in top)
    common_institutions = _top_counts(row.get("impersonated_institution", "확인 필요") for row in top)
    return IncidentEvidence(
        title="우체국 금융사기 사례와 유사한 패턴",
        summary=(
            f"유사 사례에서 많이 보이는 사기유형은 {common_types}, 접근매체는 {common_channels}, "
            f"사칭기관은 {common_institutions}입니다."
        ),
        source_title="우체국금융개발원_우체국 금융 사기계좌 정보_20251231",
        matched_fields=["사기유형", "사칭기관", "접근매체", "피해금액"],
    )


def _regional_damage_evidence() -> IncidentEvidence | None:
    rows = load_police_regional_damage()
    if not rows:
        return None
    total_2025 = sum(_to_int(row.get("damage_2025_억원", "0")) for row in rows)
    top_regions = sorted(rows, key=lambda row: _to_int(row.get("damage_2025_억원", "0")), reverse=True)[:3]
    region_text = ", ".join(f"{row.get('region')} {row.get('damage_2025_억원')}억원" for row in top_regions)
    return IncidentEvidence(
        title="지역별 보이스피싱 피해금액 근거",
        summary=f"경찰청 시도청별 자료 기준 2025년 피해금액 합계는 약 {total_2025:,}억원이며, 피해금액 상위 지역은 {region_text}입니다.",
        source_title="경찰청_전화금융사기_보이스피싱 시도청별 피해금액 현황_20251231",
        matched_fields=["시도청", "2025년 피해금액"],
    )


def _urgency_reasons(content: str, facts: ExtractedFacts) -> list[str]:
    reasons = ["보이스피싱은 송금 직후 지급정지 요청이 늦어질수록 피해금 회수가 어려워질 수 있습니다."]
    if facts.transfer_done:
        reasons.append("이미 이체 또는 송금이 이루어진 정황이 있어 은행 지급정지 요청이 최우선입니다.")
    if facts.app_installed:
        reasons.append("원격제어 앱이나 의심 앱 설치 정황이 있어 추가 이체와 개인정보 탈취 위험이 있습니다.")
    if facts.cash_delivery:
        reasons.append("현금 전달 정황은 대면편취형 피해 가능성이 있어 즉시 112 신고와 증거 보존이 필요합니다.")
    if facts.personal_info_shared:
        reasons.append("신분증·비밀번호·인증서 등 개인정보 공유 정황이 있어 계좌·카드 추가 피해 방지가 필요합니다.")
    return reasons


def _top_counts(values) -> str:
    counts: dict[str, int] = {}
    for value in values:
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    if not counts:
        return "확인 필요"
    return ", ".join(f"{value}({count}건)" for value, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:3])


def _claim_keyword(claim: str) -> str:
    for keyword in ["검찰", "경찰", "금감원", "은행", "가족", "자녀"]:
        if keyword in claim:
            return keyword
    return claim


def _to_int(value: str) -> int:
    try:
        return int(str(value).replace(",", "").strip())
    except ValueError:
        return 0
