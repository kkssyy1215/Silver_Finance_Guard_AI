from io import BytesIO

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader


SUPPORTED_TEXT_TYPES = {
    "text/plain",
    "text/markdown",
    "application/json",
}
SUPPORTED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 60


async def extract_text_from_upload(file: UploadFile) -> tuple[str, str, str]:
    content = await file.read()
    if len(content) > MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=413, detail="파일은 10MB 이하만 올릴 수 있습니다.")
    content_type = file.content_type or "application/octet-stream"

    filename = (file.filename or "").lower()

    if content_type == "application/pdf" or filename.endswith(".pdf"):
        try:
            return "pdf", _extract_pdf_text(content), "PDF에서 텍스트를 추출했습니다."
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail="PDF를 읽지 못했습니다. 손상되지 않은 파일인지 확인해주세요.") from exc

    if content_type in SUPPORTED_IMAGE_TYPES or filename.endswith((".png", ".jpg", ".jpeg", ".webp")):
        text, message = _extract_image_text(content)
        return "image", text, message

    if content_type in SUPPORTED_TEXT_TYPES or filename.endswith((".txt", ".md", ".json")):
        return "text", content.decode("utf-8", errors="ignore"), "텍스트 파일을 읽었습니다."

    return (
        "unsupported",
        "",
        "PDF, PNG, JPG, WEBP, TXT, Markdown, JSON 파일만 지원합니다.",
    )


def _extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    if len(reader.pages) > MAX_PDF_PAGES:
        raise ValueError(f"PDF는 {MAX_PDF_PAGES}쪽 이하만 올릴 수 있습니다.")
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(page.strip() for page in pages if page.strip())


def _extract_image_text(content: bytes) -> tuple[str, str]:
    """Run Korean OCR when the optional local OCR packages are installed."""
    try:
        from io import BytesIO

        from PIL import Image
        import pytesseract
    except ImportError:
        return "", "사진 OCR 패키지가 아직 설치되지 않았습니다. 직접 적기나 PDF를 사용해주세요."

    try:
        image = Image.open(BytesIO(content))
        try:
            text = pytesseract.image_to_string(image, lang="kor+eng")
        except Exception:
            text = pytesseract.image_to_string(image, lang="eng")
    except Exception:
        return "", "사진에서 글자를 읽지 못했습니다. 사진을 밝게 다시 찍어주세요."

    cleaned = text.strip()
    if not cleaned:
        return "", "사진에서 글자를 찾지 못했습니다. 약관을 가까이서 선명하게 다시 찍어주세요."
    return cleaned, "사진 속 글자를 OCR로 읽었습니다. 중요한 문장이 맞는지 확인해주세요."
