# Silver Finance Guard AI

`실버 금융가드 AI` is an MVP prototype for senior-friendly financial consumer protection.

## One-Line Description

고령층 사용자가 이해하기 어려운 금융 약관의 위험 요소를 사전에 탐지하고, 금융사고 발생 시 골든타임 내 필요한 조치와 서류 작성을 즉시 지원하는 금융소비자 보호 AI 에이전트입니다.

## Submission Contents

- Source package guide: `SUBMISSION.md`
- Technical presentation: `deliverables/실버_금융가드_AI_기술설명서.pptx`
- Technical description PDF: `deliverables/실버_금융가드_AI_기술설명서.pdf`
- Judge demo flow: `docs/demo_scenarios.md`

## Core Flows

- Pre-signup check: detect risky clauses or misleading sales language and explain them in plain Korean.
- Consumer protection check: compare detected risks with project-authored checks grounded in official consumer-protection guidance.
- Incident response: classify financial incidents such as mistaken transfers or voice phishing, then generate action steps, document checklists, and complaint drafts.
- Complaint drafting: ground complaint drafts in official model consultation cases.
- Senior-friendly UX: provide large text, high contrast, magnifier view, emergency cards, and step-by-step action cards.
- Evidence-first results: highlight detected words and show `확인 필요`/`주의 후보`, reason, question, source date, original link, and why each source was applied.
- Input accessibility: support image OCR, local Korean voice transcription, and browser read-aloud controls.
- Document export: download complaint drafts and analysis reports as TXT, Markdown, or HTML.
- Official data grounding: search imported public-data rows for financial terms, senior finance support, telemarketing seller checks, voice-phishing trend evidence, and mistaken-transfer guidance.

## Demo And Portfolio Docs

- `docs/demo_scenarios.md`: 3-minute demo script for pre-signup check, voice phishing response, and complaint drafting.
- `docs/portfolio_brief.md`: portfolio-ready project overview, problem definition, architecture, data usage, and evaluation mapping.

## Commercial And Public-Sector Data Policy

The runtime uses only public datasets whose official pages state
`이용허락범위 제한 없음`. Material with non-commercial, no-derivatives, or
unverified terms is excluded from the application and tracked as
`excluded` or `reference_only` in the registry.

- License and attribution inventory: `THIRD_PARTY_NOTICES.md`
- Privacy principles: `PRIVACY.md`
- Service notice: `TERMS.md`
- Machine-readable dataset audit: `backend/app/data/official/official_dataset_registry.json`

## Official Data Currently Used

- `backend/app/data/official/kdic_mistaken_transfer_faq.json`
- `backend/app/data/official/fsc_financial_terms.json`
- `backend/app/data/official/kdic_deposit_insurance_terms.json`
- `backend/app/data/official/kinfa_main_faq.json`
- `backend/app/data/official/kinfa_microfinance_branches.json`
- `backend/app/data/official/kinfa_microfinance_age_loan_stats.json`
- `backend/app/data/official/ftc_telemarketing_sellers_seoul_gyeonggi.json`
- `backend/app/data/official/ftc_consumer_complaint_examples.json`
- `backend/app/data/official/post_office_financial_fraud_accounts.json`
- `backend/app/data/official/police_voice_phishing_stats.json`
- `backend/app/data/official/police_voice_phishing_regional_damage.json`
- `backend/app/data/official/kdic_insured_financial_companies.json`

The raw files are placed in `data_inbox/` and excluded from git. The ingestion
script ignores restricted or unverified sources and generates normalized JSON
only for approved datasets:

```bash
python tools/ingest_official_data.py
```

API-only datasets are intentionally excluded from the MVP data registry unless a local file or non-API source is available.

## Detection Evaluation

- `backend/app/data/evaluation/risk_detection_cases.json`: 40 labeled contract and consultation sentences, including normal sentences for false-positive checks.
- `tools/evaluate_risk_detection.py`: runs the evaluation and writes `docs/risk_detection_evaluation.md` and a JSON report.
- The current evaluation result is 100% expected-case match, with 0% false positives among the normal sentences.

## Official Data Registry

The project also tracks additional official datasets in:

- `backend/app/data/official/official_dataset_registry.json`

Dataset statuses:

- `imported`: available locally and used by the app
- `planned`: permission/metadata reviewed, ready for future ingestion
- `reference_only`: official page used as procedural reference, not automatically collected yet

## Project Structure

```text
backend/
  app/
    api/v1/endpoints/   FastAPI route handlers
    core/               App config
    data/rules/         Rule dictionaries for MVP detection
    schemas/            Pydantic request/response models
    services/           Business logic
frontend/
  app/                  Next.js App Router pages
  components/           TypeScript feature UI
  lib/api.ts            Typed FastAPI client
  package.json          Next.js frontend scripts
```

## Run Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Run Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. By default, the frontend calls `http://127.0.0.1:8000` during local development. The deployed Docker service serves the frontend and API from one address.

The frontend is a Next.js + TypeScript static application served by FastAPI in
the production container.

## Verify Before Submission

```bash
cd backend
python -m pytest -q

cd ../frontend
npm ci
npm run lint
npm run build

cd ..
sh tools/create_submission_archive.sh
```

The archive contains only source code, approved runtime data, tests, and
reproduction documents. See `SUBMISSION.md` for the exact include/exclude
policy.

## Operational Safeguards

- Uploaded documents are limited to 10MB and PDFs to 60 pages.
- Text inputs have endpoint-specific size limits.
- OCR and speech-recognition failures do not expose internal exception details.
- Security headers restrict framing, content types, referrers, browser permissions, and external content loading.
- User documents and audio are processed for the current request and are not stored in a database.
- High contrast, large text, keyboard focus, reduced motion, and forced-colors modes are supported.

### Optional Input Dependencies

The backend requirements include Korean OCR (`Pillow`, `pytesseract`) and local voice transcription (`faster-whisper`). On macOS, install the OCR engine and Korean language data once:

```bash
brew install tesseract tesseract-lang
```

The first voice transcription downloads the small `tiny` Whisper model. Set `WHISPER_MODEL_SIZE` to choose another local model size.
