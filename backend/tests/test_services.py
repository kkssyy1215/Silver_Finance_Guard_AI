from app.services.explanation_detector import analyze_explanation_risk
from app.services.incident_classifier import classify_incident
from app.services.action_plan_service import build_action_plan
from app.services.risk_detector import analyze_contract_risk
from app.services.document_exporter import export_document
from app.services.complaint_service import draft_complaint
from app.schemas.analysis import TextAnalysisRequest
from app.services.official_faq_service import search_kdic_mistaken_transfer_faq
from app.services.official_dataset_service import find_official_datasets, search_financial_terms, search_official_records


def test_contract_risk_detects_auto_renewal() -> None:
    result = analyze_contract_risk(
        TextAnalysisRequest(content="별도 해지 신청이 없는 경우 계약은 자동 연장됩니다.")
    )

    assert result.overall_risk == "medium"
    assert result.risk_items[0].label == "auto_renewal"
    assert result.risk_items[0].senior_action
    assert result.risk_items[0].standard_references
    assert result.standard_comparison_summary


def test_contract_risk_exposes_detected_keywords() -> None:
    result = analyze_contract_risk(
        TextAnalysisRequest(content="마케팅 목적의 개인정보 제3자 제공에 동의합니다.")
    )

    item = result.risk_items[0]
    assert item.label == "third_party_data"
    assert "제3자" in item.detected_keywords
    assert "마케팅 목적" in item.detected_keywords


def test_explanation_risk_detects_exaggerated_return() -> None:
    result = analyze_explanation_risk(
        TextAnalysisRequest(content="이 상품은 확실히 오릅니다. 지금 가입해야 합니다.")
    )

    labels = {point.label for point in result.suspicious_points}
    assert "exaggerated_return" in labels
    assert "pressure_sales" in labels


def test_incident_classifier_prioritizes_voice_phishing() -> None:
    result = classify_incident("검찰이라고 전화가 와서 앱을 깔고 100만원을 보냈어요.")

    assert result.incident_type == "voice_phishing"
    assert result.urgency_level == "critical"
    assert result.evidence
    assert result.urgency_reasons


def test_incident_classifier_does_not_mark_wrong_account_number_as_info_leak() -> None:
    result = classify_incident("계좌번호를 잘못 눌러서 모르는 사람에게 30만원 보냈어요.")

    assert result.incident_type == "mistaken_transfer"
    assert result.extracted_facts.personal_info_shared is False


def test_incident_classifier_handles_negation_and_comma_amounts() -> None:
    result = classify_incident("앱을 설치하지 않았지만 계좌번호를 잘못 눌러 1,000,000원을 보냈어요.")

    assert result.extracted_facts.app_installed is False
    assert result.extracted_facts.transfer_done is True
    assert result.extracted_facts.amount == 1_000_000


def test_contract_risk_does_not_flag_explicitly_free_fee() -> None:
    result = analyze_contract_risk(TextAnalysisRequest(content="수수료가 없습니다."))

    assert result.risk_items == []


def test_risk_results_include_review_status_keywords_and_official_reason() -> None:
    result = analyze_contract_risk(TextAnalysisRequest(content="마케팅 목적의 개인정보 제3자 제공에 동의합니다."))
    item = result.risk_items[0]

    assert item.review_status in {"확인 필요", "주의 후보"}
    assert "제3자" in item.detected_keywords
    assert item.official_references
    assert item.official_references[0].application_reason


def test_voice_phishing_action_plan_includes_official_evidence() -> None:
    result = build_action_plan("voice_phishing", "은행이라고 전화가 와서 앱을 설치하고 50만원을 송금했어요.")

    assert result.evidence
    assert any("경찰청" in item.source_title for item in result.evidence)
    assert result.urgency_reasons


def test_document_exporter_generates_html() -> None:
    result = export_document(
        title="민원 초안",
        body="설명을 충분히 듣지 못했습니다.",
        attachments=["상품설명서", "약관"],
        export_format="html",
    )

    assert result.filename.endswith(".html")
    assert result.media_type == "text/html"
    assert "상품설명서" in result.content
    assert "font-size: 20px" in result.content


def test_complaint_draft_uses_similar_official_cases() -> None:
    result = draft_complaint(
        "보험 가입할 때 고지의무와 보험금 지급 제한을 제대로 설명받지 못했습니다.",
        "mis_selling",
    )

    assert result.similar_cases
    assert result.claim_points
    assert result.submission_checklist
    assert "참고 가능한 유사 사례" not in result.draft_body


def test_complaint_draft_excludes_unrelated_consumer_cases() -> None:
    result = draft_complaint(
        "은행 상담원이 원금이 보장된다고 설명해 가입했지만 손실 가능성을 나중에 알았습니다.",
        "general_complaint",
    )

    unrelated_words = ("패딩", "의류", "장례", "레이저 시술", "화재보험", "차주의 남편")
    assert not any(word in case.title for case in result.similar_cases for word in unrelated_words)
    assert not any(word in result.draft_body for word in unrelated_words)


def test_official_kdic_faq_search_uses_imported_csv_data() -> None:
    result = search_kdic_mistaken_transfer_faq("착오송금 얼마까지 신청 금액")

    assert result
    assert result[0].source_title == "예금보험공사_착오송금 반환지원제도 FAQ_20240729"
    assert "착오송금" in result[0].question


def test_official_dataset_registry_tracks_imported_and_planned_data() -> None:
    imported = find_official_datasets(status="imported")

    assert any(dataset.dataset_id == "KDIC_MISTAKEN_TRANSFER_FAQ_20240729" for dataset in imported)
    assert any(dataset.dataset_id == "FSC_FINANCIAL_TERMS_20260630" and dataset.row_count == 229 for dataset in imported)
    assert not any(dataset.format.startswith("OpenAPI") for dataset in find_official_datasets())


def test_official_record_search_uses_imported_financial_terms() -> None:
    results = search_official_records("예금자보호", limit=5)

    assert results
    assert any("예금" in result.title or "예금" in result.body for result in results)


def test_financial_term_search_returns_easy_explanation() -> None:
    results = search_financial_terms("지급정지", limit=3)

    assert results
    assert results[0].easy_explanation
    assert results[0].action_tip


def test_financial_term_search_handles_body_only_query() -> None:
    results = search_financial_terms("예금", limit=8)

    assert results
    assert all(result.easy_explanation for result in results)
    assert all(result.term != "예금자보호" for result in results)
    assert all(result.match_type == "related" for result in results)


def test_financial_term_search_prioritizes_exact_term_over_body_matches() -> None:
    results = search_financial_terms("예금자보호", limit=5)

    assert [result.term for result in results] == ["예금자보호"]
    assert results[0].match_type == "exact"


def test_official_record_search_uses_new_complaint_and_phishing_data() -> None:
    complaint_results = search_official_records("보험금", dataset_id="FTC_CONSUMER_COMPLAINT_EXAMPLES_20211227", limit=3)
    phishing_results = search_official_records("기관사칭", dataset_id="POLICE_VOICE_PHISHING_STATS_20251231", limit=3)
    standard_terms_results = search_official_records("기한의 이익", dataset_id="FTC_BANK_STANDARD_TERMS_20240927", limit=3)

    assert complaint_results
    assert phishing_results
    assert standard_terms_results
