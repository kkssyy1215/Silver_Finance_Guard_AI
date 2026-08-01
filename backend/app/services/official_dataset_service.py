import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from app.schemas.official_data import OfficialDataset
from app.schemas.official_data import FinancialTermExplanation
from app.schemas.official_data import OfficialRecord
from app.services.rule_loader import load_rule_file

OFFICIAL_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "official"


@lru_cache
def load_official_dataset_registry() -> list[OfficialDataset]:
    path = OFFICIAL_DATA_DIR / "official_dataset_registry.json"
    with path.open(encoding="utf-8") as registry_file:
        raw_items: list[dict[str, Any]] = json.load(registry_file)
    return [OfficialDataset(**item) for item in raw_items]


def find_official_datasets(query: str = "", status: Optional[str] = None, use_case: Optional[str] = None) -> list[OfficialDataset]:
    datasets = load_official_dataset_registry()
    filtered = []
    normalized_query = query.strip().lower()

    for dataset in datasets:
        if status and dataset.status != status:
            continue
        if use_case and use_case not in dataset.use_cases:
            continue
        if normalized_query:
            haystack = " ".join(
                [
                    dataset.title,
                    dataset.publisher,
                    dataset.portal,
                    dataset.summary,
                    " ".join(dataset.tags),
                    " ".join(dataset.use_cases),
                ]
            ).lower()
            if normalized_query not in haystack:
                continue
        filtered.append(dataset)

    return filtered


SEARCHABLE_DATA_FILES = {
    "FSC_FINANCIAL_TERMS_20260630": "fsc_financial_terms.json",
    "KDIC_DEPOSIT_INSURANCE_TERMS_20220825": "kdic_deposit_insurance_terms.json",
    "KDIC_INSURED_FINANCIAL_COMPANIES_20250930": "kdic_insured_financial_companies.json",
    "KINFA_MAIN_FAQ_20251031": "kinfa_main_faq.json",
    "KINFA_MICROFINANCE_BRANCHES_20251231": "kinfa_microfinance_branches.json",
    "FTC_TELEMARKETING_SELLERS": "ftc_telemarketing_sellers_seoul_gyeonggi.json",
    "KPF_VOICE_PHISHING_NEWS_METADATA_20241231": "kpf_voice_phishing_news_metadata.json",
    "FINANCIAL_CONSUMER_PROTECTION_PDF": "financial_consumer_protection_pdf_pages.json",
    "FTC_FINANCIAL_UNFAIR_TERMS_BRIEFING_20250320": "ftc_financial_unfair_terms_briefing_pages.json",
    "FTC_CONSUMER_COMPLAINT_EXAMPLES_20211227": "ftc_consumer_complaint_examples.json",
    "POST_OFFICE_FINANCIAL_FRAUD_ACCOUNTS_20251231": "post_office_financial_fraud_accounts.json",
    "POLICE_VOICE_PHISHING_STATS_20251231": "police_voice_phishing_stats.json",
    "POLICE_VOICE_PHISHING_REGIONAL_DAMAGE_20251231": "police_voice_phishing_regional_damage.json",
    "FTC_BANK_STANDARD_TERMS_20240927": "ftc_bank_standard_terms.json",
}


@lru_cache
def load_official_records() -> list[OfficialRecord]:
    records: list[OfficialRecord] = []
    for dataset_id, filename in SEARCHABLE_DATA_FILES.items():
        path = OFFICIAL_DATA_DIR / filename
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as data_file:
            rows: list[dict[str, Any]] = json.load(data_file)
        records.extend(_normalize_records(dataset_id, rows))
    return records


def _normalize_records(dataset_id: str, rows: list[dict[str, Any]]) -> list[OfficialRecord]:
    normalizers = {
        "FSC_FINANCIAL_TERMS_20260630": _term_record,
        "KDIC_DEPOSIT_INSURANCE_TERMS_20220825": _term_record,
        "KDIC_INSURED_FINANCIAL_COMPANIES_20250930": _insured_company_record,
        "KINFA_MAIN_FAQ_20251031": _faq_record,
        "KINFA_MICROFINANCE_BRANCHES_20251231": _branch_record,
        "FTC_TELEMARKETING_SELLERS": _telemarketing_record,
        "KPF_VOICE_PHISHING_NEWS_METADATA_20241231": _news_record,
        "FINANCIAL_CONSUMER_PROTECTION_PDF": _pdf_page_record,
        "FTC_FINANCIAL_UNFAIR_TERMS_BRIEFING_20250320": _pdf_page_record,
        "FTC_CONSUMER_COMPLAINT_EXAMPLES_20211227": _complaint_example_record,
        "POST_OFFICE_FINANCIAL_FRAUD_ACCOUNTS_20251231": _fraud_account_record,
        "POLICE_VOICE_PHISHING_STATS_20251231": _police_voice_phishing_stat_record,
        "POLICE_VOICE_PHISHING_REGIONAL_DAMAGE_20251231": _police_regional_damage_record,
        "FTC_BANK_STANDARD_TERMS_20240927": _standard_terms_record,
    }
    normalize = normalizers[dataset_id]
    return [normalize(row) for row in rows]


