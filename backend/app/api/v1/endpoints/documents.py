from fastapi import APIRouter

from app.schemas.document import DocumentExportRequest, DocumentExportResponse
from app.services.document_exporter import export_document

router = APIRouter()


@router.post("/export", response_model=DocumentExportResponse)
def export(request: DocumentExportRequest) -> DocumentExportResponse:
    return export_document(
        title=request.title,
        body=request.body,
        attachments=request.attachments,
        export_format=request.export_format,
    )

