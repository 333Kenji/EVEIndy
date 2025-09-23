Hello World
# EVEINDY
## Quickstart (no Docker)

1. Create venv and install deps
   - `python3 -m venv IndyCalculator`
   - `IndyCalculator/bin/python -m pip install --upgrade pip`
   - `IndyCalculator/bin/python -m pip install -r requirements.txt`

2. Start Postgres + Redis (local services or your own containers)
   - Set `DATABASE_URL` and `REDIS_URL` (see `.env.example`).

3. Migrate database
   - `IndyCalculator/bin/python -m alembic upgrade head`

4. Fetch & load latest SDE
   - `IndyCalculator/bin/python utils/fetch_and_load_sde.py`

5. Seed initial price snapshots (optional)
   - `IndyCalculator/bin/python utils/backfill_prices.py --provider adam4eve --region 10000002 --types 16272,16273,44,3689,9832`

6. Run API
   - `IndyCalculator/bin/python -m uvicorn app.main:app --reload`
   - Open `http://localhost:8000/docs`

7. Frontend dev server
   - `cd frontend && npm install && npm run dev`
   - Open the printed Vite URL (e.g., `http://localhost:5173`)

See also: `docs/sde_auto.md`, `docs/sde.md`, `docs/rate_limits.md`.

## Docker Compose (hot reload dev stack)

1. Copy `.env.example` to `.env` (or export the same variables in your shell).
2. From the repo root run `docker compose up`.
   - Containers: Postgres, Redis, FastAPI (with `uvicorn --reload`), Celery worker/beat, and Vite dev server (`npm run dev`).
   - Code changes on the host automatically reload the API and frontend because the repo is bind-mounted and reload flags are enabled.
3. Open the services:
   - API docs: <http://localhost:8000/docs>
   - Frontend: <http://localhost:5173>
4. When you are done, `docker compose down` stops the stack.

> Tip: If you prefer local uvicorn/npm for faster iteration, you can still run only the infrastructure pieces with `docker compose up db redis` and keep using your existing workflow.