def _term_record(row: dict[str, Any]) -> OfficialRecord:
    return OfficialRecord(
        dataset_id=row["dataset_id"],
        title=row.get("term", ""),
        body=row.get("definition", ""),
        source_title=row.get("source_title", ""),
        source_url=row.get("source_url"),
        metadata={"type": "term", "source_page": str(row.get("source_page", ""))},
    )


def _faq_record(row: dict[str, Any]) -> OfficialRecord:
    return OfficialRecord(
        dataset_id=row["dataset_id"],
        title=row.get("question", ""),
        body=row.get("answer", ""),
        source_title=row.get("source_title", ""),
        metadata={"type": "faq", "service": row.get("service", ""), "category": row.get("category", "")},
    )


def _branch_record(row: dict[str, Any]) -> OfficialRecord:
    return OfficialRecord(
        dataset_id=row["dataset_id"],
        title=row.get("name", ""),
        body=f"{row.get('region', '')} {row.get('address', '')} {row.get('phone', '')}",
        source_title=row.get("source_title", ""),
        metadata={"type": "branch", "region": row.get("region", ""), "phone": row.get("phone", "")},
    )


def _insured_company_record(row: dict[str, Any]) -> OfficialRecord:
    return OfficialRecord(
        dataset_id=row["dataset_id"],
        title=row.get("name", ""),
        body=f"{row.get('sector', '')} {row.get('address', '')} {row.get('phone', '')} {row.get('website', '')}",
        source_title=row.get("source_title", ""),
        metadata={"type": "insured_company", "sector": row.get("sector", ""), "phone": row.get("phone", "")},
    )


def _telemarketing_record(row: dict[str, Any]) -> OfficialRecord:
    return OfficialRecord(
        dataset_id=row["dataset_id"],
        title=row.get("company", ""),
        body=f"{row.get('agency', '')} {row.get('registration_no', '')} {row.get('phone', '')}",
        source_title="공정거래위원회_전화권유판매사업자정보파일",
        metadata={"type": "telemarketing_seller", "agency": row.get("agency", ""), "status": row.get("status", "")},
    )


def _news_record(row: dict[str, Any]) -> OfficialRecord:
    return OfficialRecord(
        dataset_id=row["dataset_id"],
        title=row.get("title", ""),
        body=f"{row.get('date', '')} {row.get('publisher', '')} {row.get('category_1', '')} {row.get('category_2', '')}",
        source_title=row.get("source_title", ""),
        metadata={"type": "news_metadata", "date": row.get("date", ""), "publisher": row.get("publisher", "")},
    )


def _pdf_page_record(row: dict[str, Any]) -> OfficialRecord:
    return OfficialRecord(
        dataset_id=row["dataset_id"],
        title=f"{row.get('source_title', 'PDF')} {row.get('page', '')}쪽",
        body=row.get("text", ""),
        source_title=row.get("source_title", ""),
        metadata={"type": "pdf_page", "page": str(row.get("page", ""))},
    )


def _complaint_example_record(row: dict[str, Any]) -> OfficialRecord:
    return OfficialRecord(
        dataset_id=row["dataset_id"],
        title=row.get("title", ""),
        body=f"{row.get('content', '')} {row.get('answer', '')}",
        source_title=row.get("source_title", ""),
        metadata={"type": "complaint_example", "case_no": row.get("case_no", "")},
    )


def _fraud_account_record(row: dict[str, Any]) -> OfficialRecord:
    return OfficialRecord(
        dataset_id=row["dataset_id"],
        title=f"{row.get('fraud_type', '')} · {row.get('impersonated_institution', '')}",
        body=(
            f"{row.get('age_group', '')}대 {row.get('gender', '')} "
            f"{row.get('year', '')}-{row.get('month', '')} "
            f"피해금액 {row.get('damage_amount', '')} "
            f"피해구제 사유 {row.get('relief_reason', '')} "
            f"접근매체 {row.get('access_channel', '')}"
        ),
        source_title=row.get("source_title", ""),
        metadata={
            "type": "fraud_account",
            "age_group": row.get("age_group", ""),
            "access_channel": row.get("access_channel", ""),
        },
    )


