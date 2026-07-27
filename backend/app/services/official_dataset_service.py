import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from app.schemas.official_data import OfficialDataset
from app.schemas.official_data import OfficialRecord

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
    if not normalized_query:
        return []

    results: list[tuple[int, OfficialRecord]] = []
    for record in load_official_records():
        if dataset_id and record.dataset_id != dataset_id:
            continue
        haystack = f"{record.title} {record.body} {record.source_title} {' '.join(record.metadata.values())}".lower()
        if normalized_query not in haystack:
            continue
        title_hit = normalized_query in record.title.lower()
        score = (5 if title_hit else 1) + haystack.count(normalized_query)
        results.append((score, record))

    results.sort(key=lambda item: item[0], reverse=True)
    return [record for _, record in results[:limit]]
