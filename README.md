# Silver Finance Guard AI

`실버 금융가드 AI` is an MVP prototype for senior-friendly financial consumer protection.

It supports two core flows:

- Pre-signup check: detect risky clauses or misleading sales language and explain them in plain Korean.
- Incident response: classify financial incidents such as mistaken transfers or voice phishing, then generate action steps, document checklists, and complaint drafts.

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

