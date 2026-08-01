"use client";

import { ReactNode, useEffect, useRef, useState } from "react";
import { BookOpen, Contrast, Eye, FileText, FileUp, MessageSquareWarning, Mic, Minus, Phone, Plus, Search, ShieldCheck, Siren, Square, Volume2 } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { getJson, postFile, postJson } from "@/lib/api";

type TabKey = "check" | "terms" | "incident" | "complaint";
type InputMode = "text" | "file" | "voice";
type JsonRecord = Record<string, any>;
type BrowserSpeechRecognition = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: any) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};
type BrowserSpeechRecognitionConstructor = new () => BrowserSpeechRecognition;

const tabItems: { key: TabKey; title: string; description: string; icon: typeof ShieldCheck }[] = [
  { key: "check", title: "가입 전 확인", description: "약관·문자의 위험 표현 찾기", icon: ShieldCheck },
  { key: "terms", title: "금융용어 검색", description: "어려운 단어를 쉬운 말로 보기", icon: Search },
  { key: "incident", title: "금융사고 대응", description: "잘못 보낸 돈·보이스피싱 대처", icon: Siren },
  { key: "complaint", title: "민원서 작성", description: "있었던 일을 접수 문장으로 정리", icon: FileText },
];

const sampleContract = "별도 해지 신청이 없는 경우 계약은 자동 연장됩니다. 마케팅 목적의 개인정보 제3자 제공에 동의합니다. 본 조건은 오늘만 제공되며 조기 종료될 수 있습니다.";
const incidentSamples = [
  "계좌번호를 잘못 눌러서 모르는 사람에게 30만원 보냈어요.",
  "검찰이라고 전화가 와서 앱을 깔고 100만원을 보냈어요.",
  "직접 만나 현금을 전달했어요.",
];
const complaintTypes = [
  ["general_complaint", "일반 금융 민원"],
  ["mistaken_transfer", "착오송금"],
  ["voice_phishing", "보이스피싱 의심"],
  ["mis_selling", "불완전판매 의심"],
];

const riskLabels: Record<string, string> = {
  low: "낮음", medium: "주의", high: "높음", critical: "긴급", unknown: "확인 필요",
};
const incidentLabels: Record<string, string> = {
  mistaken_transfer: "착오송금", voice_phishing: "보이스피싱 의심", general_complaint: "일반 금융 민원", mis_selling: "불완전판매 의심", unknown: "상황 확인 필요",
};
const riskItemLabels: Record<string, string> = {
  auto_renewal: "자동 연장", excessive_penalty: "과도한 위약금", third_party_data: "개인정보 제3자 제공", principal_guarantee_misleading: "원금 보장 오해", pressure_sales: "급한 가입 압박", unclear_fee: "수수료 불명확", termination_limit: "해지 제한",
};
const explanationLabels: Record<string, string> = {
  missing_risk_explanation: "손실 위험 설명 부족", exaggerated_return: "수익 과장 표현", principal_guarantee_misleading: "원금 보장 오해", omitted_fee: "비용 설명 부족", pressure_sales: "급한 가입 압박", suitability_risk: "내 상황에 맞는지 확인 필요",
};

function label(map: Record<string, string>, key: string): string { return map[key] ?? "확인 필요"; }

