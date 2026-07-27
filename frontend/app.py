from __future__ import annotations

import os
from html import escape
from typing import Any

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="실버 금융가드 AI", page_icon="🛡️", layout="wide")

FONT_SCALE_OPTIONS = {
    "기본": {"base": "18px", "large": "1.25rem", "xlarge": "1.55rem"},
    "크게": {"base": "21px", "large": "1.45rem", "xlarge": "1.8rem"},
    "아주 크게": {"base": "24px", "large": "1.65rem", "xlarge": "2.05rem"},
}

with st.sidebar:
    st.header("보기 편하게")
    font_mode = st.radio("글자 크기", ["기본", "크게", "아주 크게"], index=1)
    high_contrast = st.toggle("고대비 화면", value=True)
    magnifier_enabled = st.toggle("돋보기 보기", value=True)
    st.caption("고령층 사용자가 글자를 크게 보고, 중요한 내용을 한 번 더 확대해서 확인할 수 있습니다.")

font_tokens = FONT_SCALE_OPTIONS[font_mode]
surface_color = "#fffdf4" if high_contrast else "#ffffff"
text_color = "#111827" if high_contrast else "#243044"
border_color = "#111827" if high_contrast else "#d7dce2"
accent_color = "#b42318" if high_contrast else "#2f6fed"

