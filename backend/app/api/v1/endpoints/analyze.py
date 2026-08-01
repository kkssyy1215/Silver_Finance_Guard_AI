from fastapi import APIRouter, File, UploadFile

from app.schemas.analysis import (
    ContractRiskResponse,
    ExplanationRiskResponse,
    ExtractedDocumentText,
    AudioTranscriptionResponse,
    TextAnalysisRequest,
)
from app.services.document_parser import extract_text_from_upload
from app.services.audio_transcriber import transcribe_audio
from app.services.explanation_detector import analyze_explanation_risk
from app.services.risk_detector import analyze_contract_risk

router = APIRouter()


@router.post("/document", response_model=ContractRiskResponse)
def analyze_document(request: TextAnalysisRequest) -> ContractRiskResponse:
    return analyze_contract_risk(request)


@router.post("/document-file", response_model=ContractRiskResponse)
async def analyze_document_file(file: UploadFile = File(...)) -> ContractRiskResponse:
    source_type, text, quality_message = await extract_text_from_upload(file)
    if not text:
        return ContractRiskResponse(
            overall_risk="unknown",
            document_summary={
                "one_line": "문서를 읽지 못했습니다.",
                "easy_summary": quality_message,
                "next_action": "PDF나 텍스트 파일로 다시 올려주세요.",
            },
            risk_items=[],
            must_ask_questions=[],
            references=[],
            disclaimer="이 결과는 법적 판단이 아니라 소비자 보호를 위한 확인 보조 정보입니다.",
        )
    return analyze_contract_risk(TextAnalysisRequest(content=text, content_type=source_type))


@router.post("/extract-text", response_model=ExtractedDocumentText)
async def extract_text(file: UploadFile = File(...)) -> ExtractedDocumentText:
    source_type, text, quality_message = await extract_text_from_upload(file)
    return ExtractedDocumentText(source_type=source_type, text=text, quality_message=quality_message)


@router.post("/explanation-risk", response_model=ExplanationRiskResponse)
def analyze_explanation(request: TextAnalysisRequest) -> ExplanationRiskResponse:
    return analyze_explanation_risk(request)


@router.post("/transcribe-audio", response_model=AudioTranscriptionResponse)
async def transcribe_audio_file(file: UploadFile = File(...)) -> AudioTranscriptionResponse:
    content = await file.read()
    text, available, message = transcribe_audio(content, file.filename)
    return AudioTranscriptionResponse(text=text, available=available, message=message)
