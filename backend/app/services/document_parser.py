from io import BytesIO

from fastapi import UploadFile
from pypdf import PdfReader


SUPPORTED_TEXT_TYPES = {
    "text/plain",
    "text/markdown",
    "application/json",
}


async def extract_text_from_upload(file: UploadFile) -> tuple[str, str, str]:
    content = await file.read()
    content_type = file.content_type or "application/octet-stream"

    if content_type == "application/pdf" or file.filename.endswith(".pdf"):
        return "pdf", _extract_pdf_text(content), "PDF에서 텍스트를 추출했습니다."

    if content_type in SUPPORTED_TEXT_TYPES or file.filename.endswith((".txt", ".md", ".json")):
        return "text", content.decode("utf-8", errors="ignore"), "텍스트 파일을 읽었습니다."

    return (
        "unsupported",
        "",
        "현재 MVP에서는 PDF와 텍스트 파일을 먼저 지원합니다. 사진 OCR은 다음 단계에서 연결합니다.",
    )


def _extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(page.strip() for page in pages if page.strip())
