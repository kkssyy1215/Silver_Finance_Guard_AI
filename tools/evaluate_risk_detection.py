from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.schemas.analysis import TextAnalysisRequest
from app.services.explanation_detector import analyze_explanation_risk
from app.services.risk_detector import analyze_contract_risk


CASES_PATH = ROOT / "backend" / "app" / "data" / "evaluation" / "risk_detection_cases.json"
REPORT_PATH = ROOT / "backend" / "app" / "data" / "evaluation" / "risk_detection_report.json"
DOC_PATH = ROOT / "docs" / "risk_detection_evaluation.md"


def main() -> None:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    results = []
    for case in cases:
        request = TextAnalysisRequest(content=case["content"])
        if case["analysis_type"] == "contract":
            detected = {item.label for item in analyze_contract_risk(request).risk_items}
        else:
            detected = {item.label for item in analyze_explanation_risk(request).suspicious_points}
        expected = set(case["expected_labels"])
        results.append({
            **case,
            "detected_labels": sorted(detected),
            "case_passed": detected == expected,
            "false_positive": not expected and bool(detected),
            "missed_expected": sorted(expected - detected),
        })

    positive = [item for item in results if item["expected_labels"]]
    negative = [item for item in results if not item["expected_labels"]]
    exact_matches = sum(item["case_passed"] for item in results)
    missed = sum(bool(item["missed_expected"]) for item in positive)
    false_positives = sum(item["false_positive"] for item in negative)
    report = {
        "case_count": len(results),
        "positive_case_count": len(positive),
        "negative_case_count": len(negative),
        "exact_case_accuracy": round(exact_matches / len(results), 4),
        "positive_case_recall": round((len(positive) - missed) / len(positive), 4),
        "negative_case_false_positive_rate": round(false_positives / len(negative), 4),
        "results": results,
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 위험 탐지 오탐 방지 평가표",
        "",
        "약관 20개와 상담 문구 20개, 총 40개 문장을 규칙 기반 탐지기에 입력한 결과입니다.",
        "정상 문장은 예상 위험 항목을 비워 오탐 여부를 확인했습니다.",
        "",
        f"- 전체 문장: {report['case_count']}개",
        f"- 위험 문장 탐지 성공률: {report['positive_case_recall']:.1%}",
        f"- 정상 문장 오탐률: {report['negative_case_false_positive_rate']:.1%}",
        f"- 모든 예상 라벨 일치율: {report['exact_case_accuracy']:.1%}",
        "",
        "| ID | 유형 | 예상 결과 | 실제 결과 | 판정 |",
        "|---|---|---|---|---|",
    ]
    for item in results:
        expected = ", ".join(item["expected_labels"]) or "정상"
        detected = ", ".join(item["detected_labels"]) or "정상"
        verdict = "통과" if item["case_passed"] else "확인 필요"
        lines.append(f"| {item['id']} | {item['analysis_type']} | {expected} | {detected} | {verdict} |")
    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"평가 완료: {len(results)}개 문장")
    print(f"위험 문장 탐지 성공률: {report['positive_case_recall']:.1%}")
    print(f"정상 문장 오탐률: {report['negative_case_false_positive_rate']:.1%}")


if __name__ == "__main__":
    main()
