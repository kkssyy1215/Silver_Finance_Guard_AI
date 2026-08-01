# Contest Submission Guide

This document defines the source-code submission package for Silver Finance
Guard AI. The package is intentionally self-contained: it contains the web
application, the approved normalized official datasets required at runtime,
tests, and the documents needed to reproduce the demo.

## Included

- `backend/`: FastAPI API, rule engine, OCR and speech input services, tests,
  and normalized official datasets.
- `frontend/`: Next.js and TypeScript interface.
- `tools/`: repeatable risk-detection evaluation and source-package generator.
- `docs/`: demo script and the recorded evaluation report.
- `README.md`, `Dockerfile`, and `render.yaml`: local and container execution
  instructions.
- `LICENSE`, `PRIVACY.md`, `TERMS.md`, and `THIRD_PARTY_NOTICES.md`: use and
  data-attribution notices.

## Deliberately Excluded

- `data_inbox/`: original downloaded source files; these may be large and are
  not needed to run the application. Their normalized, permitted runtime data
  is in `backend/app/data/official/`.
- `tools/ingest_official_data.py`: a development-only importer that needs the
  excluded original files. It is retained in the repository but not included
  in the source-code submission archive.
- `deliverables/`: presentation and PDF files submitted separately from source.
- dependency folders and build output: `.venv/`, `node_modules/`, `.next/`,
  `out/`, and `.pytest_cache/`.

## Submission Checks

Run these from the repository root before creating the archive:

```bash
cd backend && python -m pytest -q
cd ../frontend && npm ci && npm run lint && npm run build
cd .. && sh tools/create_submission_archive.sh
```

The final archive is created at
`deliverables/Silver_Finance_Guard_AI_Submission_Source.zip`. Upload that ZIP
with the presentation/PDF only if the contest requests code as a separate file.

## Scope Note

This is an MVP decision-support service, not legal or financial advice. It
uses official data with an unrestricted-use indication recorded in
`THIRD_PARTY_NOTICES.md` and the runtime data registry.
