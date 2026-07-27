# Silver Finance Guard AI

`실버 금융가드 AI` is an MVP prototype for senior-friendly financial consumer protection.

It supports two core flows:

- Pre-signup check: detect risky clauses or misleading sales language and explain them in plain Korean.
- Incident response: classify financial incidents such as mistaken transfers or voice phishing, then generate action steps, document checklists, and complaint drafts.
- Document export: download complaint drafts as TXT, Markdown, or HTML.
- Official data grounding: search imported public-data FAQ rows for mistaken-transfer guidance.

## Official Data Currently Used

- `backend/app/data/official/kdic_mistaken_transfer_faq.json`
- Source: 예금보험공사_착오송금 반환지원제도 FAQ_20240729
- Portal: 공공데이터포털
- License on portal: 이용허락범위 제한 없음
- Rows imported: 12

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
  app.py                Streamlit MVP interface
```

## Run Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Run Frontend

```bash
cd frontend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

By default, the frontend calls `http://127.0.0.1:8000`.