function HighlightedText({ text, keywords }: { text: string; keywords?: string[] }) {
  const active = (keywords ?? []).filter(Boolean).sort((a, b) => b.length - a.length);
  if (!text || active.length === 0) return <>{text}</>;
  const pattern = new RegExp(`(${active.map((item) => item.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "gi");
  return <>{text.split(pattern).map((part, index) => active.some((word) => word.toLowerCase() === part.toLowerCase()) ? <mark key={`${part}-${index}`}>{part}</mark> : <span key={`${part}-${index}`}>{part}</span>)}</>;
}

function SpeakButton({ text, labelText = "읽어주기" }: { text: string; labelText?: string }) {
  const speak = () => {
    if (typeof window === "undefined" || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(text.slice(0, 4000)));
  };
  return <div className="action-row"><button className="secondary-button icon-button" type="button" onClick={speak}><Volume2 size={19} aria-hidden="true" /> {labelText}</button><button className="secondary-button icon-button" type="button" onClick={() => window.speechSynthesis?.cancel()}><Square size={17} aria-hidden="true" /> 읽기 멈추기</button></div>;
}

function ReferenceList({ references }: { references?: JsonRecord[] }) {
  if (!references?.length) return null;
  return <details className="reference"><summary>공식 근거 보기</summary><div className="reference-body">{references.map((reference, index) => <div className="reference-item" key={`${reference.source_id ?? reference.title}-${index}`}><p><strong>{reference.title}</strong>{reference.publisher ? ` · ${reference.publisher}` : ""}{reference.published_at ? ` · ${reference.published_at}` : ""}</p><p>{reference.summary}</p>{reference.application_reason && <p>이 자료를 적용한 이유: {reference.application_reason}</p>}{reference.url && <a href={reference.url} target="_blank" rel="noreferrer">공식 원문 열기</a>}</div>)}</div></details>;
}

function ErrorNotice({ message }: { message: string }) { return <div className="notice warning" role="alert">{message}</div>; }

function redactSensitiveText(text: string): string {
  return text
    .replace(/\b\d{6}[- ]?\d{7}\b/g, "[주민등록번호 가림]")
    .replace(/(비밀번호|인증번호|보안카드|pin)\s*[:：]?\s*[^\s,.!?]+/gi, "$1 [가림]")
    .replace(/\b\d{10,16}\b/g, "[계좌번호 가림]");
}

function sensitiveLabels(text: string): string[] {
  const labels: string[] = [];
  if (/\b\d{6}[- ]?\d{7}\b/.test(text)) labels.push("주민등록번호");
  if (/(비밀번호|인증번호|보안카드|pin)\s*[:：]?\s*[^\s,.!?]+/i.test(text)) labels.push("비밀번호·인증번호");
  if (/\b\d{10,16}\b/.test(text)) labels.push("계좌번호");
  return labels;
}

function PrivacyGuard({ text, onMask }: { text: string; onMask: () => void }) {
  const labels = sensitiveLabels(text);
  if (!labels.length) return null;
  return <div className="privacy-warning" role="alert"><strong>개인정보가 보입니다.</strong><span>{labels.join(", ")}는 분석 전에 가리는 것이 안전합니다.</span><button className="secondary-button" type="button" onClick={onMask}>민감한 정보 가리기</button></div>;
}

function useVoiceInput(onText: (text: string) => void, setError: (message: string) => void, filename: string) {
  const [recording, setRecording] = useState(false);
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    setError("");
    const speechWindow = window as typeof window & {
      SpeechRecognition?: BrowserSpeechRecognitionConstructor;
      webkitSpeechRecognition?: BrowserSpeechRecognitionConstructor;
    };
    const Recognition = speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;

    if (Recognition) {
      const recognition = new Recognition();
      recognition.lang = "ko-KR";
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.onresult = (event) => {
        const transcript = event.results?.[0]?.[0]?.transcript?.trim();
        if (transcript) onText(transcript);
        else setError("음성을 또렷하게 듣지 못했습니다. 천천히 다시 말해주세요.");
      };
      recognition.onerror = () => setError("음성을 듣지 못했습니다. 마이크 권한을 확인하거나 직접 적어주세요.");
      recognition.onend = () => {
        recognitionRef.current = null;
        setRecording(false);
      };
      recognitionRef.current = recognition;
      recognition.start();
      setRecording(true);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (event) => { if (event.data.size) chunksRef.current.push(event.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const audio = new File([new Blob(chunksRef.current, { type: "audio/webm" })], filename, { type: "audio/webm" });
        try {
          const data = await postFile<JsonRecord>("/api/v1/analyze/transcribe-audio", audio);
          if (data.text) onText(data.text);
          else setError(data.message ?? "음성을 글자로 바꾸지 못했습니다.");
        } catch (caught) {
          setError(caught instanceof Error ? caught.message : "음성 변환에 실패했습니다.");
        } finally {
          recorderRef.current = null;
          setRecording(false);
        }
      };
      recorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch {
      setError("마이크를 사용할 수 없습니다. 브라우저 권한을 확인하거나 직접 적어주세요.");
    }
  };

  const stopRecording = () => {
    recognitionRef.current?.stop();
    recorderRef.current?.stop();
    recognitionRef.current = null;
    setRecording(false);
  };

  return { recording, startRecording, stopRecording };
}

function FileMode({ onFile, busy }: { onFile: (file: File) => void; busy: boolean }) {
  return <div className="upload-box"><label className="field-label icon-label" htmlFor="document-file"><FileUp size={19} aria-hidden="true" /> PDF, 사진 또는 텍스트 파일</label><input id="document-file" type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,.txt,.md,.json" disabled={busy} onChange={(event) => { const file = event.target.files?.[0]; if (file) onFile(file); }} /><p className="input-help">파일을 읽은 뒤 문장을 직접 고칠 수 있습니다. {busy ? "파일을 읽는 중입니다." : "개인정보는 올리기 전에 지워주세요."}</p></div>;
}

function ModeChoice({ name, value, checked, onChange, children }: { name: string; value: string; checked: boolean; onChange: () => void; children: ReactNode }) {
  return <div className="mode-choice"><input id={`${name}-${value}`} type="radio" name={name} checked={checked} onChange={onChange} /><label htmlFor={`${name}-${value}`}>{children}</label></div>;
}

function GuardianShare({ title, summary, details }: { title: string; summary: string; details?: string[] }) {
  const [message, setMessage] = useState("");
  const shareText = redactSensitiveText([`실버 금융가드: ${title}`, summary, ...(details ?? [])].filter(Boolean).join("\n"));
  const encodedText = encodeURIComponent(shareText);
  const share = async () => {
    try {
      if (navigator.share) { await navigator.share({ title: "실버 금융가드 결과", text: shareText }); setMessage("공유 화면을 열었습니다."); }
      else if (navigator.clipboard) { await navigator.clipboard.writeText(shareText); setMessage("요약을 복사했습니다. 문자나 메신저에 붙여 넣으세요."); }
      else setMessage("이 기기에서는 공유 기능을 사용할 수 없습니다. 출력하기를 이용해주세요.");
    } catch { setMessage("공유를 취소했습니다."); }
  };
  return <details className="guardian-share"><summary>보호자에게 공유</summary><div className="guardian-share-body"><p className="input-help">계좌번호, 비밀번호 등 민감한 정보는 가린 요약만 공유합니다.</p><div className="guardian-preview">{shareText}</div><div className="share-actions"><button className="secondary-button" type="button" onClick={() => void share()}>문자·공유</button><a className="secondary-button" href={`sms:?&body=${encodedText}`}>문자로 보내기</a><button className="secondary-button" type="button" onClick={() => window.print()}>출력하기</button></div>{message && <p className="input-help" role="status">{message}</p>}<div className="qr-wrap"><QRCodeSVG value={shareText.slice(0, 900)} size={156} includeMargin aria-label="보호자 공유용 QR 코드" /><span>휴대폰으로 찍으면 요약 내용을 볼 수 있습니다.</span></div></div></details>;
}

export default function FinanceGuardApp() {
  const [tab, setTab] = useState<TabKey>("check");
  const [scale, setScale] = useState<"normal" | "large" | "xlarge">("large");
  const [highContrast, setHighContrast] = useState(false);
  const [magnifier, setMagnifier] = useState(false);
  const [error, setError] = useState("");
  const contentRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const restorePreferences = window.setTimeout(() => {
      const savedScale = window.localStorage.getItem("silver-font-scale") as "normal" | "large" | "xlarge" | null;
      if (savedScale) setScale(savedScale);
      const savedContrast = window.localStorage.getItem("silver-high-contrast");
      if (savedContrast) setHighContrast(savedContrast === "true");
    }, 0);
    return () => window.clearTimeout(restorePreferences);
  }, []);
  useEffect(() => { window.localStorage.setItem("silver-font-scale", scale); }, [scale]);
  useEffect(() => { window.localStorage.setItem("silver-high-contrast", String(highContrast)); }, [highContrast]);

  const sizes = ["normal", "large", "xlarge"] as const;
  const sizeIndex = sizes.indexOf(scale);
  const sizeLabel = scale === "normal" ? "보통" : scale === "large" ? "크게" : "아주 크게";
  const changeSize = (direction: -1 | 1) => setScale(sizes[Math.max(0, Math.min(sizes.length - 1, sizeIndex + direction))]);
  const changeTab = (next: TabKey) => {
    setTab(next);
    setError("");
    window.setTimeout(() => contentRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 0);
  };

  return <div className={`app-shell ${scale === "large" ? "scale-large" : scale === "xlarge" ? "scale-xlarge" : ""} ${highContrast ? "high-contrast" : ""}`}>
    <div className="top-rule" />
    <main className="page-wrap">
      <header className="site-header">
        <div className="brand"><div className="eyebrow">금융소비자 보호 서비스</div><h1>실버 금융가드</h1><p>어려운 금융 내용을 쉬운 말로 확인하고, 지금 할 일을 안내받으세요.</p></div>
        <div className="tool-box" aria-label="보기 설정"><span className="tool-label">보기 설정</span><div className="size-control" aria-label="글자 크기"><button type="button" aria-label="글자 작게" disabled={sizeIndex === 0} onClick={() => changeSize(-1)}><Minus size={20} aria-hidden="true" /></button><strong aria-live="polite">{sizeLabel}</strong><button type="button" aria-label="글자 크게" disabled={sizeIndex === sizes.length - 1} onClick={() => changeSize(1)}><Plus size={20} aria-hidden="true" /></button></div><button className={`tool-button icon-button ${highContrast ? "active" : ""}`} type="button" aria-pressed={highContrast} onClick={() => setHighContrast((value) => !value)}><Contrast size={19} aria-hidden="true" /> {highContrast ? "고대비 끄기" : "고대비 보기"}</button><button className={`tool-button icon-button ${magnifier ? "active" : ""}`} type="button" aria-pressed={magnifier} onClick={() => setMagnifier((value) => !value)}><Eye size={19} aria-hidden="true" /> 입력 크게 보기</button></div>
      </header>

      <section className="service-picker" aria-labelledby="service-picker-title"><div className="service-picker-heading"><span>1단계</span><h2 id="service-picker-title">무엇을 도와드릴까요?</h2></div><nav className="service-grid" aria-label="주요 기능">{tabItems.map((item) => { const Icon = item.icon; return <button key={item.key} type="button" className={`service-button ${tab === item.key ? "active" : ""} ${item.key === "incident" ? "urgent" : ""}`} aria-current={tab === item.key ? "page" : undefined} onClick={() => changeTab(item.key)}><Icon size={25} aria-hidden="true" /><span><strong>{item.title}</strong><small>{item.description}</small></span></button>; })}</nav></section>

      <section className="content-panel" ref={contentRef} tabIndex={-1}>{tab === "check" && <ContractCheck magnifier={magnifier} setError={setError} error={error} />} {tab === "terms" && <TermSearch magnifier={magnifier} setError={setError} error={error} />} {tab === "incident" && <IncidentResponse magnifier={magnifier} setError={setError} error={error} />} {tab === "complaint" && <ComplaintDraft setError={setError} error={error} />}</section>
      <p className="footer-note">이 서비스는 공식 자료 기반의 확인 보조 도구입니다. 최종 가입·신고·민원 제출 전에는 해당 금융회사와 공식 기관의 최신 안내를 함께 확인하세요.</p>
    </main>
  </div>;
}

function ContractCheck({ magnifier, setError, error }: { magnifier: boolean; setError: (value: string) => void; error: string }) {
  const [mode, setMode] = useState<InputMode>("text");
  const [text, setText] = useState("");
  const [analysisKind, setAnalysisKind] = useState<"contract" | "explanation">("contract");
  const [result, setResult] = useState<JsonRecord | null>(null);
  const [loading, setLoading] = useState("");
  const [fileLoading, setFileLoading] = useState(false);
  const [fileMessage, setFileMessage] = useState("");
  const resultRef = useRef<HTMLDivElement | null>(null);
  const { recording, startRecording, stopRecording } = useVoiceInput((voiceText) => {
    setText(voiceText);
    setMode("text");
    setFileMessage("음성을 글자로 바꿨습니다. 잘못 읽은 부분이 없는지 확인하고 고쳐주세요.");
  }, setError, "voice-input.webm");

  useEffect(() => {
    if (result) resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [result]);

  const runAnalysis = async (kind: "contract" | "explanation") => {
    setError(""); setResult(null); setLoading(kind);
    try {
      if (!text.trim()) throw new Error("확인할 문장이나 상담 내용을 입력해주세요.");
      const data = await postJson<JsonRecord>(kind === "contract" ? "/api/v1/analyze/document" : "/api/v1/analyze/explanation-risk", { content: redactSensitiveText(text), content_type: "text", user_age_group: "senior" });
      setResult({ ...data, kind });
    } catch (caught) { setError(caught instanceof Error ? caught.message : "분석에 실패했습니다."); }
    finally { setLoading(""); }
  };

  const handleFile = async (selectedFile: File) => {
    setFileMessage(""); setError(""); setFileLoading(true);
    try {
      const extracted = await postFile<JsonRecord>("/api/v1/analyze/extract-text", selectedFile);
      if (!extracted.text) throw new Error(extracted.quality_message ?? "파일에서 글자를 읽지 못했습니다.");
      setText(extracted.text); setMode("text"); setFileMessage(extracted.quality_message ?? "파일을 읽었습니다. 내용을 확인하고 고쳐주세요.");
    } catch (caught) { setError(caught instanceof Error ? caught.message : "파일을 읽지 못했습니다."); }
    finally { setFileLoading(false); }
  };

  return <><div className="panel-heading"><div><span className="panel-label">2단계 · 내용 넣기</span><h2>가입 전에 확인하기</h2><p>받은 문자, 약관 또는 상담 내용을 그대로 넣어주세요.</p></div></div><div className="choice-block"><strong className="choice-title">무엇을 확인할까요?</strong><div className="analysis-choice-row"><button type="button" className={analysisKind === "contract" ? "analysis-choice active" : "analysis-choice"} aria-pressed={analysisKind === "contract"} onClick={() => setAnalysisKind("contract")}><BookOpen size={22} aria-hidden="true" /><span><strong>약관·문자 확인</strong><small>불리하거나 위험한 표현을 찾아요</small></span></button><button type="button" className={analysisKind === "explanation" ? "analysis-choice active" : "analysis-choice"} aria-pressed={analysisKind === "explanation"} onClick={() => setAnalysisKind("explanation")}><MessageSquareWarning size={22} aria-hidden="true" /><span><strong>상담 설명 확인</strong><small>직원이 빠뜨린 설명을 살펴봐요</small></span></button></div></div><div className="input-section"><strong className="choice-title">어떻게 넣을까요?</strong><div className="mode-row"><ModeChoice name="contract-mode" value="text" checked={mode === "text"} onChange={() => setMode("text")}>직접 입력</ModeChoice><ModeChoice name="contract-mode" value="file" checked={mode === "file"} onChange={() => setMode("file")}>사진·PDF</ModeChoice><ModeChoice name="contract-mode" value="voice" checked={mode === "voice"} onChange={() => setMode("voice")}>음성 입력</ModeChoice></div>{mode === "file" ? <FileMode onFile={(selectedFile) => void handleFile(selectedFile)} busy={fileLoading} /> : mode === "voice" ? <div className="voice-box"><p>상담 내용이나 문자를 천천히 읽어주세요.</p><button type="button" className={recording ? "secondary-button icon-button" : "primary-button icon-button"} onClick={recording ? stopRecording : startRecording}>{recording ? <><Square size={18} aria-hidden="true" /> 녹음 끝내기</> : <><Mic size={18} aria-hidden="true" /> 녹음 시작</>}</button>{recording && <span className="recording" role="status">녹음 중입니다. 말이 끝나면 녹음 끝내기를 누르세요.</span>}</div> : <div><div className="field-heading"><label className="field-label" htmlFor="contract-text">확인할 내용</label><button className="text-button" type="button" onClick={() => setText(sampleContract)}>예시 넣기</button></div><textarea id="contract-text" value={text} onChange={(event) => setText(event.target.value)} placeholder="문자나 약관 내용을 여기에 적어주세요." />{fileMessage && <div className="notice success" role="status">{fileMessage}</div>}<PrivacyGuard text={text} onMask={() => setText(redactSensitiveText(text))} />{magnifier && text.trim() && <div className="magnifier"><strong>입력한 내용 크게 보기</strong>{text}</div>}<button className="primary-button full-button" type="button" aria-busy={Boolean(loading)} disabled={Boolean(loading) || fileLoading || !text.trim()} onClick={() => void runAnalysis(analysisKind)}>{loading ? "내용을 확인하고 있습니다..." : "내용 확인하기"}</button></div>}</div>{error && <ErrorNotice message={error} />}{result && <div ref={resultRef}><ContractResult result={result} /></div>}</>;
}

function ContractResult({ result }: { result: JsonRecord }) {
  const isExplanation = result.kind === "explanation";
  const items = isExplanation ? result.suspicious_points ?? [] : result.risk_items ?? [];
  const overall = result.overall_risk ?? result.risk_level ?? "unknown";
  const itemName = (item: JsonRecord) => isExplanation ? label(explanationLabels, item.label) : label(riskItemLabels, item.label);
  return <section className="result-area" aria-labelledby="contract-result-title"><div className="result-heading"><span>3단계 · 결과 확인</span><h2 id="contract-result-title">확인 결과</h2></div><div className="score"><strong>{label(riskLabels, overall)}</strong><span>{result.document_summary?.one_line ?? result.summary?.one_line ?? "확인 결과를 읽어보세요."}<small>위험 확정이 아니라, 다시 확인하면 좋은 부분입니다.</small></span></div><div className="result-stack">{items.length === 0 ? <div className="empty"><strong>큰 위험 신호는 찾지 못했습니다.</strong><span>그래도 가입 전에는 공식 설명서의 손실 가능성, 수수료, 해지 조건을 확인하세요.</span></div> : items.map((item: JsonRecord, index: number) => { const text = item.original_text ?? item.detected_text ?? ""; const easy = item.simplified_text ?? item.easy_explanation ?? ""; const reason = item.why_it_matters ?? item.reason ?? ""; return <article className="result-card" key={`${item.label}-${index}`}><div className="result-card-top"><h3>{itemName(item)}</h3><div><span className="status-pill">{label(riskLabels, item.severity)}</span><span className="status-pill blue">{item.review_status ?? "확인 필요"}</span></div></div><p className="easy-summary">{easy}</p><div className="detected-block"><strong>찾은 문장</strong><div className="highlighted-text"><HighlightedText text={text} keywords={item.detected_keywords} /></div></div><div className="decision-grid"><div><strong>왜 확인해야 하나요?</strong><p>{reason}</p></div><div className="question"><strong>직원에게 이렇게 물어보세요</strong><p>{item.must_ask_question}</p></div></div><SpeakButton text={`${easy}. 직원에게 물어볼 말은 ${item.must_ask_question}`} labelText="쉽게 읽어주기" /><ReferenceList references={item.official_references} /></article>; })}{result.must_ask_questions?.length > 0 && <div className="result-card question-card"><h3>직원에게 보여줄 질문</h3><ol>{result.must_ask_questions.map((question: string) => <li key={question}>{question}</li>)}</ol></div>}<ReferenceList references={result.references} /><GuardianShare title="가입 전 확인 결과" summary={result.document_summary?.one_line ?? result.summary?.one_line ?? "확인 결과를 확인해주세요."} details={items.slice(0, 4).map((item: JsonRecord) => `${itemName(item)}: ${item.simplified_text ?? item.easy_explanation ?? "확인 필요"}`)} /></div></section>;
}

function TermSearch({ magnifier, setError, error }: { magnifier: boolean; setError: (value: string) => void; error: string }) {
  const [query, setQuery] = useState("");
  const [terms, setTerms] = useState<JsonRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const resultRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => { if (searched) resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }); }, [searched, terms]);
  const search = async (nextQuery = query) => { const cleaned = nextQuery.trim(); if (!cleaned) { setError("궁금한 금융 단어를 입력해주세요."); return; } setQuery(cleaned); setError(""); setLoading(true); setSearched(false); try { const data = await getJson<{ terms: JsonRecord[] }>("/api/v1/official-data/terms/search", { query: cleaned, limit: 5 }); setTerms(data.terms); setSearched(true); } catch (caught) { setError(caught instanceof Error ? caught.message : "금융용어 검색에 실패했습니다."); } finally { setLoading(false); } };
  return <><div className="panel-heading"><div><span className="panel-label">2단계 · 단어 입력</span><h2>어려운 금융 단어 찾기</h2><p>궁금한 단어 하나를 입력하면 먼저 쉬운 말로 설명합니다.</p></div></div><div className="term-search-row"><label className="sr-only" htmlFor="term-query">궁금한 금융 단어</label><input id="term-query" type="text" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void search(); }} placeholder="예: 예금자보호" /><button className="primary-button icon-button" type="button" onClick={() => void search()} disabled={loading || !query.trim()}><Search size={20} aria-hidden="true" /> {loading ? "찾는 중..." : "검색"}</button></div><div className="quick-terms" aria-label="자주 찾는 금융용어"><span>자주 찾는 단어</span>{["예금자보호", "지급정지", "청약철회", "중도상환수수료"].map((term) => <button type="button" key={term} onClick={() => void search(term)}>{term}</button>)}</div>{magnifier && query.trim() && <div className="magnifier"><strong>검색할 단어 크게 보기</strong>{query}</div>}{error && <ErrorNotice message={error} />}{searched && <div ref={resultRef} className="result-area"><div className="result-heading"><span>3단계 · 뜻 확인</span><h2>검색 결과</h2></div>{terms.length > 0 ? <><div className="search-summary">{terms.some((term) => term.match_type === "exact") ? "입력한 단어와 정확히 일치하는 뜻입니다." : `‘${query}’와 정확히 같은 단어가 없어 관련된 용어를 보여드립니다.`}</div><div className="result-stack">{terms.map((term, index) => <article className="result-card term-card" key={`${term.term}-${index}`}><div className="result-card-top"><h3>{term.term}</h3><span className="status-pill blue">{term.match_type === "exact" ? "정확히 일치" : "관련 용어"}</span></div><strong className="result-label">쉽게 말하면</strong><p className="easy-summary">{term.easy_explanation}</p>{term.action_tip && <div className="question"><strong>기억할 점</strong><p>{term.action_tip}</p></div>}<SpeakButton text={`${term.term}. 쉽게 말하면 ${term.easy_explanation}`} labelText="뜻 읽어주기" /><details className="reference"><summary>공식 정의와 출처 보기</summary><div className="reference-body"><p>{term.official_definition || "공식 정의가 등록되지 않았습니다."}</p><p><strong>출처</strong> · {term.source_title}</p>{term.source_url && <a href={term.source_url} target="_blank" rel="noreferrer">공식 출처 열기</a>}</div></details></article>)}</div></> : <div className="empty"><strong>일치하는 단어를 찾지 못했습니다.</strong><span>단어를 짧게 바꾸어 다시 검색해보세요.</span></div>}</div>}</>;
}

function IncidentResponse({ magnifier, setError, error }: { magnifier: boolean; setError: (value: string) => void; error: string }) {
  const [mode, setMode] = useState<"text" | "voice">("text");
  const [content, setContent] = useState("");
  const [voiceMessage, setVoiceMessage] = useState("");
  const [bankPhone, setBankPhone] = useState("");
  const [companyQuery, setCompanyQuery] = useState("");
  const [companies, setCompanies] = useState<JsonRecord[]>([]);
  const [companyLoading, setCompanyLoading] = useState(false);
  const [incident, setIncident] = useState<JsonRecord | null>(null);
  const [plan, setPlan] = useState<JsonRecord | null>(null);
  const [loading, setLoading] = useState(false);
  const resultRef = useRef<HTMLDivElement | null>(null);
  const digits = bankPhone.replace(/[^0-9+]/g, "");
  const { recording, startRecording, stopRecording } = useVoiceInput((voiceText) => {
    setContent(voiceText);
    setMode("text");
    setVoiceMessage("음성을 글자로 바꿨습니다. 잘못 읽은 부분이 없는지 확인하고 고쳐주세요.");
  }, setError, "incident-voice.webm");
  useEffect(() => { if (incident && plan) resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }); }, [incident, plan]);
  const run = async () => { if (!content.trim()) { setError("무슨 일이 있었는지 한 문장으로 적어주세요."); return; } setError(""); setIncident(null); setPlan(null); setLoading(true); try { const safeContent = redactSensitiveText(content); const classified = await postJson<JsonRecord>("/api/v1/incidents/classify", { content: safeContent }); const actionPlan = await postJson<JsonRecord>("/api/v1/incidents/action-plan", { incident_type: classified.incident_type, content: safeContent }); setIncident(classified); setPlan(actionPlan); } catch (caught) { setError(caught instanceof Error ? caught.message : "사고 대응 분석에 실패했습니다."); } finally { setLoading(false); } };
  const searchCompanies = async () => { if (!companyQuery.trim()) return; setCompanyLoading(true); setError(""); try { const data = await getJson<{ records: JsonRecord[] }>("/api/v1/official-data/records/search", { query: companyQuery, dataset_id: "KDIC_INSURED_FINANCIAL_COMPANIES_20250930", limit: 6 }); setCompanies(data.records); if (!data.records.length) setError("공식 목록에서 금융회사를 찾지 못했습니다. 기관명을 다시 확인해주세요."); } catch (caught) { setError(caught instanceof Error ? caught.message : "금융회사 검색에 실패했습니다."); } finally { setCompanyLoading(false); } };
  return <><div className="panel-heading"><div><span className="panel-label">긴급할 때 가장 먼저</span><h2>금융사고 대응</h2><p>돈을 보냈거나 개인정보를 알려줬다면 바로 신고부터 하세요.</p></div></div><div className="emergency-box"><strong>지금 피해가 진행 중인가요?</strong><p>분석 결과를 기다리지 말고 먼저 전화하세요.</p><div className="emergency-actions"><a className="call-button danger icon-button" href="tel:112"><Phone size={21} aria-hidden="true" /> 경찰 112 신고</a><a className="call-button icon-button" href="tel:1332"><Phone size={21} aria-hidden="true" /> 금융감독원 1332</a></div></div><div className="input-section"><strong className="choice-title">무슨 일이 있었나요?</strong><div className="sample-buttons" aria-label="사고 상황 예시">{[["잘못 송금", incidentSamples[0]], ["전화 사기", incidentSamples[1]], ["현금 전달", incidentSamples[2]]].map(([title, sample]) => <button type="button" key={title} onClick={() => { setContent(sample); setMode("text"); }}>{title}</button>)}</div><div className="mode-row"><ModeChoice name="incident-mode" value="text" checked={mode === "text"} onChange={() => setMode("text")}>직접 입력</ModeChoice><ModeChoice name="incident-mode" value="voice" checked={mode === "voice"} onChange={() => setMode("voice")}>음성 입력</ModeChoice></div>{mode === "voice" ? <div className="voice-box"><p>사고 상황을 천천히 말해주세요.</p><button type="button" className={recording ? "secondary-button icon-button" : "primary-button icon-button"} onClick={recording ? stopRecording : startRecording}>{recording ? <><Square size={18} aria-hidden="true" /> 녹음 끝내기</> : <><Mic size={18} aria-hidden="true" /> 녹음 시작</>}</button>{recording && <span className="recording" role="status">녹음 중입니다.</span>}</div> : <><label className="sr-only" htmlFor="incident-content">사고 상황</label><textarea id="incident-content" value={content} onChange={(event) => setContent(event.target.value)} placeholder="예: 모르는 사람에게 돈을 잘못 보냈어요." />{voiceMessage && <div className="notice success" role="status">{voiceMessage}</div>}<PrivacyGuard text={content} onMask={() => setContent(redactSensitiveText(content))} />{magnifier && content.trim() && <div className="magnifier"><strong>사고 상황 크게 보기</strong>{content}</div>}<details className="company-finder"><summary>송금한 금융회사 연락처 찾기</summary><div className="company-finder-body"><div className="company-search-row"><label className="sr-only" htmlFor="company-query">금융회사 이름</label><input id="company-query" type="text" value={companyQuery} onChange={(event) => setCompanyQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void searchCompanies(); }} placeholder="예: 국민은행" /><button className="secondary-button" type="button" onClick={() => void searchCompanies()} disabled={companyLoading}>{companyLoading ? "찾는 중" : "연락처 찾기"}</button></div><p className="input-help">예금보험공사 공식 금융회사 목록을 사용합니다. 실제 고객센터 번호는 카드 뒷면이나 공식 앱에서도 확인하세요.</p>{companies.length > 0 && <div className="company-results">{companies.map((company, index) => <button className="company-result" type="button" key={`${company.title}-${index}`} onClick={() => { setBankPhone(company.metadata?.phone ?? ""); setCompanyQuery(company.title); setCompanies([]); }}><strong>{company.title}</strong><span>{company.metadata?.phone || "전화번호 없음"}</span></button>)}</div>}<label className="field-label" htmlFor="bank-phone">선택한 연락처</label><input id="bank-phone" type="tel" value={bankPhone} onChange={(event) => setBankPhone(event.target.value)} placeholder="번호를 선택하거나 입력하세요" />{digits && <a className="call-button compact icon-button" href={`tel:${digits}`}><Phone size={19} aria-hidden="true" /> 이 번호로 전화하기</a>}</div></details><button className="primary-button full-button" type="button" aria-busy={loading} onClick={() => void run()} disabled={loading || !content.trim()}>{loading ? "지금 할 일을 찾고 있습니다..." : "지금 할 일 확인하기"}</button></>}</div>{error && <ErrorNotice message={error} />}{incident && plan && <div ref={resultRef}><IncidentResult incident={incident} plan={plan} bankPhone={digits} /></div>}</>;
}

function IncidentResult({ incident, plan, bankPhone }: { incident: JsonRecord; plan: JsonRecord; bankPhone: string }) {
  const steps = [["지금 바로 할 일", plan.immediate], ["10분 안에 할 일", plan.within_10min], ["오늘 할 일", plan.today], ["이후 준비할 일", plan.follow_up]] as [string, JsonRecord[]][];
  return <section className="result-area" aria-labelledby="incident-result-title"><div className="result-heading"><span>다음 단계 · 바로 행동</span><h2 id="incident-result-title">지금 할 일</h2></div><div className="score"><strong>{label(riskLabels, incident.urgency_level)}</strong><span><b>{label(incidentLabels, incident.incident_type)}</b>으로 보입니다.<small>{incident.first_action_summary}</small></span></div><div className="result-stack"><div className="result-card action-card"><h3>먼저 전화하세요</h3><div className="call-grid">{bankPhone ? <a className="call-button icon-button" href={`tel:${bankPhone}`}><Phone size={19} aria-hidden="true" /> 송금한 금융회사</a> : <span className="call-button disabled">금융회사 번호 미입력</span>}<a className="call-button danger icon-button" href="tel:112"><Phone size={19} aria-hidden="true" /> 경찰 112</a><a className="call-button icon-button" href="tel:1332"><Phone size={19} aria-hidden="true" /> 금감원 1332</a></div></div><SpeakButton text={`${incident.first_action_summary} ${(plan.immediate ?? []).map((step: JsonRecord) => step.action).join(" ")}`} labelText="지금 할 일 읽어주기" />{steps.map(([title, items]) => items?.length > 0 && <div className="result-card" key={title}><h3>{title}</h3><div className="steps">{items.map((step) => <div className="step" key={`${title}-${step.order}`}><div className="step-number">{step.order}</div><div><strong>{step.action}</strong><span>{step.reason}</span></div></div>)}</div></div>)}{plan.required_documents?.length > 0 && <div className="result-card"><h3>준비할 서류</h3><ul className="check-list">{plan.required_documents.map((document: JsonRecord) => <li key={document.name}><strong>{document.name}</strong><span>{document.reason}{document.alternative ? ` 대체 가능: ${document.alternative}` : ""}</span></li>)}</ul></div>}<ReferenceList references={plan.references} /><GuardianShare title="사고 대응 결과" summary={incident.first_action_summary} details={[`상황: ${label(incidentLabels, incident.incident_type)}`, ...(plan.immediate ?? []).slice(0, 3).map((step: JsonRecord) => `먼저 할 일: ${step.action}`)]} /><div className="footer-note">{plan.disclaimer}</div></div></section>;
}

function ComplaintDraft({ setError, error }: { setError: (value: string) => void; error: string }) {
  const [statement, setStatement] = useState("");
  const [type, setType] = useState("general_complaint");
  const [result, setResult] = useState<JsonRecord | null>(null);
  const [editedDraft, setEditedDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [download, setDownload] = useState<{ filename: string; content: string } | null>(null);
  const resultRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => { if (result) resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }); }, [result]);
  const run = async () => { setError(""); setLoading(true); setDownload(null); try { const data = await postJson<JsonRecord>("/api/v1/complaints/draft", { user_statement: redactSensitiveText(statement), incident_type: type }); setResult(data); setEditedDraft(data.draft_body ?? ""); } catch (caught) { setError(caught instanceof Error ? caught.message : "민원 초안 작성에 실패했습니다."); } finally { setLoading(false); } };
  const exportDraft = async (format: string) => { if (!result) return; try { const data = await postJson<JsonRecord>("/api/v1/documents/export", { title: result.title, body: editedDraft, attachments: result.recommended_attachments, export_format: format }); setDownload({ filename: data.filename, content: data.content }); } catch (caught) { setError(caught instanceof Error ? caught.message : "파일 만들기에 실패했습니다."); } };
  return <><div className="panel-heading"><div><span className="panel-label">2단계 · 있었던 일 입력</span><h2>민원서 초안 만들기</h2><p>문장을 잘 쓰지 못해도 괜찮습니다. 기억나는 대로 적어주세요.</p></div></div><div className="form-grid"><div><label className="field-label" htmlFor="complaint-type">어떤 문제인가요?</label><select id="complaint-type" value={type} onChange={(event) => setType(event.target.value)}>{complaintTypes.map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></div><div><label className="field-label" htmlFor="complaint-statement">무슨 일이 있었나요?</label><textarea id="complaint-statement" value={statement} onChange={(event) => setStatement(event.target.value)} placeholder="언제, 어디서, 어떤 설명을 들었고 무슨 피해가 있었는지 적어주세요." /><p className="input-help">계좌번호, 비밀번호, 주민등록번호는 적지 마세요. 발견하면 분석 전에 가립니다.</p><PrivacyGuard text={statement} onMask={() => setStatement(redactSensitiveText(statement))} /></div></div><button className="primary-button full-button" type="button" aria-busy={loading} onClick={() => void run()} disabled={loading || !statement.trim()}>{loading ? "민원 문장을 정리하고 있습니다..." : "민원서 초안 만들기"}</button>{error && <ErrorNotice message={error} />}{result && <div ref={resultRef} className="result-area"><div className="result-heading"><span>3단계 · 확인하고 저장</span><h2>민원서 초안</h2></div><div className="result-stack"><div className="result-card"><span className="status-pill blue">{label(incidentLabels, result.complaint_type)}</span><h3>{result.title}</h3><p>{result.summary}</p><label className="field-label" htmlFor="complaint-draft">틀린 내용은 직접 고쳐주세요</label><textarea id="complaint-draft" className="draft-editor" value={editedDraft} onChange={(event) => setEditedDraft(event.target.value)} /><SpeakButton text={editedDraft} labelText="민원서 읽어주기" />{result.similar_cases?.length > 0 && <details className="reference"><summary>관련 공식 사례 보기</summary><div className="reference-body">{result.similar_cases.map((item: JsonRecord) => <div className="reference-item" key={item.case_no || item.title}><p><strong>{item.title}</strong></p><p>{item.relevance_reason}</p><p>{item.answer_summary}</p></div>)}</div></details>}</div>{result.claim_points?.length > 0 && <div className="result-card"><h3>꼭 전달할 내용</h3><ul className="check-list">{result.claim_points.map((point: string) => <li key={point}>{point}</li>)}</ul></div>}{result.submission_checklist?.length > 0 && <div className="result-card"><h3>접수 전에 확인하세요</h3><ul className="check-list">{result.submission_checklist.map((item: string) => <li key={item}>{item}</li>)}</ul></div>}<div className="result-card"><h3>함께 내면 좋은 자료</h3><ul className="check-list">{result.recommended_attachments?.map((item: string) => <li key={item}>{item}</li>)}</ul><div className="action-row"><button className="secondary-button" type="button" onClick={() => void exportDraft("txt")}>문서 파일 만들기</button><button className="secondary-button" type="button" onClick={() => window.print()}>인쇄하기</button></div>{download && <a className="download-link" download={download.filename} href={`data:text/plain;charset=utf-8,${encodeURIComponent(download.content)}`}>{download.filename} 받기</a>}</div><GuardianShare title="민원서 초안" summary={result.summary ?? result.title} details={[editedDraft, ...(result.submission_checklist ?? []).slice(0, 2)]} /><div className="footer-note">{result.disclaimer}</div></div></div>}</>;
}