def _police_voice_phishing_stat_record(row: dict[str, Any]) -> OfficialRecord:
    return OfficialRecord(
        dataset_id=row["dataset_id"],
        title=f"{row.get('year', '')}년 보이스피싱 현황",
        body=(
            f"기관사칭형 발생 {row.get('institution_impersonation_cases', '')}건, "
            f"피해액 {row.get('institution_impersonation_damage_억원', '')}억원, "
            f"검거인원 {row.get('institution_impersonation_arrests', '')}명. "
            f"대출사기형 발생 {row.get('loan_fraud_cases', '')}건, "
            f"피해액 {row.get('loan_fraud_damage_억원', '')}억원, "
            f"검거인원 {row.get('loan_fraud_arrests', '')}명."
        ),
        source_title=row.get("source_title", ""),
        metadata={"type": "voice_phishing_stat", "year": row.get("year", "")},
    )


def _police_regional_damage_record(row: dict[str, Any]) -> OfficialRecord:
    return OfficialRecord(
        dataset_id=row["dataset_id"],
        title=f"{row.get('region', '')} 보이스피싱 피해금액",
        body=(
            f"2023년 {row.get('damage_2023_억원', '')}억원, "
            f"2024년 {row.get('damage_2024_억원', '')}억원, "
            f"2025년 {row.get('damage_2025_억원', '')}억원"
        ),
        source_title=row.get("source_title", ""),
        metadata={"type": "voice_phishing_regional_damage", "region": row.get("region", "")},
    )


def _standard_terms_record(row: dict[str, Any]) -> OfficialRecord:
    return OfficialRecord(
        dataset_id=row["dataset_id"],
        title=row.get("title", ""),
        body=row.get("text", ""),
        source_title=row.get("source_title", ""),
        metadata={"type": "standard_terms", "source_file": row.get("source_file", "")},
    )


def search_official_records(query: str, dataset_id: Optional[str] = None, limit: int = 10) -> list[OfficialRecord]:
    normalized_query = query.strip().lower()
    compact_query = normalized_query.replace(" ", "")
    if not normalized_query:
        return []

    results: list[tuple[int, OfficialRecord]] = []
    for record in load_official_records():
        if dataset_id and record.dataset_id != dataset_id:
            continue
        haystack = f"{record.title} {record.body} {record.source_title} {' '.join(record.metadata.values())}".lower()
        compact_haystack = haystack.replace(" ", "")
        if normalized_query not in haystack and compact_query not in compact_haystack:
            continue
        title_hit = normalized_query in record.title.lower()
        score = (5 if title_hit else 1) + haystack.count(normalized_query)
        results.append((score, record))

    results.sort(key=lambda item: item[0], reverse=True)
    return [record for _, record in results[:limit]]


def search_financial_terms(query: str, limit: int = 8) -> list[FinancialTermExplanation]:
    normalized_query = query.strip().lower()
    compact_query = normalized_query.replace(" ", "")
    if not normalized_query:
        return []

    easy_results = _easy_dictionary_results(query)
    term_records = [
        record
        for record in load_official_records()
        if record.dataset_id in {"FSC_FINANCIAL_TERMS_20260630", "KDIC_DEPOSIT_INSURANCE_TERMS_20220825"}
    ]
    scored_records: list[tuple[int, OfficialRecord]] = []
    for record in term_records:
        title = record.title.lower()
        compact_title = title.replace(" ", "")
        body = record.body.lower()
        compact_body = body.replace(" ", "")
        if compact_query == compact_title:
            score = 1000
        elif compact_query in compact_title or compact_title in compact_query:
            # Prefer short, directly named terms over long titles that merely contain the query.
            title_position_bonus = 18 if compact_title.startswith(compact_query) or compact_title.endswith(compact_query) else 8
            score = 100 + title_position_bonus - max(0, len(compact_title) - len(compact_query)) * 3
        elif normalized_query in body or compact_query in compact_body:
            score = 10
        else:
            continue
        scored_records.append((score, record))

    scored_records.sort(key=lambda item: item[0], reverse=True)
    exact_or_title_matches = [record for score, record in scored_records if score >= 80]
    body_matches = [record for score, record in scored_records if score < 80]

    if easy_results or exact_or_title_matches:
        selected_records = exact_or_title_matches
    else:
        selected_records = body_matches

    explanations = easy_results + [_to_financial_term_explanation(record, compact_query) for record in selected_records[:limit]]
    deduped: list[FinancialTermExplanation] = []
    seen: set[str] = set()
    for item in explanations:
        key = item.term.replace(" ", "").lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:limit]


