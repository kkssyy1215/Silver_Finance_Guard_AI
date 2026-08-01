from __future__ import annotations

import os
import tempfile
from pathlib import Path


_model = None


def transcribe_audio(content: bytes, filename: str | None) -> tuple[str, bool, str]:
    """Transcribe audio locally when faster-whisper is installed and configured."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return "", False, "음성 입력을 사용하려면 faster-whisper 패키지를 설치해주세요. 직접 적기도 사용할 수 있습니다."

    global _model
    try:
        if _model is None:
            model_size = os.getenv("WHISPER_MODEL_SIZE", "tiny")
            _model = WhisperModel(model_size, device="cpu", compute_type="int8")
        suffix = Path(filename or "recording.wav").suffix or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix) as audio_file:
            audio_file.write(content)
            audio_file.flush()
            segments, _ = _model.transcribe(str(audio_file.name), language="ko", vad_filter=True)
            text = " ".join(segment.text.strip() for segment in segments).strip()
    except Exception:
        return "", False, "음성을 글자로 바꾸지 못했습니다. 다시 녹음해주세요."

    if not text:
        return "", False, "음성이 너무 짧거나 잘 들리지 않습니다. 조금 더 천천히 말해주세요."
    return text, True, "음성을 글자로 바꿨습니다. 내용을 확인한 뒤 분석을 시작해주세요."
