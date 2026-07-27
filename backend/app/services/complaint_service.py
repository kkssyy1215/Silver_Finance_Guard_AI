import json
import re
from functools import lru_cache
from pathlib import Path

from app.schemas.complaint import ComplaintDraftResponse, SimilarComplaintCase
from app.services.risk_detector import DISCLAIMER

OFFICIAL_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "official"


def draft_complaint(user_statement: str, incident_type: str) -> ComplaintDraftResponse:
    title_map = {
        "mistaken_transfer": "착오송금 반환 요청 관련 민원 초안",
        "voice_phishing": "보이스피싱 피해구제 요청 관련 민원 초안",
        "mis_selling": "금융상품 중요사항 설명 부족 관련 민원 초안",
    }
    title = title_map.get(incident_type, "금융소비자 민원 초안")
    attachments = _attachments_for(incident_type)
    similar_cases = find_similar_complaint_cases(user_statement, incident_type)
    claim_points = _claim_points_for(user_statement, incident_type, similar_cases)
    checklist = _submission_checklist_for(incident_type)

    return ComplaintDraftResponse(
        complaint_type=incident_type,
        title=title,
        summary="사용자 진술과 공식 모범상담 사례를 함께 참고해 정리한 초안입니다.",
        draft_body=(
            f"본인은 다음과 같은 금융 관련 문제를 겪었습니다.\n\n"
            f"1. 사건 내용\n{user_statement}\n\n"
            f"2. 문제로 보는 이유\n{_format_numbered(claim_points)}\n\n"
            f"3. 요청 사항\n"
            f"관련 절차와 사실관계를 확인해주시고, 설명 부족·부당 권유·피해 발생 여부에 대해 조사해 주시기 바랍니다. "
            f"확인 결과에 따라 계약 취소, 손해 회복, 수수료 환급, 피해구제 절차 안내 등 필요한 조치를 요청드립니다.\n\n"
            f"4. 참고 가능한 유사 사례\n{_format_similar_cases(similar_cases)}\n\n"
            f"5. 첨부 예정 자료\n{', '.join(attachments)}"
        ),
        recommended_attachments=attachments,
        editable_fields=["사건 발생일", "금액", "금융회사명", "요청 사항"],
        similar_cases=similar_cases,
        claim_points=claim_points,
        submission_checklist=checklist,
        disclaimer=DISCLAIMER,
    )


def _attachments_for(incident_type: str) -> list[str]:
    if incident_type == "voice_phishing":
        return ["이체확인증", "문자/메신저 캡처", "통화 기록", "피해 사실 정리서"]
    if incident_type == "mistaken_transfer":
        return ["이체확인증", "통장 거래내역", "반환 요청 접수 내역"]
    return ["상품설명서", "약관", "상담 녹취 또는 통화 기록", "문자 안내 화면"]


@lru_cache
def load_complaint_examples() -> list[dict[str, str]]:
    path = OFFICIAL_DATA_DIR / "ftc_consumer_complaint_examples.json"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as examples_file:
        return json.load(examples_file)


def find_similar_complaint_cases(user_statement: str, incident_type: str, limit: int = 3) -> list[SimilarComplaintCase]:
    query_terms = _important_terms(user_statement) + _terms_for_incident_type(incident_type)
    scored_cases: list[tuple[int, dict[str, str]]] = []

    for case in load_complaint_examples():
        haystack = f"{case.get('title', '')} {case.get('content', '')} {case.get('answer', '')}"
        score = _score(haystack, query_terms)
        if score <= 0:
            continue
        scored_cases.append((score, case))

    scored_cases.sort(key=lambda item: item[0], reverse=True)
    return [
        SimilarComplaintCase(
            title=case.get("title", ""),
            case_no=case.get("case_no", ""),
            relevance_reason=_relevance_reason(case, query_terms),
            answer_summary=_summarize_answer(case.get("answer", "")),
        )
        for _, case in scored_cases[:limit]
    ]