def _easy_dictionary_results(query: str) -> list[FinancialTermExplanation]:
    normalized_query = query.replace(" ", "").lower()
    results = []
    for item in load_rule_file("easy_language_dictionary.json"):
        normalized_term = item["term"].replace(" ", "").lower()
        # A generic query such as "예금" must not be presented as the exact term "예금자보호".
        if normalized_query != normalized_term:
            continue
        results.append(
            FinancialTermExplanation(
                term=item["term"],
                match_type="exact",
                official_definition="",
                easy_explanation=item["easy"],
                action_tip=item["action"],
                source_title="고령층 쉬운 말 변환 사전",
                source_url=None,
            )
        )
    return results


def _to_financial_term_explanation(record: OfficialRecord, compact_query: str = "") -> FinancialTermExplanation:
    easy_match = _easy_dictionary_match(record.title)
    official_definition = record.body.strip()
    if easy_match:
        easy_explanation = easy_match["easy"]
        action_tip = easy_match["action"]
    else:
        easy_explanation = _simplify_definition(official_definition)
        action_tip = _action_tip_for_term(record.title, official_definition)

    return FinancialTermExplanation(
        term=record.title,
        match_type="exact" if compact_query and record.title.replace(" ", "").lower() == compact_query else "related",
        official_definition=official_definition,
        easy_explanation=easy_explanation,
        action_tip=action_tip,
        source_title=record.source_title,
        source_url=record.source_url,
    )


def _easy_dictionary_match(term: str) -> Optional[dict[str, str]]:
    normalized_term = term.replace(" ", "").lower()
    for item in load_rule_file("easy_language_dictionary.json"):
        dictionary_term = item["term"].replace(" ", "").lower()
        if dictionary_term in normalized_term or normalized_term in dictionary_term:
            return item
    return None


def _simplify_definition(definition: str) -> str:
    if not definition:
        return "공식 설명을 찾았지만 쉬운 설명을 만들기 위한 내용이 부족합니다."
    text = definition.replace("ㆍ", ", ").strip()
    lower_text = text.lower()
    if "부실" in text and ("금융회사" in text or "정리" in text):
        return "문제가 생긴 금융회사를 정리하거나 남은 자산을 관리하기 위해 만든 회사나 제도입니다."
    if "사기이용계좌" in text or "입출금" in text and "금지" in text:
        return "사기 피해가 의심되는 계좌에서 돈이 더 빠져나가지 못하게 막는 조치입니다."
    if ("예금자" in text and "보호" in text) or "예금보호한도" in text or "부보예금" in text:
        return "은행이나 금융회사가 문제가 생겼을 때 일정 한도 안에서 내 예금을 보호해 주는 제도입니다."
    if "청약" in text and ("철회" in text or "취소" in text):
        return "가입한 뒤 정해진 기간 안에 다시 생각해 보고 계약을 취소하는 제도입니다."
    if "위약금" in text or "해지수수료" in text:
        return "계약을 중간에 그만둘 때 내야 할 수 있는 돈입니다."
    if "개인정보" in text or "제3자" in text:
        return "내 이름, 전화번호 같은 정보를 다른 회사에 줄 수 있다는 뜻입니다."
    if "원금" in text and "손실" in text:
        return "처음 넣은 돈보다 적게 돌려받을 수 있다는 뜻입니다."
    if "펀드" in lower_text or "투자" in text or "증권" in text:
        return "돈을 불리기 위해 투자하는 상품이나 제도이며, 손실 가능성과 수수료를 꼭 확인해야 합니다."
    if "대출" in text or "채무" in text or "상환" in text:
        return "돈을 빌리고 갚는 조건과 관련된 용어입니다. 이자, 갚는 날짜, 수수료를 확인해야 합니다."
    first_sentence = re.split(r"[.。]", text)[0].strip()
    if len(first_sentence) > 120:
        first_sentence = first_sentence[:120].rstrip() + "..."
    return first_sentence


def _action_tip_for_term(term: str, definition: str) -> str:
    text = f"{term} {definition}"
    if any(keyword in text for keyword in ["예금", "보호", "보험"]):
        return "내 돈이 보호 대상인지, 한도와 조건을 꼭 확인하세요."
    if any(keyword in text for keyword in ["대출", "이자", "상환", "채무"]):
        return "이자, 갚는 날짜, 중도상환 비용을 숫자로 확인하세요."
    if any(keyword in text for keyword in ["투자", "펀드", "증권", "파생", "손실"]):
        return "원금 손실 가능성과 수수료를 먼저 물어보세요."
    if any(keyword in text for keyword in ["개인정보", "동의", "제공"]):
        return "거절해도 가입할 수 있는 선택 동의인지 확인하세요."
    return "상담사에게 이 용어를 쉬운 말로 다시 설명해 달라고 요청하세요."
