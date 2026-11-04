# TikTok Live Game

A full-stack, real-time interactive game for TikTok LIVE streams.

| Layer     | Tech                                   |
| --------- | -------------------------------------- |
| Frontend  | React 19 + TypeScript + Vite           |
| Backend   | FastAPI (Python 3.11+) + Uvicorn       |
| Realtime  | WebSocket (FastAPI ⇄ browser)          |
| Database  | SQLite via SQLAlchemy 2 (async, aiosqlite) |

> **Status:** project skeleton only — game/business logic is not implemented yet.

## Project structure

```
TikTok-Live-Game/
├── backend/
│   ├── app/
│   │   ├── api/            # REST routers (mounted under /api)
│   │   │   └── routes/
│   │   ├── core/           # Settings / configuration
│   │   ├── db/             # SQLAlchemy engine, session, Base
│   │   ├── models/         # ORM models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic (TODO)
│   │   ├── websocket/      # WebSocket endpoint + connection manager
│   │   └── main.py         # FastAPI app entry point
│   ├── tests/
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/          # useWebSocket
│   │   ├── services/       # REST API client
│   │   ├── config.ts       # API / WS URLs
│   │   └── App.tsx
│   ├── vite.config.ts      # Dev proxy → backend
│   └── .env.example
└── .github/workflows/ci.yml
```

## Prerequisites

- Python **3.11+**
- Node.js **20+** (npm)
- Git

## Getting started

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # Windows: copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

- API docs: <http://localhost:8000/docs>
- Health check: `GET /api/health`
- WebSocket: `ws://localhost:8000/ws`

The SQLite database file is created automatically at `backend/data/app.db`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The Vite dev server proxies `/api` and `/ws` to the backend,
so the page should show **API: ok** and **WebSocket: open** when both are running.

## Scripts

| Location   | Command                    | Description                 |
| ---------- | -------------------------- | --------------------------- |
| `backend`  | `uvicorn app.main:app --reload` | Run API in dev mode    |
| `backend`  | `pytest`                   | Run tests                   |
| `backend`  | `ruff check .`             | Lint                        |
| `frontend` | `npm run dev`              | Start dev server            |
| `frontend` | `npm run build`            | Type-check & production build |
| `frontend` | `npm run lint`             | Lint (oxlint)               |

## Configuration

Backend settings are read from environment variables or `backend/.env`
(see [`backend/.env.example`](backend/.env.example)):

| Variable       | Default                                  |
| -------------- | ---------------------------------------- |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/app.db`      |
| `CORS_ORIGINS` | `http://localhost:5173`                  |
| `DEBUG`        | `true`                                   |

Frontend overrides go in `frontend/.env.local` (`VITE_API_URL`, `VITE_WS_URL`).

## Roadmap

- [ ] TikTok LIVE event ingestion (gifts, comments, likes)
- [ ] Game state & rules engine
- [ ] Database models and migrations (Alembic)
- [ ] Game UI / overlay for OBS

## Publishing to GitHub

```bash
git remote add origin https://github.com/<your-username>/TikTok-Live-Game.git
git push -u origin main
```
