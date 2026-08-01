"use client";

import { ReactNode, useEffect, useRef, useState } from "react";
import { FileUp, Mic, Phone, Square, Volume2 } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { getJson, postFile, postJson } from "@/lib/api";

type TabKey = "check" | "terms" | "incident" | "complaint";
type InputMode = "text" | "file" | "voice";
type JsonRecord = Record<string, any>;

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
  return <div className="reference"><strong>공식 근거</strong>{references.map((reference, index) => <div key={`${reference.source_id ?? reference.title}-${index}`}><p><strong>{reference.title}</strong> · {reference.publisher}{reference.published_at ? ` · ${reference.published_at}` : ""}</p><p>{reference.summary}</p>{reference.application_reason && <p>이 결과에 적용한 이유: {reference.application_reason}</p>}{reference.url && <a href={reference.url} target="_blank" rel="noreferrer">원문 보기</a>}</div>)}</div>;
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
  const [highContrast, setHighContrast] = useState(true);
  const [magnifier, setMagnifier] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const savedScale = window.localStorage.getItem("silver-font-scale") as "normal" | "large" | "xlarge" | null;
    if (savedScale) setScale(savedScale);
    const savedContrast = window.localStorage.getItem("silver-high-contrast");
    if (savedContrast) setHighContrast(savedContrast === "true");
  }, []);
  useEffect(() => { window.localStorage.setItem("silver-font-scale", scale); }, [scale]);
  useEffect(() => { window.localStorage.setItem("silver-high-contrast", String(highContrast)); }, [highContrast]);

  const updateScale = (value: "normal" | "large" | "xlarge") => setScale(value);
  const changeTab = (next: TabKey) => { setTab(next); setError(""); window.scrollTo({ top: 0, behavior: "smooth" }); };

  return <div className={`app-shell ${scale === "large" ? "scale-large" : scale === "xlarge" ? "scale-xlarge" : ""} ${highContrast ? "high-contrast" : ""}`}>
    <div className="top-rule" />
    <main className="page-wrap">
      <header className="site-header">
        <div className="brand"><div className="eyebrow">금융소비자 보호 안내</div><h1>실버 금융가드</h1><p>어려운 금융 문장을 함께 읽고, 위험 신호를 찾고, 지금 할 일을 알려드립니다.</p></div>
        <div className="tool-box" aria-label="화면 도구"><label>화면 도구</label><button className={`font-button ${scale === "normal" ? "active" : ""}`} type="button" onClick={() => updateScale("normal")}>작게</button><button className={`font-button ${scale === "large" ? "active" : ""}`} type="button" onClick={() => updateScale("large")}>크게</button><button className={`font-button ${scale === "xlarge" ? "active" : ""}`} type="button" onClick={() => updateScale("xlarge")}>아주 크게</button><button className={`contrast-button ${highContrast ? "active" : ""}`} type="button" onClick={() => setHighContrast((value) => !value)}>고대비</button><button className={`contrast-button ${magnifier ? "active" : ""}`} type="button" onClick={() => setMagnifier((value) => !value)}>돋보기</button></div>
      </header>

      <section className="welcome" aria-label="서비스 소개"><div className="welcome-main"><h2>가입 전에 한 번 더.<br />사고가 나면 바로 대응.</h2><p>상담 내용, 약관, 문자, 사진을 넣으면 공식 자료를 근거로 위험한 표현과 필요한 질문을 정리합니다.</p></div><div className="welcome-side"><h3>사용 순서</h3><ol className="quick-list"><li>어려운 내용을 입력합니다.</li><li>확인이 필요한 문장을 읽습니다.</li><li>질문·전화·서류를 준비합니다.</li></ol></div></section>

      <nav className="tabs" aria-label="주요 기능">{([["check", "가입 전 안심점검"], ["terms", "금융용어검색"], ["incident", "사고 대응"], ["complaint", "민원 초안"]] as [TabKey, string][]).map(([key, text]) => <button key={key} type="button" className={`tab-button ${tab === key ? "active" : ""}`} onClick={() => changeTab(key)}>{text}</button>)}</nav>
      <section className="content-panel">{tab === "check" && <ContractCheck magnifier={magnifier} setError={setError} error={error} />} {tab === "terms" && <TermSearch magnifier={magnifier} setError={setError} error={error} />} {tab === "incident" && <IncidentResponse magnifier={magnifier} setError={setError} error={error} />} {tab === "complaint" && <ComplaintDraft setError={setError} error={error} />}</section>
      <p className="footer-note">이 서비스는 공식 자료 기반의 확인 보조 도구입니다. 최종 가입·신고·민원 제출 전에는 해당 금융회사와 공식 기관의 최신 안내를 함께 확인하세요.</p>
    </main>
  </div>;
}

function ContractCheck({ magnifier, setError, error }: { magnifier: boolean; setError: (value: string) => void; error: string }) {
  const [mode, setMode] = useState<InputMode>("text");
  const [text, setText] = useState(sampleContract);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<JsonRecord | null>(null);
  const [loading, setLoading] = useState("");
  const [fileLoading, setFileLoading] = useState(false);
  const [fileMessage, setFileMessage] = useState("");
  const [recording, setRecording] = useState(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const runAnalysis = async (kind: "contract" | "explanation") => {
    setError(""); setResult(null); setLoading(kind);
    try {
      let data: JsonRecord;
      if (mode === "file") {
        if (!file) throw new Error("먼저 PDF, 사진 또는 텍스트 파일을 올려주세요.");
        data = await postFile<JsonRecord>("/api/v1/analyze/document-file", file);
      } else {
        if (!text.trim()) throw new Error("분석할 문장이나 상담 내용을 입력해주세요.");
        data = await postJson<JsonRecord>(kind === "contract" ? "/api/v1/analyze/document" : "/api/v1/analyze/explanation-risk", { content: redactSensitiveText(text), content_type: "text", user_age_group: "senior" });
      }
      setResult({ ...data, kind });
    } catch (caught) { setError(caught instanceof Error ? caught.message : "분석에 실패했습니다."); }
    finally { setLoading(""); }
  };

  const handleFile = async (selectedFile: File) => {
    setFile(selectedFile); setFileMessage(""); setError(""); setFileLoading(true);
    try {
      const extracted = await postFile<JsonRecord>("/api/v1/analyze/extract-text", selectedFile);
      if (!extracted.text) throw new Error(extracted.quality_message ?? "파일에서 글자를 읽지 못했습니다.");
      setText(extracted.text); setMode("text"); setFileMessage(extracted.quality_message ?? "파일을 읽었습니다. 내용을 확인하고 고쳐주세요.");
    } catch (caught) { setError(caught instanceof Error ? caught.message : "파일을 읽지 못했습니다."); }
    finally { setFileLoading(false); }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (event) => { if (event.data.size) chunksRef.current.push(event.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const audio = new File([new Blob(chunksRef.current, { type: "audio/webm" })], "voice-input.webm", { type: "audio/webm" });
        try { const data = await postFile<JsonRecord>("/api/v1/analyze/transcribe-audio", audio); if (data.text) setText(data.text); else setError(data.message ?? "음성을 글자로 바꾸지 못했습니다."); } catch (caught) { setError(caught instanceof Error ? caught.message : "음성 변환에 실패했습니다."); }
      };
      recorderRef.current = recorder; recorder.start(); setRecording(true); setError("");
    } catch { setError("마이크를 사용할 수 없습니다. 브라우저 권한을 확인하거나 직접 적기를 이용해주세요."); }
  };
  const stopRecording = () => { recorderRef.current?.stop(); recorderRef.current = null; setRecording(false); };

  return <><div className="panel-heading"><div><span className="panel-label">가입 전 예방</span><h2>가입 전 안심점검</h2><p>내용을 넣으면 확인할 문장과 질문을 정리합니다.</p></div></div><div className="notice">법률 판단이 아닙니다. 확인이 필요한 후보와 공식 근거를 보여드립니다.</div><h3 className="section-title">내용 넣기</h3><div className="mode-row"><ModeChoice name="contract-mode" value="text" checked={mode === "text"} onChange={() => setMode("text")}>직접 적기</ModeChoice><ModeChoice name="contract-mode" value="file" checked={mode === "file"} onChange={() => setMode("file")}>사진·파일 올리기</ModeChoice><ModeChoice name="contract-mode" value="voice" checked={mode === "voice"} onChange={() => setMode("voice")}>음성으로 말하기</ModeChoice></div>{mode === "file" ? <FileMode onFile={(selectedFile) => void handleFile(selectedFile)} busy={fileLoading} /> : mode === "voice" ? <div className="notice neutral"><p>상담 내용이나 문자 내용을 천천히 읽어주세요.</p><div className="action-row"><button type="button" className={recording ? "secondary-button icon-button" : "primary-button icon-button"} onClick={recording ? stopRecording : startRecording}>{recording ? <><Square size={18} aria-hidden="true" /> 녹음 끝내기</> : <><Mic size={18} aria-hidden="true" /> 녹음 시작</>}</button>{recording && <span className="recording">녹음 중입니다.</span>}</div></div> : <div><label className="field-label" htmlFor="contract-text">문자·약관·상담 내용</label><textarea id="contract-text" value={text} onChange={(event) => setText(event.target.value)} placeholder="예: 원금은 보장되며 오늘까지만 가입할 수 있습니다." />{fileMessage && <div className="notice neutral">{fileMessage}</div>}<PrivacyGuard text={text} onMask={() => setText(redactSensitiveText(text))} />{magnifier && <div className="magnifier"><strong>입력한 내용</strong>{text || "입력한 내용이 여기에 표시됩니다."}</div>}</div>}<div className="action-row"><button className="primary-button" type="button" disabled={Boolean(loading) || fileLoading} onClick={() => void runAnalysis("contract")}>{loading === "contract" ? "확인 중..." : "약관 위험 점검"}</button><button className="secondary-button" type="button" disabled={Boolean(loading) || fileLoading} onClick={() => void runAnalysis("explanation")}>{loading === "explanation" ? "확인 중..." : "설명의무 위험 점검"}</button></div>{error && <ErrorNotice message={error} />}{result && <ContractResult result={result} />}</>;
}

function ContractResult({ result }: { result: JsonRecord }) {
  const isExplanation = result.kind === "explanation";
  const items = isExplanation ? result.suspicious_points ?? [] : result.risk_items ?? [];
  const overall = result.overall_risk ?? result.risk_level ?? "unknown";
  return <div className="result-stack"><div className="score"><strong>{label(riskLabels, overall)}</strong><span>{result.document_summary?.one_line ?? result.summary?.one_line ?? "확인 결과를 읽어보세요."}<br />가입이나 분쟁의 법적 판단이 아닌 확인 보조 정보입니다.</span></div>{items.length === 0 ? <div className="empty">큰 위험 신호는 찾지 못했습니다. 그래도 공식 설명서와 질문 카드를 한 번 더 확인하세요.</div> : items.map((item: JsonRecord, index: number) => { const itemLabel = isExplanation ? label(explanationLabels, item.label) : label(riskItemLabels, item.label); const text = item.original_text ?? item.detected_text ?? ""; const easy = item.simplified_text ?? item.easy_explanation ?? ""; const reason = item.why_it_matters ?? item.reason ?? ""; return <article className="result-card" key={`${item.label}-${index}`}><span className="status-pill">{itemLabel} · {label(riskLabels, item.severity)}</span><div className="status-pill blue">{item.review_status ?? "확인 필요"}</div><h3>감지된 단어가 표시된 문장</h3><div className="highlighted-text"><HighlightedText text={text} keywords={item.detected_keywords} /></div><h3>쉽게 해석하면</h3><p>{easy}</p><h3>왜 확인해야 하나요?</h3><p>{reason}</p><div className="question"><strong>지금 물어볼 질문</strong><br />{item.must_ask_question}</div><SpeakButton text={`${easy}. 지금 물어볼 질문은 ${item.must_ask_question}`} labelText="이 결과 읽어주기" /><ReferenceList references={item.official_references} /></article>; })}{result.must_ask_questions?.length > 0 && <div className="result-card"><h3>직원에게 보여줄 질문 카드</h3><ol>{result.must_ask_questions.map((question: string) => <li key={question}>{question}</li>)}</ol></div>}<ReferenceList references={result.references} /><GuardianShare title="가입 전 안심점검 결과" summary={result.document_summary?.one_line ?? result.summary?.one_line ?? "확인 결과를 확인해주세요."} details={items.slice(0, 4).map((item: JsonRecord) => `${label(riskItemLabels, item.label)}: ${item.simplified_text ?? item.easy_explanation ?? "확인 필요"}`)} /></div>;
}

function TermSearch({ magnifier, setError, error }: { magnifier: boolean; setError: (value: string) => void; error: string }) {
  const [query, setQuery] = useState("예금자보호");
  const [terms, setTerms] = useState<JsonRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const search = async () => { if (!query.trim()) return; setError(""); setLoading(true); try { const data = await getJson<{ terms: JsonRecord[] }>("/api/v1/official-data/terms/search", { query, limit: 8 }); setTerms(data.terms); } catch (caught) { setError(caught instanceof Error ? caught.message : "금융용어 검색에 실패했습니다."); } finally { setLoading(false); } };
  return <><div className="panel-heading"><div><span className="panel-label">공식 용어 사전</span><h2>금융용어검색</h2><p>금융 단어의 공식 정의와 누구나 이해할 수 있는 쉬운 해석을 나눠서 보여드립니다.</p></div></div><div className="notice">예금자보호, 지급정지, 청약철회, 위약금처럼 궁금한 단어 하나만 입력하세요.</div><div style={{ marginTop: 18 }}><label className="field-label" htmlFor="term-query">궁금한 금융 단어</label><input id="term-query" type="text" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void search(); }} placeholder="예: 예금자보호" />{magnifier && <div className="magnifier"><strong>돋보기: 검색할 단어</strong>{query}</div>}</div><div className="action-row"><button className="primary-button" type="button" onClick={() => void search()} disabled={loading}>{loading ? "찾는 중..." : "금융용어 검색"}</button></div>{error && <ErrorNotice message={error} />}{terms.length > 0 && <><div className="notice neutral result-summary">{terms.some((term) => term.match_type === "exact") ? "검색어와 정확히 일치하는 용어입니다." : `‘${query}’라는 단독 용어가 없어 관련 용어를 보여드립니다.`}</div><div className="result-stack">{terms.map((term, index) => <article className="result-card" key={`${term.term}-${index}`}><h3>{term.term}</h3><span className="status-pill blue">{term.match_type === "exact" ? "정확히 일치" : "관련 용어"}</span><p>{term.easy_explanation}</p><div className="notice neutral"><strong>공식 정의</strong><br />{term.official_definition || "공식 정의가 등록되지 않았습니다."}</div><div className="question"><strong>확인할 일</strong><br />{term.action_tip}</div><div className="reference"><strong>출처</strong><p>{term.source_title}</p>{term.source_url && <a href={term.source_url} target="_blank" rel="noreferrer">공식 출처 열기</a>}</div></article>)}</div></>}{!loading && terms.length === 0 && <div className="empty">검색 결과가 여기에 표시됩니다.</div>}</>;
}

function IncidentResponse({ magnifier, setError, error }: { magnifier: boolean; setError: (value: string) => void; error: string }) {
  const [mode, setMode] = useState<"text" | "voice">("text");
  const [content, setContent] = useState(incidentSamples[0]);
  const [bankPhone, setBankPhone] = useState("");
  const [companyQuery, setCompanyQuery] = useState("");
  const [companies, setCompanies] = useState<JsonRecord[]>([]);
  const [companyLoading, setCompanyLoading] = useState(false);
  const [incident, setIncident] = useState<JsonRecord | null>(null);
  const [plan, setPlan] = useState<JsonRecord | null>(null);
  const [loading, setLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const digits = bankPhone.replace(/[^0-9+]/g, "");
  const run = async () => { setError(""); setIncident(null); setPlan(null); setLoading(true); try { const safeContent = redactSensitiveText(content); const classified = await postJson<JsonRecord>("/api/v1/incidents/classify", { content: safeContent }); const actionPlan = await postJson<JsonRecord>("/api/v1/incidents/action-plan", { incident_type: classified.incident_type, content: safeContent }); setIncident(classified); setPlan(actionPlan); } catch (caught) { setError(caught instanceof Error ? caught.message : "사고 대응 분석에 실패했습니다."); } finally { setLoading(false); } };
  const searchCompanies = async () => { if (!companyQuery.trim()) return; setCompanyLoading(true); setError(""); try { const data = await getJson<{ records: JsonRecord[] }>("/api/v1/official-data/records/search", { query: companyQuery, dataset_id: "KDIC_INSURED_FINANCIAL_COMPANIES_20250930", limit: 6 }); setCompanies(data.records); if (!data.records.length) setError("공식 목록에서 금융회사를 찾지 못했습니다. 기관명을 다시 확인해주세요."); } catch (caught) { setError(caught instanceof Error ? caught.message : "금융회사 검색에 실패했습니다."); } finally { setCompanyLoading(false); } };
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (event) => { if (event.data.size) chunksRef.current.push(event.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const audio = new File([new Blob(chunksRef.current, { type: "audio/webm" })], "incident-voice.webm", { type: "audio/webm" });
        try { const data = await postFile<JsonRecord>("/api/v1/analyze/transcribe-audio", audio); if (data.text) setContent(data.text); else setError(data.message ?? "음성을 글자로 바꾸지 못했습니다."); } catch (caught) { setError(caught instanceof Error ? caught.message : "음성 변환에 실패했습니다."); }
      };
      recorderRef.current = recorder; recorder.start(); setRecording(true); setError("");
    } catch { setError("마이크를 사용할 수 없습니다. 브라우저 권한을 확인하거나 직접 적기를 이용해주세요."); }
  };
  const stopRecording = () => { recorderRef.current?.stop(); recorderRef.current = null; setRecording(false); };
  return <><div className="panel-heading"><div><span className="panel-label">골든타임 대응</span><h2>사고 대응</h2><p>착오송금이나 보이스피싱이 의심되면 지금 할 일을 봅니다.</p></div></div><div className="notice warning"><strong>급하면 분석보다 먼저 전화하세요.</strong> 보이스피싱은 112, 송금 사고는 은행, 금융 상담은 1332입니다.</div><h3 className="section-title">상황 입력</h3><div className="mode-row"><ModeChoice name="incident-mode" value="text" checked={mode === "text"} onChange={() => setMode("text")}>직접 적기</ModeChoice><ModeChoice name="incident-mode" value="voice" checked={mode === "voice"} onChange={() => setMode("voice")}>음성으로 말하기</ModeChoice></div>{mode === "text" && <select aria-label="상황 예시" value={incidentSamples.includes(content) ? content : "직접 입력"} onChange={(event) => { if (event.target.value !== "직접 입력") setContent(event.target.value); }}><option>직접 입력</option>{incidentSamples.map((sample) => <option key={sample}>{sample}</option>)}</select>}{mode === "voice" && <div className="notice neutral"><p>사고 상황을 천천히 말해주세요.</p><div className="action-row"><button type="button" className={recording ? "secondary-button icon-button" : "primary-button icon-button"} onClick={recording ? stopRecording : startRecording}>{recording ? <><Square size={18} aria-hidden="true" /> 녹음 끝내기</> : <><Mic size={18} aria-hidden="true" /> 녹음 시작</>}</button>{recording && <span className="recording">녹음 중입니다.</span>}</div></div>}<textarea aria-label="사고 상황" value={content} onChange={(event) => setContent(event.target.value)} placeholder="예: 모르는 사람에게 돈을 잘못 보냈어요." /><PrivacyGuard text={content} onMask={() => setContent(redactSensitiveText(content))} />{magnifier && <div className="magnifier"><strong>사고 상황</strong>{content}</div>}<div className="company-finder"><label className="field-label" htmlFor="company-query">송금한 금융회사 찾기</label><div className="company-search-row"><input id="company-query" type="text" value={companyQuery} onChange={(event) => setCompanyQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") void searchCompanies(); }} placeholder="예: 국민은행" /><button className="secondary-button" type="button" onClick={() => void searchCompanies()} disabled={companyLoading}>{companyLoading ? "찾는 중" : "공식 연락처 찾기"}</button></div><p className="input-help">예금보험공사 공식 금융회사 목록의 연락처입니다. 고객센터는 카드 뒷면이나 공식 앱에서도 확인하세요.</p>{companies.length > 0 && <div className="company-results">{companies.map((company, index) => <button className="company-result" type="button" key={`${company.title}-${index}`} onClick={() => { setBankPhone(company.metadata?.phone ?? ""); setCompanyQuery(company.title); setCompanies([]); }}><strong>{company.title}</strong><span>{company.metadata?.phone || "전화번호 없음"}</span></button>)}</div>}</div><label className="field-label" htmlFor="bank-phone">송금한 금융회사 연락처</label><input id="bank-phone" type="tel" value={bankPhone} onChange={(event) => setBankPhone(event.target.value)} placeholder="공식 번호를 선택하거나 입력하세요" /><div className="action-row"><button className="primary-button" type="button" onClick={() => void run()} disabled={loading}>{loading ? "상황을 확인하는 중..." : "사고 대응 시작"}</button></div>{error && <ErrorNotice message={error} />}{incident && plan && <IncidentResult incident={incident} plan={plan} bankPhone={digits} />}</>;
}

function IncidentResult({ incident, plan, bankPhone }: { incident: JsonRecord; plan: JsonRecord; bankPhone: string }) {
  const steps = [["지금 바로 할 일", plan.immediate], ["10분 안에 할 일", plan.within_10min], ["오늘 할 일", plan.today], ["이후 준비할 일", plan.follow_up]] as [string, JsonRecord[]][];
  return <div className="result-stack"><div className="score"><strong>{label(riskLabels, incident.urgency_level)}</strong><span>상황 판단: {label(incidentLabels, incident.incident_type)}<br />{incident.first_action_summary}</span></div>{steps.map(([title, items]) => items?.length > 0 && <div className="result-card" key={title}><h3>{title}</h3><div className="steps">{items.map((step) => <div className="step" key={`${title}-${step.order}`}><div className="step-number">{step.order}</div><div><strong>{step.action}</strong><span>{step.reason}</span></div></div>)}</div></div>)}<SpeakButton text={`${incident.first_action_summary} ${(plan.immediate ?? []).map((step: JsonRecord) => step.action).join(" ")}`} labelText="지금 할 일 읽어주기" /><div className="result-card"><h3>바로 전화하기</h3><div className="call-grid">{bankPhone ? <a className="call-button icon-button" href={`tel:${bankPhone}`}><Phone size={19} aria-hidden="true" /> 송금한 은행</a> : <span className="call-button disabled">은행 번호 입력 필요</span>}<a className="call-button icon-button" href="tel:112"><Phone size={19} aria-hidden="true" /> 112 신고</a><a className="call-button icon-button" href="tel:1332"><Phone size={19} aria-hidden="true" /> 1332 상담</a></div></div>{plan.required_documents?.length > 0 && <div className="result-card"><h3>준비할 서류</h3><ul>{plan.required_documents.map((document: JsonRecord) => <li key={document.name}><strong>{document.name}</strong> · {document.reason}{document.alternative ? ` (대체: ${document.alternative})` : ""}</li>)}</ul></div>}<ReferenceList references={plan.references} /><GuardianShare title="사고 대응 결과" summary={incident.first_action_summary} details={[`상황: ${label(incidentLabels, incident.incident_type)}`, ...(plan.immediate ?? []).slice(0, 3).map((step: JsonRecord) => `먼저 할 일: ${step.action}`)]} /><div className="footer-note">{plan.disclaimer}</div></div>;
}

function ComplaintDraft({ setError, error }: { setError: (value: string) => void; error: string }) {
  const [statement, setStatement] = useState("");
  const [type, setType] = useState("general_complaint");
  const [result, setResult] = useState<JsonRecord | null>(null);
  const [loading, setLoading] = useState(false);
  const [download, setDownload] = useState<{ filename: string; content: string } | null>(null);
  const run = async () => { setError(""); setLoading(true); try { setResult(await postJson<JsonRecord>("/api/v1/complaints/draft", { user_statement: redactSensitiveText(statement), incident_type: type })); } catch (caught) { setError(caught instanceof Error ? caught.message : "민원 초안 작성에 실패했습니다."); } finally { setLoading(false); } };
  const exportDraft = async (format: string) => { if (!result) return; try { const data = await postJson<JsonRecord>("/api/v1/documents/export", { title: result.title, body: result.draft_body, attachments: result.recommended_attachments, export_format: format }); setDownload({ filename: data.filename, content: data.content }); } catch (caught) { setError(caught instanceof Error ? caught.message : "파일 만들기에 실패했습니다."); } };
  return <><div className="panel-heading"><div><span className="panel-label">제출 준비</span><h2>민원 초안</h2><p>있었던 일을 적으면 접수용 문장으로 정리합니다.</p></div></div><div className="notice neutral">계좌번호, 비밀번호, 주민등록번호는 적지 마세요. 입력하면 자동으로 가리고 보냅니다.</div><div style={{ marginTop: 18 }}><label className="field-label" htmlFor="complaint-type">문제 유형</label><select id="complaint-type" value={type} onChange={(event) => setType(event.target.value)}>{complaintTypes.map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select><label className="field-label" htmlFor="complaint-statement" style={{ marginTop: 15 }}>있었던 일</label><textarea id="complaint-statement" value={statement} onChange={(event) => setStatement(event.target.value)} placeholder="예: 상담원이 원금이 보장된다고 설명했지만 손실 가능성을 나중에 알았습니다." /><PrivacyGuard text={statement} onMask={() => setStatement(redactSensitiveText(statement))} /></div><div className="action-row"><button className="primary-button" type="button" onClick={() => void run()} disabled={loading || !statement.trim()}>{loading ? "초안을 정리하는 중..." : "민원 초안 만들기"}</button></div>{error && <ErrorNotice message={error} />}{result && <div className="result-stack"><div className="result-card"><span className="status-pill blue">{label(incidentLabels, result.complaint_type)}</span><h3>{result.title}</h3><p>{result.summary}</p><div className="highlighted-text" style={{ whiteSpace: "pre-wrap" }}>{result.draft_body}</div><SpeakButton text={result.draft_body} labelText="민원 초안 읽어주기" /></div>{result.claim_points?.length > 0 && <div className="result-card"><h3>핵심 주장</h3><ul>{result.claim_points.map((point: string) => <li key={point}>{point}</li>)}</ul></div>}{result.submission_checklist?.length > 0 && <div className="result-card"><h3>접수 전 체크리스트</h3><ul>{result.submission_checklist.map((item: string) => <li key={item}>{item}</li>)}</ul></div>}<div className="result-card"><h3>첨부 권장 자료</h3><ul>{result.recommended_attachments?.map((item: string) => <li key={item}>{item}</li>)}</ul><div className="action-row"><button className="secondary-button" type="button" onClick={() => void exportDraft("txt")}>TXT 다운로드 준비</button><button className="secondary-button" type="button" onClick={() => void exportDraft("md")}>Markdown 다운로드 준비</button></div>{download && <a className="download-link" download={download.filename} href={`data:text/plain;charset=utf-8,${encodeURIComponent(download.content)}`}>{download.filename} 받기</a>}</div><GuardianShare title="민원 초안" summary={result.summary ?? result.title} details={[...(result.claim_points ?? []).slice(0, 3), ...(result.submission_checklist ?? []).slice(0, 2)]} /><div className="footer-note">{result.disclaimer}</div></div>}</>;
}
