from __future__ import annotations

import csv
import json
import re
import time
import zipfile
from datetime import date
from html import unescape
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from pypdf import PdfReader

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_INBOX = PROJECT_ROOT / "data_inbox"
OFFICIAL_DATA_DIR = PROJECT_ROOT / "backend" / "app" / "data" / "official"
REGISTRY_PATH = OFFICIAL_DATA_DIR / "official_dataset_registry.json"

FSC_TERMS_URL = "https://www.fsc.go.kr/in090301"
USER_AGENT = "SilverFinanceGuardAI/0.1 educational public-data ingestion"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    for encoding in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            with path.open(encoding=encoding, newline="") as csv_file:
                return [dict(row) for row in csv.DictReader(csv_file)]
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("csv", b"", 0, 1, f"Cannot decode {path}")


def write_json(path: Path, rows: list[dict[str, Any]] | dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as json_file:
        json.dump(rows, json_file, ensure_ascii=False, indent=2)
        json_file.write("\n")


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = unescape(value)
    value = value.replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def field(row: dict[str, str], name: str) -> str:
    value = row.get(name)
    return str(value).strip() if value is not None else ""


def find_inbox_file(stem: str, suffix: str = ".csv") -> Path:
    matches = [path for path in DATA_INBOX.glob(f"*{stem}*{suffix}")]
    if not matches:
        raise FileNotFoundError(f"data_inbox에서 '{stem}' 파일을 찾지 못했습니다.")
    return matches[0]


def ingest_kinfa_faq() -> int:
    source_path = find_inbox_file("대표홈페이지 자주하는질문")
    rows = read_csv_rows(source_path)
    normalized = [
        {
            "dataset_id": "KINFA_MAIN_FAQ_20251031",
            "category": row.get("카테고리", "").strip(),
            "service": row.get("구분", "").strip(),
            "question": row.get("자주하는 질문", "").strip(),
            "answer": row.get("질문답변", "").strip(),
            "source_title": "서민금융진흥원_대표홈페이지 자주하는질문_20251031",
            "source_file": source_path.name,
        }
        for row in rows
        if row.get("자주하는 질문") and row.get("질문답변")
    ]
    write_json(OFFICIAL_DATA_DIR / "kinfa_main_faq.json", normalized)
    return len(normalized)


def ingest_kdic_terms() -> int:
    source_path = find_inbox_file("예금보험 용어사전")
    rows = read_csv_rows(source_path)
    normalized = [
        {
            "dataset_id": "KDIC_DEPOSIT_INSURANCE_TERMS_20220825",
            "term": row.get("용어", "").strip(),
            "definition": row.get("내용", "").strip(),
            "source_title": "예금보험공사_예금보험 용어사전_20220825",
            "source_file": source_path.name,
        }
        for row in rows
        if row.get("용어") and row.get("내용")
    ]
    write_json(OFFICIAL_DATA_DIR / "kdic_deposit_insurance_terms.json", normalized)
    return len(normalized)


def ingest_microfinance_branches() -> int:
    source_path = find_inbox_file("미소금융지점 현황")
    rows = read_csv_rows(source_path)
    normalized = [
        {
            "dataset_id": "KINFA_MICROFINANCE_BRANCHES_20251231",
            "branch_type": row.get("구분", "").strip(),
            "region": row.get("지역", "").strip(),
            "name": row.get("지점명", "").strip(),
            "address": row.get("주소", "").strip(),
            "phone": row.get("전화번호", "").strip(),
            "source_title": "서민금융진흥원 미소금융지점 현황_20251231",
            "source_file": source_path.name,
        }
        for row in rows
        if row.get("지점명") and row.get("주소")
    ]
    write_json(OFFICIAL_DATA_DIR / "kinfa_microfinance_branches.json", normalized)
    return len(normalized)


def ingest_microfinance_age_stats() -> int:
    source_path = find_inbox_file("미소금융 연령대별 대출실적")
    rows = read_csv_rows(source_path)
    normalized = [
        {
            "dataset_id": "KINFA_MICROFINANCE_AGE_LOAN_20241231",
            "institution": row.get("기관명", "").strip(),
            "age_group": row.get("연령대", "").strip(),
            "year": row.get("년도", "").strip(),
            "amount_억원": row.get("금액(억원)", "").strip(),
            "count_건": row.get("건수(건)", "").strip(),
            "source_title": "서민금융진흥원_미소금융 연령대별 대출실적 현황_20241231",
            "source_file": source_path.name,
        }
        for row in rows
        if row.get("연령대") and row.get("년도")
    ]
    write_json(OFFICIAL_DATA_DIR / "kinfa_microfinance_age_loan_stats.json", normalized)
    return len(normalized)


def ingest_telemarketing_sellers() -> int:
    rows: list[dict[str, str]] = []
    for source_path in sorted(DATA_INBOX.glob("*전화권유판매사업자*.csv")):
        for row in read_csv_rows(source_path):
            rows.append(
                {
                    "dataset_id": "FTC_TELEMARKETING_SELLERS",
                    "registration_no": field(row, "전화판매번호"),
                    "agency": field(row, "신고기관명"),
                    "company": field(row, "상호"),
                    "business_registration_no": field(row, "사업자등록번호"),
                    "corporation_type": field(row, "법인여부"),
                    "representative": field(row, "대표자명"),
                    "phone": field(row, "전화번호"),
                    "status": field(row, "영업상태"),
                    "source_file": source_path.name,
                }
            )
    normalized = [row for row in rows if row["company"]]
    write_json(OFFICIAL_DATA_DIR / "ftc_telemarketing_sellers_seoul_gyeonggi.json", normalized)
    return len(normalized)


def ingest_voice_phishing_news() -> int:
    source_path = find_inbox_file("보이스피싱")
    rows = read_csv_rows(source_path)
    normalized = [
        {
            "dataset_id": "KPF_VOICE_PHISHING_NEWS_METADATA_20241231",
            "date": row.get("일자", "").strip(),
            "publisher": row.get("언론사", "").strip(),
            "title": row.get("제목", "").strip(),
            "category_1": row.get("통합 분류1", "").strip(),
            "category_2": row.get("통합 분류2", "").strip(),
            "category_3": row.get("통합 분류3", "").strip(),
            "people": row.get("개체명(인물)", "").strip(),
            "regions": row.get("개체명(지역)", "").strip(),
            "source_title": "한국언론진흥재단_뉴스빅데이터_메타데이터_보이스피싱_20241231",
            "source_file": source_path.name,
        }
        for row in rows
        if row.get("제목")
    ]
    write_json(OFFICIAL_DATA_DIR / "kpf_voice_phishing_news_metadata.json", normalized)
    return len(normalized)


def ingest_financial_consumer_protection_pdf() -> int:
    matches = list(DATA_INBOX.glob("*금융소비자 보호*.pdf"))
    if not matches:
        return 0
    source_path = matches[0]
    reader = PdfReader(str(source_path))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = clean_text(page.extract_text() or "")
        if text:
            pages.append(
                {
                    "dataset_id": "FINANCIAL_CONSUMER_PROTECTION_PDF",
                    "page": index,
                    "text": text,
                    "source_title": "금융소비자 보호.pdf",
                    "source_file": source_path.name,
                }
            )
    write_json(OFFICIAL_DATA_DIR / "financial_consumer_protection_pdf_pages.json", pages)
    return len(pages)


def ingest_unfair_terms_briefing_pdf() -> int:
    matches = list(DATA_INBOX.glob("R2503897*.pdf"))
    if not matches:
        return 0
    source_path = matches[0]
    reader = PdfReader(str(source_path))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = clean_text(page.extract_text() or "")
        if text:
            pages.append(
                {
                    "dataset_id": "FTC_FINANCIAL_UNFAIR_TERMS_BRIEFING_20250320",
                    "page": index,
                    "text": text,
                    "source_title": "금융 분야 불공정약관 개선 공동 설명회 자료",
                    "source_file": source_path.name,
                }
            )
    write_json(OFFICIAL_DATA_DIR / "ftc_financial_unfair_terms_briefing_pages.json", pages)
    return len(pages)


def ingest_consumer_complaint_examples() -> int:
    source_path = find_inbox_file("소비자 민원학습데이터 모범상담 사례")
    rows = read_csv_rows(source_path)
    normalized = [
        {
            "dataset_id": "FTC_CONSUMER_COMPLAINT_EXAMPLES_20211227",
            "case_no": field(row, "사건번호(ACCIDENT_NO)"),
            "title": field(row, "사건제목(ACCIDENT_TITLE)"),
            "content": field(row, "사건내용(ACCIDENT_CONTENT)"),
            "answer": field(row, "답변내용(ANS_CONTENT)"),
            "source_title": "공정거래위원회_소비자 민원학습데이터 모범상담 사례_20211227",
            "source_file": source_path.name,
        }
        for row in rows
        if field(row, "사건제목(ACCIDENT_TITLE)") and field(row, "답변내용(ANS_CONTENT)")
    ]
    write_json(OFFICIAL_DATA_DIR / "ftc_consumer_complaint_examples.json", normalized)
    return len(normalized)


def ingest_post_office_fraud_accounts() -> int:
    source_path = find_inbox_file("우체국 금융 사기계좌")
    rows = read_csv_rows(source_path)
    normalized = [
        {
            "dataset_id": "POST_OFFICE_FINANCIAL_FRAUD_ACCOUNTS_20251231",
            "age_group": field(row, "연령대"),
            "gender": field(row, "피해자 성별"),
            "year": field(row, "최초 접수년"),
            "month": field(row, "최초 접수월"),
            "damage_amount": field(row, " 피해자계좌_피해(송금)액 "),
            "fraud_type": field(row, "사기유형"),
            "impersonated_institution": field(row, "사칭기관"),
            "relief_reason": field(row, "피해구제 신청사유"),
            "access_channel": field(row, "접근매체"),
            "source_title": "우체국금융개발원_우체국 금융 사기계좌 정보_20251231",
            "source_file": source_path.name,
        }
        for row in rows
        if field(row, "사기유형") or field(row, "사칭기관")
    ]
    write_json(OFFICIAL_DATA_DIR / "post_office_financial_fraud_accounts.json", normalized)
    return len(normalized)


def ingest_police_voice_phishing_stats() -> int:
    source_path = find_inbox_file("경찰청_보이스피싱 현황")
    rows = read_csv_rows(source_path)
    normalized = [
        {
            "dataset_id": "POLICE_VOICE_PHISHING_STATS_20251231",
            "year": field(row, "구분"),
            "institution_impersonation_cases": field(row, "기관사칭형_발생건수"),
            "institution_impersonation_damage_억원": field(row, "기관사칭형_피해액_억원"),
            "institution_impersonation_arrests": field(row, "기관사칭형_검거인원"),
            "loan_fraud_cases": field(row, "대출사기형_발생건수"),
            "loan_fraud_damage_억원": field(row, "대출사기형_피해액_억원"),
            "loan_fraud_arrests": field(row, "대출사기형_검거인원"),
            "source_title": "경찰청_보이스피싱 현황_20251231",
            "source_file": source_path.name,
        }
        for row in rows
        if field(row, "구분")
    ]
    write_json(OFFICIAL_DATA_DIR / "police_voice_phishing_stats.json", normalized)
    return len(normalized)


def ingest_police_voice_phishing_regional_damage() -> int:
    source_path = find_inbox_file("시도청별 피해금액")
    rows = read_csv_rows(source_path)
    normalized = [
        {
            "dataset_id": "POLICE_VOICE_PHISHING_REGIONAL_DAMAGE_20251231",
            "region": field(row, "시도청"),
            "damage_2023_억원": field(row, "2023년"),
            "damage_2024_억원": field(row, "2024년"),
            "damage_2025_억원": field(row, "2025년"),
            "source_title": "경찰청_전화금융사기_보이스피싱 시도청별 피해금액 현황_20251231",
            "source_file": source_path.name,
        }
        for row in rows
        if field(row, "시도청")
    ]
    write_json(OFFICIAL_DATA_DIR / "police_voice_phishing_regional_damage.json", normalized)
    return len(normalized)


def ingest_kdic_insured_companies() -> int:
    source_path = find_inbox_file("부보금융회사 목록")
    rows = read_csv_rows(source_path)
    normalized = [
        {
            "dataset_id": "KDIC_INSURED_FINANCIAL_COMPANIES_20250930",
            "sector": field(row, "금융권"),
            "name": field(row, "기관명"),
            "address": field(row, "주소"),
            "phone": field(row, "연락처"),
            "website": field(row, "사이트(URL)"),
            "source_title": "예금보험공사_부보금융회사 목록_20250930",
            "source_file": source_path.name,
        }
        for row in rows
        if field(row, "기관명")
    ]
    write_json(OFFICIAL_DATA_DIR / "kdic_insured_financial_companies.json", normalized)
    return len(normalized)


def extract_hwpx_text(path: Path) -> str:
    paragraphs: list[str] = []
    with zipfile.ZipFile(path) as archive:
        section_names = sorted(name for name in archive.namelist() if name.startswith("Contents/section") and name.endswith(".xml"))
        for name in section_names:
            root = ElementTree.fromstring(archive.read(name))
            for node in root.iter():
                if node.tag.endswith("}t") or node.tag == "t":
                    if node.text:
                        paragraphs.append(node.text)
    return clean_text(" ".join(paragraphs))


def ingest_bank_standard_terms() -> int:
    documents = []
    for source_path in sorted(DATA_INBOX.glob("*.hwpx")):
        title = source_path.stem
        text = extract_hwpx_text(source_path)
        if not text:
            continue
        documents.append(
            {
                "dataset_id": "FTC_BANK_STANDARD_TERMS_20240927",
                "title": title,
                "text": text,
                "source_title": title,
                "source_file": source_path.name,
            }
        )
    write_json(OFFICIAL_DATA_DIR / "ftc_bank_standard_terms.json", documents)
    return len(documents)


def fetch_fsc_page(page: int) -> str:
    url = f"{FSC_TERMS_URL}?curPage={page}"
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", "replace")


def ingest_fsc_financial_terms() -> int:
    terms: list[dict[str, Any]] = []
    link_pattern = re.compile(r"href=\"(?P<href>\./in090301/view\?dicId=\d+&curPage=\d+)\"[^>]*>(?P<title>.*?)</a>", re.S)
    desc_pattern = re.compile(r"<div class=\"info2\">\s*(?P<desc>.*?)</div>", re.S)

    for page in range(1, 24):
        html = fetch_fsc_page(page)
        link_matches = list(link_pattern.finditer(html))
        for index, link_match in enumerate(link_matches):
            term = clean_text(link_match.group("title"))
            if not term:
                continue
            href = link_match.group("href").replace("./", "/")
            dic_id_match = re.search(r"dicId=(\d+)", href)
            block_end = link_matches[index + 1].start() if index + 1 < len(link_matches) else html.find("</ul>", link_match.end())
            block = html[link_match.end() : block_end if block_end != -1 else link_match.end() + 4000]
            desc_match = desc_pattern.search(block)
            terms.append(
                {
                    "dataset_id": "FSC_FINANCIAL_TERMS_20260630",
                    "term": term,
                    "definition": clean_text(desc_match.group("desc") if desc_match else ""),
                    "source_title": "금융위원회_금융용어사전_20260630",
                    "source_url": f"https://www.fsc.go.kr{href}",
                    "source_id": dic_id_match.group(1) if dic_id_match else "",
                    "source_page": page,
                }
            )
        time.sleep(0.2)

    write_json(OFFICIAL_DATA_DIR / "fsc_financial_terms.json", terms)
    return len(terms)


def update_registry(row_counts: dict[str, int]) -> None:
    with REGISTRY_PATH.open(encoding="utf-8") as registry_file:
        registry: list[dict[str, Any]] = json.load(registry_file)

    local_paths = {
        "KINFA_MAIN_FAQ_20251031": "backend/app/data/official/kinfa_main_faq.json",
        "FSC_FINANCIAL_TERMS_20260630": "backend/app/data/official/fsc_financial_terms.json",
        "KDIC_DEPOSIT_INSURANCE_TERMS_20220825": "backend/app/data/official/kdic_deposit_insurance_terms.json",
        "KINFA_MICROFINANCE_BRANCHES_20251231": "backend/app/data/official/kinfa_microfinance_branches.json",
        "KINFA_MICROFINANCE_AGE_LOAN_20241231": "backend/app/data/official/kinfa_microfinance_age_loan_stats.json",
        "FTC_TELEMARKETING_SELLERS": "backend/app/data/official/ftc_telemarketing_sellers_seoul_gyeonggi.json",
        "KPF_VOICE_PHISHING_NEWS_METADATA_20241231": "backend/app/data/official/kpf_voice_phishing_news_metadata.json",
        "FINANCIAL_CONSUMER_PROTECTION_PDF": "backend/app/data/official/financial_consumer_protection_pdf_pages.json",
        "FTC_FINANCIAL_UNFAIR_TERMS_BRIEFING_20250320": "backend/app/data/official/ftc_financial_unfair_terms_briefing_pages.json",
        "FTC_CONSUMER_COMPLAINT_EXAMPLES_20211227": "backend/app/data/official/ftc_consumer_complaint_examples.json",
        "POST_OFFICE_FINANCIAL_FRAUD_ACCOUNTS_20251231": "backend/app/data/official/post_office_financial_fraud_accounts.json",
        "POLICE_VOICE_PHISHING_STATS_20251231": "backend/app/data/official/police_voice_phishing_stats.json",
        "POLICE_VOICE_PHISHING_REGIONAL_DAMAGE_20251231": "backend/app/data/official/police_voice_phishing_regional_damage.json",
        "KDIC_INSURED_FINANCIAL_COMPANIES_20250930": "backend/app/data/official/kdic_insured_financial_companies.json",
        "FTC_BANK_STANDARD_TERMS_20240927": "backend/app/data/official/ftc_bank_standard_terms.json",
    }

    registry = [
        item
        for item in registry
        if item["dataset_id"] != "FSC_DEPOSIT_INSURANCE_COMPANY_PRODUCT_API"
    ]

    for item in registry:
        dataset_id = item["dataset_id"]
        if dataset_id in local_paths:
            item["status"] = "imported"
            item["local_path"] = local_paths[dataset_id]
            if dataset_id in row_counts:
                item["row_count"] = row_counts[dataset_id]

    if "FINANCIAL_CONSUMER_PROTECTION_PDF" not in {item["dataset_id"] for item in registry}:
        registry.append(
            {
                "dataset_id": "FINANCIAL_CONSUMER_PROTECTION_PDF",
                "title": "금융소비자 보호.pdf",
                "publisher": "공식 자료",
                "portal": "사용자 제공 공식 PDF",
                "url": "",
                "format": "PDF",
                "row_count": row_counts.get("FINANCIAL_CONSUMER_PROTECTION_PDF", 0),
                "license": "사용자 제공 공식 자료",
                "fee": "무료",
                "modified_at": None,
                "status": "imported",
                "local_path": local_paths["FINANCIAL_CONSUMER_PROTECTION_PDF"],
                "tags": ["금융소비자보호", "설명의무", "민원", "피해예방"],
                "use_cases": ["procedure_guidance", "complaint_draft", "explanation_duty"],
                "summary": "금융소비자 보호 관련 PDF를 페이지 단위 텍스트로 추출해 설명의무, 민원 초안, 절차 안내의 근거 자료로 활용합니다.",
            }
        )

    existing_ids = {item["dataset_id"] for item in registry}
    additions = [
        {
            "dataset_id": "FTC_FINANCIAL_UNFAIR_TERMS_BRIEFING_20250320",
            "title": "금융 분야 불공정약관 개선 공동 설명회 자료",
            "publisher": "공정거래위원회·금융감독원",
            "portal": "KDI 경제정보센터",
            "url": "https://eiec.kdi.re.kr/policy/materialView.do?num=264605&pg=&pp=20&topic=L",
            "format": "PDF",
            "row_count": row_counts.get("FTC_FINANCIAL_UNFAIR_TERMS_BRIEFING_20250320", 0),
            "license": "공식 공개 자료",
            "fee": "무료",
            "modified_at": "2025-03-20",
            "status": "imported",
            "local_path": local_paths["FTC_FINANCIAL_UNFAIR_TERMS_BRIEFING_20250320"],
            "tags": ["불공정약관", "금융약관", "약관심사", "표준약관", "독소조항"],
            "use_cases": ["dark_pattern_detection", "contract_comparison", "risk_dictionary"],
            "summary": "금융 분야 약관 심사 제도와 불공정약관 유형을 설명하는 공식 자료로, 독소조항 탐지 규칙 고도화에 활용합니다.",
        },
        {
            "dataset_id": "FTC_CONSUMER_COMPLAINT_EXAMPLES_20211227",
            "title": "공정거래위원회_소비자 민원학습데이터 모범상담 사례_20211227",
            "publisher": "공정거래위원회",
            "portal": "공공데이터포털",
            "url": "https://www.data.go.kr/data/15098335/fileData.do",
            "format": "CSV",
            "row_count": row_counts.get("FTC_CONSUMER_COMPLAINT_EXAMPLES_20211227", 0),
            "license": "이용허락범위 제한 없음",
            "fee": "무료",
            "modified_at": "2025-08-01",
            "status": "imported",
            "local_path": local_paths["FTC_CONSUMER_COMPLAINT_EXAMPLES_20211227"],
            "tags": ["소비자민원", "모범상담", "피해구제", "민원초안", "보험"],
            "use_cases": ["complaint_draft", "case_reference", "answer_style"],
            "summary": "사건 제목, 사건 내용, 답변 내용으로 구성된 소비자 모범상담 사례로, 유사 사례 검색과 민원 초안 작성에 활용합니다.",
        },
        {
            "dataset_id": "POST_OFFICE_FINANCIAL_FRAUD_ACCOUNTS_20251231",
            "title": "우체국금융개발원_우체국 금융 사기계좌 정보_20251231",
            "publisher": "우체국금융개발원",
            "portal": "공공데이터포털",
            "url": "https://www.data.go.kr/data/15021794/fileData.do?recommendDataYn=Y",
            "format": "CSV",
            "row_count": row_counts.get("POST_OFFICE_FINANCIAL_FRAUD_ACCOUNTS_20251231", 0),
            "license": "공공데이터포털 파일데이터",
            "fee": "무료",
            "modified_at": "2026-01-23",
            "status": "imported",
            "local_path": local_paths["POST_OFFICE_FINANCIAL_FRAUD_ACCOUNTS_20251231"],
            "tags": ["금융사기", "보이스피싱", "피해금액", "연령대", "사칭기관"],
            "use_cases": ["voice_phishing_trend", "senior_risk_analysis", "incident_classification"],
            "summary": "전기통신금융사기 피해 사례의 연령대, 성별, 피해금액, 사기유형, 사칭기관, 접근매체 정보를 제공합니다.",
        },
        {
            "dataset_id": "POLICE_VOICE_PHISHING_STATS_20251231",
            "title": "경찰청_보이스피싱 현황_20251231",
            "publisher": "경찰청",
            "portal": "공공데이터포털",
            "url": "https://www.data.go.kr/tcs/dss/selectDataSetList.do?keyword=%EB%B3%B4%EC%9D%B4%EC%8A%A4%ED%94%BC%EC%8B%B1",
            "format": "CSV",
            "row_count": row_counts.get("POLICE_VOICE_PHISHING_STATS_20251231", 0),
            "license": "공공데이터포털 파일데이터",
            "fee": "무료",
            "modified_at": "2026-01-21",
            "status": "imported",
            "local_path": local_paths["POLICE_VOICE_PHISHING_STATS_20251231"],
            "tags": ["보이스피싱", "기관사칭형", "대출사기형", "피해액", "발생건수"],
            "use_cases": ["voice_phishing_trend", "demo_statistics", "problem_definition"],
            "summary": "연도별 기관사칭형·대출사기형 보이스피싱 발생건수, 피해액, 검거인원 통계입니다.",
        },
        {
            "dataset_id": "POLICE_VOICE_PHISHING_REGIONAL_DAMAGE_20251231",
            "title": "경찰청_전화금융사기_보이스피싱 시도청별 피해금액 현황_20251231",
            "publisher": "경찰청",
            "portal": "공공데이터포털",
            "url": "https://www.data.go.kr/tcs/dss/selectDataSetList.do?keyword=%EB%B3%B4%EC%9D%B4%EC%8A%A4%ED%94%BC%EC%8B%B1",
            "format": "CSV",
            "row_count": row_counts.get("POLICE_VOICE_PHISHING_REGIONAL_DAMAGE_20251231", 0),
            "license": "공공데이터포털 파일데이터",
            "fee": "무료",
            "modified_at": "2026-01-21",
            "status": "imported",
            "local_path": local_paths["POLICE_VOICE_PHISHING_REGIONAL_DAMAGE_20251231"],
            "tags": ["보이스피싱", "지역별", "피해금액", "시도청", "통계"],
            "use_cases": ["voice_phishing_trend", "demo_statistics", "regional_analysis"],
            "summary": "시도청별 보이스피싱 피해금액을 연도별로 제공하여 지역별 피해 규모 분석에 활용합니다.",
        },
        {
            "dataset_id": "KDIC_INSURED_FINANCIAL_COMPANIES_20250930",
            "title": "예금보험공사_부보금융회사 목록_20250930",
            "publisher": "예금보험공사",
            "portal": "공공데이터포털",
            "url": "https://www.data.go.kr/tcs/dss/selectDataSetList.do?conditionType=search&dType=&keyword=&org=%EC%98%88%EA%B8%88%EB%B3%B4%ED%97%98%EA%B3%B5%EC%82%AC&orgFilter=%EC%98%88%EA%B8%88%EB%B3%B4%ED%97%98%EA%B3%B5%EC%82%AC&orgFullName=%EC%98%88%EA%B8%88%EB%B3%B4%ED%97%98%EA%B3%B5%EC%82%AC",
            "format": "CSV",
            "row_count": row_counts.get("KDIC_INSURED_FINANCIAL_COMPANIES_20250930", 0),
            "license": "이용허락범위 제한 없음",
            "fee": "무료",
            "modified_at": "2026-07-22",
            "status": "imported",
            "local_path": local_paths["KDIC_INSURED_FINANCIAL_COMPANIES_20250930"],
            "tags": ["부보금융회사", "예금자보호", "금융회사", "주소", "홈페이지"],
            "use_cases": ["deposit_protection", "institution_lookup", "product_precheck"],
            "summary": "예금보험 적용 대상 금융회사 목록으로, 기관명·주소·연락처·홈페이지 확인에 활용합니다.",
        },
        {
            "dataset_id": "FTC_BANK_STANDARD_TERMS_20240927",
            "title": "공정거래위원회 은행 표준약관 3종_20240927",
            "publisher": "공정거래위원회",
            "portal": "공정거래위원회",
            "url": "https://www.ftc.go.kr/www/selectBbsNttList.do?bordCd=201&key=202",
            "format": "HWPX",
            "row_count": row_counts.get("FTC_BANK_STANDARD_TERMS_20240927", 0),
            "license": "공식 공개 표준약관",
            "fee": "무료",
            "modified_at": "2024-09-27",
            "status": "imported",
            "local_path": local_paths["FTC_BANK_STANDARD_TERMS_20240927"],
            "tags": ["표준약관", "예금거래", "은행여신", "가계대출", "기업대출"],
            "use_cases": ["contract_comparison", "dark_pattern_detection", "standard_terms_reference"],
            "summary": "예금거래기본약관, 은행여신거래기본약관 가계용·기업용을 텍스트로 추출해 약관 비교 기준으로 활용합니다.",
        },
    ]
    registry.extend(item for item in additions if item["dataset_id"] not in existing_ids)

    write_json(REGISTRY_PATH, registry)


def main() -> None:
    row_counts = {
        "KINFA_MAIN_FAQ_20251031": ingest_kinfa_faq(),
        "KDIC_DEPOSIT_INSURANCE_TERMS_20220825": ingest_kdic_terms(),
        "KINFA_MICROFINANCE_BRANCHES_20251231": ingest_microfinance_branches(),
        "KINFA_MICROFINANCE_AGE_LOAN_20241231": ingest_microfinance_age_stats(),
        "FTC_TELEMARKETING_SELLERS": ingest_telemarketing_sellers(),
        "KPF_VOICE_PHISHING_NEWS_METADATA_20241231": ingest_voice_phishing_news(),
        "FINANCIAL_CONSUMER_PROTECTION_PDF": ingest_financial_consumer_protection_pdf(),
        "FTC_FINANCIAL_UNFAIR_TERMS_BRIEFING_20250320": ingest_unfair_terms_briefing_pdf(),
        "FTC_CONSUMER_COMPLAINT_EXAMPLES_20211227": ingest_consumer_complaint_examples(),
        "POST_OFFICE_FINANCIAL_FRAUD_ACCOUNTS_20251231": ingest_post_office_fraud_accounts(),
        "POLICE_VOICE_PHISHING_STATS_20251231": ingest_police_voice_phishing_stats(),
        "POLICE_VOICE_PHISHING_REGIONAL_DAMAGE_20251231": ingest_police_voice_phishing_regional_damage(),
        "KDIC_INSURED_FINANCIAL_COMPANIES_20250930": ingest_kdic_insured_companies(),
        "FTC_BANK_STANDARD_TERMS_20240927": ingest_bank_standard_terms(),
        "FSC_FINANCIAL_TERMS_20260630": ingest_fsc_financial_terms(),
    }
    update_registry(row_counts)
    write_json(
        OFFICIAL_DATA_DIR / "ingestion_manifest.json",
        {
            "generated_at": date.today().isoformat(),
            "source_folder": str(DATA_INBOX),
            "row_counts": row_counts,
            "excluded": [
                {
                    "dataset_id": "FSC_DEPOSIT_INSURANCE_COMPANY_PRODUCT_API",
                    "reason": "사용자 요청에 따라 API만 제공하는 데이터는 제외했습니다.",
                }
            ],
        },
    )
    print(json.dumps(row_counts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