st.markdown(
    f"""
    <style>
    html, body, [class*="css"] {{
      font-size: {font_tokens["base"]};
      color: {text_color};
    }}
    .main .block-container {{ max-width: 1120px; padding-top: 1.4rem; }}
    h1 {{ font-size: 2.5rem !important; line-height: 1.2; }}
    h2, h3 {{ letter-spacing: -0.02em; }}
    div[data-testid="stButton"] button {{
      min-height: 3.8rem;
      font-size: {font_tokens["large"]};
      font-weight: 700;
      border-radius: 14px;
    }}
    textarea {{
      font-size: {font_tokens["large"]} !important;
      line-height: 1.75 !important;
      background: {surface_color} !important;
    }}
    .notice {{
      border-left: 8px solid {accent_color};
      background: {surface_color};
      color: {text_color};
      padding: 1.1rem 1.2rem;
      margin: 0.8rem 0 1.2rem;
      border-radius: 14px;
      font-size: {font_tokens["large"]};
      line-height: 1.65;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
    }}
    .senior-guide {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 0.8rem;
      margin: 1rem 0;
    }}
    .guide-card, .big-card, .emergency-card, .magnifier-card {{
      border: 2px solid {border_color};
      border-radius: 18px;
      padding: 1rem 1.1rem;
      background: {surface_color};
      color: {text_color};
      box-shadow: 0 8px 22px rgba(15, 23, 42, 0.08);
    }}
    .guide-card strong {{
      display: block;
      font-size: {font_tokens["large"]};
      margin-bottom: 0.25rem;
    }}
    .guide-card span {{
      font-size: 1rem;
      line-height: 1.55;
    }}
    .magnifier-card {{
      border-color: {accent_color};
      font-size: {font_tokens["xlarge"]};
      line-height: 1.85;
      margin: 0.7rem 0 1rem;
    }}
    .step-card {{
      display: flex;
      gap: 1rem;
      align-items: flex-start;
      border: 2px solid {border_color};
      border-radius: 18px;
      padding: 1rem;
      margin-bottom: 0.8rem;
      background: {surface_color};
    }}
    .step-number {{
      min-width: 3rem;
      height: 3rem;
      border-radius: 999px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: {accent_color};
      color: white;
      font-weight: 800;
      font-size: 1.35rem;
    }}
    .step-body strong {{
      display: block;
      font-size: {font_tokens["large"]};
      margin-bottom: 0.25rem;
    }}
    .step-body span {{
      line-height: 1.55;
    }}
    .emergency-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 0.8rem;
      margin: 1rem 0;
    }}
    .emergency-card strong {{
      display: block;
      font-size: {font_tokens["xlarge"]};
      color: {accent_color};
      margin-bottom: 0.2rem;
    }}
    .emergency-card span {{
      line-height: 1.5;
    }}
    @media (max-width: 760px) {{
      .senior-guide, .emergency-grid {{ grid-template-columns: 1fr; }}
    }}
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


def render_senior_guide() -> None:
    st.markdown(
        """
        <div class="senior-guide">
          <div class="guide-card"><strong>1. 크게 읽기</strong><span>왼쪽에서 글자 크기를 키우고 고대비 화면을 켤 수 있습니다.</span></div>
          <div class="guide-card"><strong>2. 천천히 확인</strong><span>중요한 문장은 돋보기 보기로 한 번 더 크게 보여드립니다.</span></div>
          <div class="guide-card"><strong>3. 바로 행동</strong><span>사고가 의심되면 먼저 전화, 증거 저장, 지급정지 순서로 안내합니다.</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_magnifier(title: str, text: str) -> None:
    if not magnifier_enabled or not text:
        return
    cleaned = escape(text.strip()).replace("\n", "<br>")
    st.markdown(
        f"""
        <div class="magnifier-card">
          <strong>{escape(title)}</strong><br>
          {cleaned}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_step_card(order: int, action: str, reason: str) -> None:
    st.markdown(
        f"""
        <div class="step-card">
          <div class="step-number">{order}</div>
          <div class="step-body">
            <strong>{escape(action)}</strong>
            <span>{escape(reason)}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_emergency_cards() -> None:
    st.markdown(
        """
        <div class="emergency-grid">
          <div class="emergency-card"><strong>112</strong><span>보이스피싱·현금 전달·협박이 있으면 경찰에 바로 신고하세요.</span></div>
          <div class="emergency-card"><strong>은행</strong><span>돈을 보냈다면 송금한 은행에 지급정지부터 요청하세요.</span></div>
          <div class="emergency-card"><strong>1332</strong><span>금융감독원 상담이 필요할 때 금융소비자 상담센터로 문의하세요.</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def export_report_button(title: str, body: str, attachments: list[str], button_label: str, key: str) -> None:
    exported = post_json(
        "/api/v1/documents/export",
        {
            "title": title,
            "body": body,
            "attachments": attachments,
            "export_format": "html",
        },
    )
    if exported:
        st.download_button(
            button_label,
            data=exported["content"].encode("utf-8"),
            file_name=exported["filename"],
            mime=f"{exported['media_type']}; charset=utf-8",
            use_container_width=True,
            key=key,
        )


def build_contract_report(result: dict[str, Any]) -> tuple[str, str, list[str]]:
    lines = [
        f"전체 위험도: {risk_label(result['overall_risk'])}",
        "",
        "쉬운 요약",
        result["document_summary"]["one_line"],
        result["document_summary"]["easy_summary"],
        result["document_summary"]["next_action"],
        "",
        "위험 항목",
    ]
    for index, item in enumerate(result.get("risk_items", []), start=1):
        lines.extend(
            [
                f"{index}. {item['label']} - {risk_label(item['severity'])}",
                f"문제 문장: {item['original_text']}",
                f"감지된 핵심 단어: {', '.join(item.get('detected_keywords', []))}",
                f"쉬운 설명: {item['simplified_text']}",
                f"확인 질문: {item['must_ask_question']}",
                f"어르신 행동 안내: {item.get('senior_action', '')}",
                f"표준약관 비교: {item.get('comparison_result', '')}",
                "",
            ]
        )
    if result.get("standard_comparison_summary"):
        lines.append("표준약관 기준 확인 요약")
        lines.extend(f"- {summary}" for summary in result["standard_comparison_summary"])
    return "약관 위험 점검 리포트", "\n".join(lines), ["약관 원문", "상품설명서", "상담 녹취 또는 문자 안내"]


def build_explanation_report(result: dict[str, Any]) -> tuple[str, str, list[str]]:
    lines = [
        f"위험도: {risk_label(result['risk_level'])}",
        "",
        "쉬운 요약",
        result["summary"]["one_line"],
        result["summary"]["easy_summary"],
        result["summary"]["next_action"],
        "",
        "의심 표현",
    ]
    for index, point in enumerate(result.get("suspicious_points", []), start=1):
        lines.extend(
            [
                f"{index}. {point['label']} - {risk_label(point['severity'])}",
                f"쉬운 설명: {point['easy_explanation']}",
                f"이유: {point['reason']}",
                f"확인 질문: {point['must_ask_question']}",
                "",
            ]
        )
    lines.append("확인 질문")
    lines.extend(f"- {question}" for question in result.get("must_ask_questions", []))
    return "설명의무 위험 점검 리포트", "\n".join(lines), ["상담 녹취", "문자 안내", "상품설명서", "가입 신청서"]


def build_incident_report(classified: dict[str, Any], plan: dict[str, Any]) -> tuple[str, str, list[str]]:
    lines = [
        f"사고 유형: {classified['incident_type']}",
        f"긴급도: {risk_label(classified['urgency_level'])}",
        f"첫 행동: {classified['first_action_summary']}",
        "",
        "왜 지금 바로 해야 하나요?",
    ]
    lines.extend(f"- {reason}" for reason in classified.get("urgency_reasons", []))
    lines.append("")
    lines.append("공식 데이터 근거")
    for item in classified.get("evidence", []):
        lines.append(f"- {item['title']}: {item['summary']} ({item['source_title']})")
    for title, key in [
        ("지금 바로 할 일", "immediate"),
        ("10분 안에 할 일", "within_10min"),
        ("오늘 할 일", "today"),
        ("이후 준비할 일", "follow_up"),
    ]:
        lines.extend(["", title])
        for step in plan.get(key, []):
            lines.append(f"{step['order']}. {step['action']} - {step['reason']}")
    documents = [doc["name"] for doc in plan.get("required_documents", [])]
    return "금융사고 대응 리포트", "\n".join(lines), documents


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


def render_faq_matches(faq_matches: list[dict[str, str]]) -> None:
    if not faq_matches:
        return
    st.subheader("공식 FAQ 기반 답변")
    for faq in faq_matches:
        with st.container(border=True):
            st.markdown(f"**Q. {faq['question']}**")
            st.write(faq["answer"])
            st.caption(f"{faq['source_title']} · {faq['category']}")
            st.link_button("FAQ 출처 보기", faq["source_url"])


def render_incident_evidence(evidence: list[dict[str, Any]], urgency_reasons: list[str]) -> None:
    if urgency_reasons:
        st.subheader("왜 지금 바로 해야 하나요?")
        for reason in urgency_reasons:
            st.warning(reason)
    if evidence:
        st.subheader("공식 데이터 근거")
        for item in evidence:
            with st.container(border=True):
                st.markdown(f"**{item['title']}**")
                st.write(item["summary"])
                st.caption(item["source_title"])
                if item.get("matched_fields"):
                    st.write("확인 항목: " + ", ".join(item["matched_fields"]))


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
        render_magnifier("돋보기: 내가 입력한 내용", content)
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
                    if item.get("detected_keywords"):
                        st.error("주의가 필요하다고 본 단어: " + ", ".join(item["detected_keywords"]))
                    if item.get("original_text"):
                        st.info(f"탐지된 원문: {item['original_text']}")
                    st.write(item["simplified_text"])
                    render_magnifier("돋보기: 쉬운 설명", item["simplified_text"])
                    st.caption(item["why_it_matters"])
                    st.warning(item["must_ask_question"])
                    if item.get("senior_action"):
                        st.info(f"어르신용 행동 안내: {item['senior_action']}")
                    if item.get("comparison_result"):
                        st.write(f"표준약관 비교: {item['comparison_result']}")
                    if item.get("standard_references"):
                        with st.expander("표준약관 근거 보기"):
                            for reference in item["standard_references"]:
                                st.write(reference)
            if result["must_ask_questions"]:
                st.subheader("가입 전 꼭 물어볼 질문")
                for question in result["must_ask_questions"]:
                    st.write(f"- {question}")
            if result.get("standard_comparison_summary"):
                st.subheader("표준약관 기준 확인 요약")
                for summary in result["standard_comparison_summary"]:
                    st.write(f"- {summary}")
            report_title, report_body, report_attachments = build_contract_report(result)
            export_report_button(report_title, report_body, report_attachments, "약관 점검 리포트 다운로드", "contract_report")
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
            report_title, report_body, report_attachments = build_explanation_report(result)
            export_report_button(report_title, report_body, report_attachments, "설명의무 점검 리포트 다운로드", "explanation_report")
            render_references(result.get("references", []))
            st.caption(result["disclaimer"])


def render_incident_response() -> None:
    st.header("사고 대응")
    st.write("착오송금이나 보이스피싱이 의심될 때 지금 해야 할 일을 순서대로 알려드립니다.")
    render_emergency_cards()

    quick = st.radio(
        "상황 예시",
        [
            "계좌번호를 잘못 눌러서 모르는 사람에게 30만원 보냈어요.",
            "검찰이라고 전화가 와서 앱을 깔고 100만원을 보냈어요.",
            "직접 만나 현금을 전달했어요.",
        ],
    )
    content = st.text_area("상황을 편하게 적어주세요.", value=quick, height=140)
    render_magnifier("돋보기: 내 사고 상황", content)

    if st.button("사고 대응 시작", use_container_width=True):
        classified = post_json("/api/v1/incidents/classify", {"content": content})
        if not classified:
            return

        st.metric("분류 결과", classified["incident_type"])
        st.metric("긴급도", risk_label(classified["urgency_level"]))
        st.info(classified["first_action_summary"])
        render_incident_evidence(classified.get("evidence", []), classified.get("urgency_reasons", []))
        render_faq_matches(classified.get("faq_matches", []))
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
                render_step_card(step["order"], step["action"], step["reason"])

        render_incident_evidence(plan.get("evidence", []), plan.get("urgency_reasons", []))

        st.subheader("준비할 서류")
        for doc in plan["required_documents"]:
            st.write(f"- {doc['name']}: {doc['reason']}")
            if doc["alternative"]:
                st.caption(f"대체 자료: {doc['alternative']}")

        render_references(plan.get("references", []))
        render_faq_matches(plan.get("faq_matches", []))

        report_title, report_body, report_attachments = build_incident_report(classified, plan)
        export_report_button(report_title, report_body, report_attachments, "사고 대응 리포트 다운로드", "incident_report")

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
    render_magnifier("돋보기: 민원 상황 설명", statement)

    if st.button("민원 초안 만들기", use_container_width=True):
        result = post_json(
            "/api/v1/complaints/draft",
            {"user_statement": statement, "incident_type": incident_type},
        )
        if result:
            st.subheader(result["title"])
            st.write(result["summary"])
            draft_body = st.text_area("초안", value=result["draft_body"], height=260)
            render_magnifier("돋보기: 민원 초안", draft_body)
            if result.get("claim_points"):
                st.subheader("주장 포인트")
                for point in result["claim_points"]:
                    st.write(f"- {point}")
            if result.get("similar_cases"):
                st.subheader("공식 모범상담 유사 사례")
                for case in result["similar_cases"]:
                    with st.container(border=True):
                        st.markdown(f"**{case['title']}**")
                        st.caption(f"사건번호: {case['case_no']}")
                        st.write(case["relevance_reason"])
                        st.info(case["answer_summary"])
            if result.get("submission_checklist"):
                st.subheader("접수 전 체크리스트")
                for item in result["submission_checklist"]:
                    st.write(f"- {item}")
            st.subheader("첨부 권장 자료")
            for attachment in result["recommended_attachments"]:
                st.write(f"- {attachment}")
            export_format = st.radio("다운로드 형식", ["txt", "md", "html"], horizontal=True)
            exported = post_json(
                "/api/v1/documents/export",
                {
                    "title": result["title"],
                    "body": draft_body,
                    "attachments": result["recommended_attachments"],
                    "export_format": export_format,
                },
            )
            if exported:
                st.download_button(
                    "초안 다운로드",
                    data=exported["content"].encode("utf-8"),
                    file_name=exported["filename"],
                    mime=f"{exported['media_type']}; charset=utf-8",
                    use_container_width=True,
                )
            st.caption(result["disclaimer"])


def render_official_data() -> None:
    st.header("공식 데이터")
    st.write("프로젝트에 실제로 연결했거나, 다음 수집 후보로 관리 중인 공식 데이터 목록입니다.")

    col1, col2 = st.columns(2)
    with col1:
        status = st.selectbox("상태", ["전체", "imported", "planned", "reference_only"])
    with col2:
        query = st.text_input("검색어", placeholder="예: 착오송금, 보이스피싱, 고령층")

    params = {}
    if status != "전체":
        params["status"] = status
    if query:
        params["query"] = query

    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/official-data/datasets", params=params, timeout=20)
        response.raise_for_status()
        datasets = response.json()["datasets"]
    except requests.RequestException as exc:
        st.error(f"공식 데이터 목록을 불러오지 못했습니다. ({exc})")
        return

    st.caption(f"총 {len(datasets)}개 데이터")
    for dataset in datasets:
        with st.container(border=True):
            st.markdown(f"**{dataset['title']}**")
            st.caption(f"{dataset['publisher']} · {dataset['portal']} · {dataset['status']}")
            st.write(dataset["summary"])
            st.write(f"형식: {dataset['format']} / 행 수: {dataset['row_count'] or '확인 필요'}")
            st.write(f"이용조건: {dataset['license']} / 비용: {dataset['fee']}")
            st.write("태그: " + ", ".join(dataset["tags"]))
            if dataset["url"]:
                st.link_button("출처 보기", dataset["url"])

    st.divider()
    st.subheader("정제 데이터 검색")
    st.write("금융용어, 표준약관, 민원 사례, 서민금융 FAQ, 예금보험 자료, 전화권유판매 사업자, 보이스피싱 통계를 한 번에 검색합니다.")
    record_query = st.text_input("데이터 검색어", value="예금자보호", placeholder="예: 예금자보호, 미소금융, 보이스피싱, 자동연장")
    if st.button("공식 데이터에서 검색", use_container_width=True):
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/v1/official-data/records/search",
                params={"query": record_query, "limit": 10},
                timeout=20,
            )
            response.raise_for_status()
            records = response.json()["records"]
        except requests.RequestException as exc:
            st.error(f"정제 데이터 검색에 실패했습니다. ({exc})")
            return

        st.caption(f"검색 결과 {len(records)}건")
        for record in records:
            with st.container(border=True):
                st.markdown(f"**{record['title']}**")
                st.caption(f"{record['source_title']} · {record['dataset_id']}")
                st.write(record["body"][:600] + ("..." if len(record["body"]) > 600 else ""))
                if record.get("source_url"):
                    st.link_button("원문 보기", record["source_url"])


st.title("실버 금융가드 AI")
st.markdown(
    '<div class="notice">고령층 사용자가 이해하기 어려운 금융 약관의 위험 요소를 사전에 탐지하고, 금융사고 발생 시 골든타임 내 필요한 조치와 서류 작성을 지원합니다.</div>',
    unsafe_allow_html=True,
)
render_senior_guide()

tab_contract, tab_incident, tab_complaint, tab_data = st.tabs(["가입 전 점검", "사고 대응", "민원 초안", "공식 데이터"])

with tab_contract:
    render_contract_check()

with tab_incident:
    render_incident_response()

with tab_complaint:
    render_complaint_draft()

with tab_data:
    render_official_data()
