# Development and deployment

## Local development

1. Install Python requirements from `backend/requirements.txt`.
2. Start the API from the repository root with `uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000`.
3. In `frontend`, install npm dependencies and run `npm run dev -- --host 0.0.0.0`.
4. Open the Vite URL and load the demo repository. API docs are available at `/docs`.

Set `DATABASE_PATH`, `STORAGE_DIR`, `CORS_ORIGINS`, and optional provider/GitHub variables in the backend environment. Keep secrets in an untracked `.env`; use `.env.example` as the key list.

## Docker Compose

With Docker Compose 2.24 or newer, run `docker compose up --build`. The web service is at `http://localhost:5173` and proxies API requests to the healthy API container. SQLite and indexed repository files persist in separate named volumes mounted under `/app/data` and `/app/backend/storage`; neither volume covers application source.

## Verification commands

From repository root:

```powershell
cd backend
python -m pytest tests -q
cd ..
python -m compileall -q backend
python -c "from backend.app.evaluation import run_benchmark; print(run_benchmark())"
cd frontend
npm run build
npm test -- --run
```

If Docker is installed, additionally run `docker compose config` and `docker compose up --build`, then visit `/api/health`, `/api/evaluation/run`, and the browser workflow. Report environment limitations explicitly.