def _claim_points_for(user_statement: str, incident_type: str, similar_cases: list[SimilarComplaintCase]) -> list[str]:
    points = []
    normalized = user_statement.lower()

    if incident_type == "mis_selling" or any(term in normalized for term in ["설명", "원금", "손실", "수익", "위험", "권유"]):
        points.append("상품 가입 전 원금 손실 가능성, 수수료, 중도해지 조건 등 중요사항을 충분히 설명받았는지 확인이 필요합니다.")
    if any(term in normalized for term in ["오늘", "지금", "급하게", "확실", "무조건", "보장"]):
        points.append("확정적 수익 표현이나 즉시 가입 압박이 있었다면 부당 권유 또는 불완전판매 가능성을 확인해야 합니다.")
    if incident_type == "voice_phishing":
        points.append("피해금 이동을 막기 위해 지급정지, 피해구제 신청, 수사기관 신고가 신속히 진행되었는지 확인이 필요합니다.")
    if incident_type == "mistaken_transfer":
        points.append("송금 금융회사를 통한 반환 요청을 먼저 진행했는지, 미반환 시 착오송금 반환지원 대상인지 확인해야 합니다.")
    if similar_cases:
        points.append("공식 모범상담 사례와 유사한 쟁점이 있어, 사실관계와 증빙자료를 중심으로 판단을 요청할 수 있습니다.")

    return points or ["사실관계, 계약 내용, 상담 당시 설명, 피해 발생 경위를 기준으로 구제 가능성을 확인해야 합니다."]


def _submission_checklist_for(incident_type: str) -> list[str]:
    common = [
        "사건 발생일과 상담·가입·송금 시간을 날짜순으로 정리하기",
        "금융회사명, 담당자명, 통화번호, 상품명을 빈칸 없이 적기",
        "주장만 쓰지 말고 문자, 녹취, 약관, 이체내역 같은 증빙을 함께 준비하기",
    ]
    if incident_type == "voice_phishing":
        return ["은행에 지급정지 요청 여부 확인하기", "경찰 신고 접수번호 확인하기", "피해구제신청서 제출 여부 확인하기"] + common
    if incident_type == "mistaken_transfer":
        return ["송금한 은행에 반환 요청 접수했는지 확인하기", "수취인에게 직접 연락하지 말고 금융회사 절차로 진행하기"] + common
    return ["상품설명서와 실제 들은 설명이 다른 부분 표시하기", "원금손실·수수료·해지조건 설명 여부를 따로 적기"] + common


def _terms_for_incident_type(incident_type: str) -> list[str]:
    if incident_type == "voice_phishing":
        return ["보이스피싱", "사기", "피해구제", "지급정지", "사칭"]
    if incident_type == "mistaken_transfer":
        return ["착오송금", "송금", "반환", "계좌"]
    if incident_type == "mis_selling":
        return ["보험", "투자", "설명", "고지의무", "원금", "손실", "수수료"]
    return ["소비자", "피해", "민원", "보상", "환급"]


def _important_terms(text: str) -> list[str]:
    tokens = re.findall(r"[가-힣A-Za-z0-9]{2,}", text)
    stopwords = {"저는", "제가", "관련", "문제", "했습니다", "있습니다", "그리고", "그런데", "받았습니다"}
    return [token for token in tokens if token not in stopwords][:16]


def _score(text: str, terms: list[str]) -> int:
    normalized = text.lower()
    return sum(normalized.count(term.lower()) for term in terms if term)


def _relevance_reason(case: dict[str, str], terms: list[str]) -> str:
    haystack = f"{case.get('title', '')} {case.get('content', '')} {case.get('answer', '')}".lower()
    matched = [term for term in terms if term and term.lower() in haystack][:4]
    if matched:
        return "입력 내용과 '" + "', '".join(matched) + "' 쟁점이 겹칩니다."
    return "소비자 피해구제 쟁점이 유사합니다."


def _summarize_answer(answer: str) -> str:
    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?。])\s+| {2,}", answer) if sentence.strip()]
    if not sentences:
        return answer[:220]
    return " ".join(sentences[:2])[:260]


def _format_numbered(items: list[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))


def _format_similar_cases(cases: list[SimilarComplaintCase]) -> str:
    if not cases:
        return "현재 입력과 직접 연결되는 공식 모범상담 사례는 찾지 못했습니다."
    return "\n".join(
        f"{index}. {case.title} - {case.relevance_reason} 답변 요지: {case.answer_summary}"
        for index, case in enumerate(cases, start=1)
    )
