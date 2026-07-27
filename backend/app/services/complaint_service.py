from app.schemas.complaint import ComplaintDraftResponse
from app.services.risk_detector import DISCLAIMER


def draft_complaint(user_statement: str, incident_type: str) -> ComplaintDraftResponse:
    title_map = {
        "mistaken_transfer": "착오송금 반환 요청 관련 민원 초안",
        "voice_phishing": "보이스피싱 피해구제 요청 관련 민원 초안",
        "mis_selling": "금융상품 중요사항 설명 부족 관련 민원 초안",
    }
    title = title_map.get(incident_type, "금융소비자 민원 초안")
    attachments = _attachments_for(incident_type)

    return ComplaintDraftResponse(
        complaint_type=incident_type,
        title=title,
        summary="사용자 진술을 사실 중심으로 정리한 초안입니다.",
        draft_body=(
            f"본인은 다음과 같은 금융 관련 문제를 겪었습니다.\n\n"
            f"1. 사건 내용\n{user_statement}\n\n"
            f"2. 요청 사항\n관련 절차와 사실관계를 확인해주시고, 필요한 구제 또는 안내를 요청드립니다.\n\n"
            f"3. 첨부 예정 자료\n{', '.join(attachments)}"
        ),
        recommended_attachments=attachments,
        editable_fields=["사건 발생일", "금액", "금융회사명", "요청 사항"],
        disclaimer=DISCLAIMER,
    )


def _attachments_for(incident_type: str) -> list[str]:
    if incident_type == "voice_phishing":
        return ["이체확인증", "문자/메신저 캡처", "통화 기록", "피해 사실 정리서"]
    if incident_type == "mistaken_transfer":
        return ["이체확인증", "통장 거래내역", "반환 요청 접수 내역"]
    return ["상품설명서", "약관", "상담 녹취 또는 통화 기록", "문자 안내 화면"]

