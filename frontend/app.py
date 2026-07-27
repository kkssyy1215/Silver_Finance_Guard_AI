from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="실버 금융가드 AI", page_icon="🛡️", layout="wide")

st.markdown(
    """
    <style>
    .main .block-container { max-width: 1080px; padding-top: 2rem; }
    div[data-testid="stButton"] button {
      min-height: 3rem;
      font-size: 1.05rem;
      font-weight: 700;
    }
    textarea { font-size: 1.05rem !important; }
    .risk-card {
      border: 1px solid #d7dce2;
      border-radius: 8px;
      padding: 1rem;
      margin-bottom: 0.8rem;
      background: #ffffff;
    }
    .notice {
      border-left: 5px solid #2f6fed;
      background: #f5f8ff;
      padding: 0.9rem 1rem;
      margin: 0.8rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def post_json(path: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    try:
        response = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        st.error(f"서버와 연결하지 못했습니다. 백엔드가 실행 중인지 확인해주세요. ({exc})")
        return None


def post_file(path: str, field_name: str, uploaded_file: Any) -> dict[str, Any] | None:
    try:
        files = {
            field_name: (
                uploaded_file.name,
                uploaded_file.getvalue(),
                uploaded_file.type or "application/octet-stream",
            )
        }
        response = requests.post(f"{API_BASE_URL}{path}", files=files, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        st.error(f"파일 분석 중 문제가 생겼습니다. 백엔드가 실행 중인지 확인해주세요. ({exc})")
        return None


def risk_label(level: str) -> str:
    labels = {
        "low": "낮음",
        "medium": "주의",
        "high": "높음",
        "critical": "긴급",
        "unknown": "확인 필요",
    }
    return labels.get(level, "확인 필요")


def render_easy_summary(summary: dict[str, str]) -> None:
    st.subheader(summary["one_line"])
    st.write(summary["easy_summary"])
    st.info(summary["next_action"])


def render_references(references: list[dict[str, str]]) -> None:
    if not references:
        return
    st.subheader("근거 자료")
    for reference in references:
        with st.container(border=True):
            st.markdown(f"**{reference['title']}**")
            st.caption(reference["publisher"])
            st.write(reference["summary"])
            st.link_button("원문 보기", reference["url"])


def render_contract_check() -> None:
    st.header("가입 전 점검")
    st.write("약관, 계약서, 문자, 상담 내용을 넣으면 위험한 표현을 쉬운 말로 알려드립니다.")

    input_mode = st.radio("입력 방식", ["텍스트 입력", "PDF/텍스트 파일 업로드"], horizontal=True)
    sample = (
        "별도 해지 신청이 없는 경우 계약은 자동 연장됩니다. "
        "마케팅 목적의 개인정보 제3자 제공에 동의합니다. "
        "본 조건은 오늘만 제공되며 조기 종료될 수 있습니다."
    )
    content = ""
    uploaded_file = None

    if input_mode == "텍스트 입력":
        content = st.text_area("확인할 내용을 입력하세요.", value=sample, height=180)
    else:
        uploaded_file = st.file_uploader("PDF 또는 텍스트 파일을 올려주세요.", type=["pdf", "txt", "md", "json"])
        st.caption("사진 OCR은 다음 단계에서 연결할 예정입니다. 현재는 PDF와 텍스트 파일을 먼저 지원합니다.")

    col1, col2 = st.columns(2)
    with col1:
        analyze_contract = st.button("약관 위험 점검", use_container_width=True)
    with col2:
        analyze_explanation = st.button("설명의무 위험 점검", use_container_width=True)

    if analyze_contract:
        if input_mode == "PDF/텍스트 파일 업로드":
            if uploaded_file is None:
                st.warning("분석할 파일을 먼저 올려주세요.")
                return
            result = post_file("/api/v1/analyze/document-file", "file", uploaded_file)
        else:
            result = post_json("/api/v1/analyze/document", {"content": content})
        if result:
            render_easy_summary(result["document_summary"])
            st.metric("전체 위험도", risk_label(result["overall_risk"]))
            for item in result["risk_items"]:
                with st.container(border=True):
                    st.markdown(f"**{item['label']} · {risk_label(item['severity'])}**")
                    st.write(item["simplified_text"])
                    st.caption(item["why_it_matters"])
                    st.warning(item["must_ask_question"])
            if result["must_ask_questions"]:
                st.subheader("가입 전 꼭 물어볼 질문")
                for question in result["must_ask_questions"]:
                    st.write(f"- {question}")
            render_references(result.get("references", []))
            st.caption(result["disclaimer"])

    if analyze_explanation:
        if input_mode != "텍스트 입력":
            st.warning("설명의무 위험 점검은 상담 내용이나 문자 텍스트를 입력해서 사용해주세요.")
            return
        result = post_json(
            "/api/v1/analyze/explanation-risk",
            {"content": content, "content_type": "consultation_note", "user_age_group": "senior"},
        )
        if result:
            render_easy_summary(result["summary"])
            st.metric("위험도", risk_label(result["risk_level"]))
            for point in result["suspicious_points"]:
                with st.container(border=True):
                    st.markdown(f"**{point['label']} · {risk_label(point['severity'])}**")
                    st.write(point["easy_explanation"])
                    st.caption(point["reason"])
                    st.warning(point["must_ask_question"])
            st.subheader("확인 질문")
            for question in result["must_ask_questions"]:
                st.write(f"- {question}")
            render_references(result.get("references", []))
            st.caption(result["disclaimer"])


def render_incident_response() -> None:
    st.header("사고 대응")
    st.write("착오송금이나 보이스피싱이 의심될 때 지금 해야 할 일을 순서대로 알려드립니다.")

    quick = st.radio(
        "상황 예시",
        [
            "계좌번호를 잘못 눌러서 모르는 사람에게 30만원 보냈어요.",
            "검찰이라고 전화가 와서 앱을 깔고 100만원을 보냈어요.",
            "직접 만나 현금을 전달했어요.",
        ],
    )
    content = st.text_area("상황을 편하게 적어주세요.", value=quick, height=140)

    if st.button("사고 대응 시작", use_container_width=True):
        classified = post_json("/api/v1/incidents/classify", {"content": content})
        if not classified:
            return

        st.metric("분류 결과", classified["incident_type"])
        st.metric("긴급도", risk_label(classified["urgency_level"]))
        st.info(classified["first_action_summary"])
        render_references(classified.get("references", []))

        plan = post_json(
            "/api/v1/incidents/action-plan",
            {"incident_type": classified["incident_type"], "content": content},
        )
        if not plan:
            return

        for title, key in [
            ("지금 바로 할 일", "immediate"),
            ("10분 안에 할 일", "within_10min"),
            ("오늘 할 일", "today"),
            ("이후 준비할 일", "follow_up"),
        ]:
            st.subheader(title)
            for step in plan[key]:
                st.write(f"{step['order']}. {step['action']}")
                st.caption(step["reason"])

        st.subheader("준비할 서류")
        for doc in plan["required_documents"]:
            st.write(f"- {doc['name']}: {doc['reason']}")
            if doc["alternative"]:
                st.caption(f"대체 자료: {doc['alternative']}")

        render_references(plan.get("references", []))

        st.session_state["last_incident_type"] = classified["incident_type"]
        st.session_state["last_statement"] = content
        st.caption(plan["disclaimer"])


def render_complaint_draft() -> None:
    st.header("민원 초안")
    st.write("장황한 상황 설명을 민원 접수용 문장으로 정리합니다.")

    default_statement = st.session_state.get(
        "last_statement",
        "상품 가입 당시 원금 손실 가능성과 해지 비용에 대한 설명을 충분히 듣지 못했습니다.",
    )
    incident_type = st.selectbox(
        "문제 유형",
        ["mis_selling", "mistaken_transfer", "voice_phishing", "general_complaint"],
        index=0,
    )
    statement = st.text_area("상황 설명", value=default_statement, height=180)

    if st.button("민원 초안 만들기", use_container_width=True):
        result = post_json(
            "/api/v1/complaints/draft",
            {"user_statement": statement, "incident_type": incident_type},
        )
        if result:
            st.subheader(result["title"])
            st.write(result["summary"])
            st.text_area("초안", value=result["draft_body"], height=260)
            st.subheader("첨부 권장 자료")
            for attachment in result["recommended_attachments"]:
                st.write(f"- {attachment}")
            st.caption(result["disclaimer"])


st.title("실버 금융가드 AI")
st.markdown(
    '<div class="notice">고령층 사용자가 이해하기 어려운 금융 약관의 위험 요소를 사전에 탐지하고, 금융사고 발생 시 골든타임 내 필요한 조치와 서류 작성을 지원합니다.</div>',
    unsafe_allow_html=True,
)

tab_contract, tab_incident, tab_complaint = st.tabs(["가입 전 점검", "사고 대응", "민원 초안"])

with tab_contract:
    render_contract_check()

with tab_incident:
    render_incident_response()

with tab_complaint:
    render_complaint_draft()
