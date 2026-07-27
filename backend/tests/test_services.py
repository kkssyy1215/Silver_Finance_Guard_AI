from app.services.explanation_detector import analyze_explanation_risk
from app.services.incident_classifier import classify_incident
from app.services.risk_detector import analyze_contract_risk
from app.services.document_exporter import export_document
from app.schemas.analysis import TextAnalysisRequest


def test_contract_risk_detects_auto_renewal() -> None:
    result = analyze_contract_risk(
        TextAnalysisRequest(content="별도 해지 신청이 없는 경우 계약은 자동 연장됩니다.")
    )

    assert result.overall_risk == "medium"
    assert result.risk_items[0].label == "auto_renewal"


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
