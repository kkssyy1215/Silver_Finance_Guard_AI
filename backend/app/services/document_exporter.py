from datetime import datetime

from app.schemas.document import DocumentExportResponse


def export_document(title: str, body: str, attachments: list[str], export_format: str) -> DocumentExportResponse:
    normalized_format = export_format.lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    safe_title = _safe_filename(title)

    if normalized_format == "html":
        return DocumentExportResponse(
            filename=f"{safe_title}_{timestamp}.html",
            media_type="text/html",
            content=_to_html(title, body, attachments),
        )

    if normalized_format == "md":
        return DocumentExportResponse(
            filename=f"{safe_title}_{timestamp}.md",
            media_type="text/markdown",
            content=_to_markdown(title, body, attachments),
        )

    return DocumentExportResponse(
        filename=f"{safe_title}_{timestamp}.txt",
        media_type="text/plain",
        content=_to_text(title, body, attachments),
    )


def _to_text(title: str, body: str, attachments: list[str]) -> str:
    attachment_text = "\n".join(f"- {attachment}" for attachment in attachments) or "- 없음"
    return f"{title}\n\n{body}\n\n첨부 권장 자료\n{attachment_text}\n"


def _to_markdown(title: str, body: str, attachments: list[str]) -> str:
    attachment_text = "\n".join(f"- {attachment}" for attachment in attachments) or "- 없음"
    return f"# {title}\n\n{body}\n\n## 첨부 권장 자료\n{attachment_text}\n"


def _to_html(title: str, body: str, attachments: list[str]) -> str:
    attachment_items = "".join(f"<li>{_escape(attachment)}</li>" for attachment in attachments) or "<li>없음</li>"
    body_html = "<br>".join(_escape(line) for line in body.splitlines())
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>{_escape(title)}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", sans-serif;
      line-height: 1.7;
      max-width: 760px;
      margin: 48px auto;
      color: #1f2933;
    }}
    h1 {{ font-size: 28px; }}
    h2 {{ font-size: 20px; margin-top: 32px; }}
    .notice {{
      border-left: 4px solid #2f6fed;
      padding: 12px 16px;
      background: #f5f8ff;
      margin-top: 32px;
    }}
  </style>
</head>
<body>
  <h1>{_escape(title)}</h1>
  <p>{body_html}</p>
  <h2>첨부 권장 자료</h2>
  <ul>{attachment_items}</ul>
  <div class="notice">이 문서는 AI가 작성한 초안입니다. 제출 전 사실관계와 개인정보를 다시 확인하세요.</div>
</body>
</html>
"""


def _safe_filename(title: str) -> str:
    normalized = "".join(ch if ch.isalnum() else "_" for ch in title).strip("_")
    return normalized[:48] or "document"


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )

