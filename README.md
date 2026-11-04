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


## Quiz MVP (demo mode)

This branch includes a local-only quiz simulation. It **does not connect to TikTok LIVE**.
The game begins at question 1 (answer: `jacket`) and cycles through eight
Vietnamese-to-English questions every 30 seconds. Correct answers earn 10 points
per viewer per question; scores and history are held in memory and reset on restart.

1. Run backend and frontend using the setup instructions above.
2. Visit http://localhost:5173/ to use the demo controls.
3. Submit a player name and an English answer, or click Next Question.
4. Add an OBS Browser Source pointing to `http://localhost:5173/?overlay=1`,
   with width **1080** and height **1920** to show only the portrait overlay.

Demo REST API:
- `GET /api/game/state` — current question, timer and scores.
- `POST /api/game/answer` — simulated comment, JSON `{"name":"viewer","answer":"jacket"}`.
- `POST /api/game/next` — manually advance question.

WebSocket broadcasts `{"type":"game_state","data":...}` on each tick and score update.

**Safety:** demo write endpoints do not have authentication. Run only on your own
computer, bind Uvicorn to `127.0.0.1` (the default), and do not publish the
backend on a public server. Production TikTok integration, persistence,
moderation and admin authentication are future work.

Run backend tests with `cd backend && pytest` and frontend checks using
`cd frontend && npm run build && npm run lint`.


## TikTok LIVE integration (optional, experimental)

> The TikTokLive Python package is **unofficial**. Public TikTok LIVE chat
> ingestion can stop working when TikTok changes its protocol, or may not be
> supported for a specific account/region. Test with your own public livestream.

1. Start from the branch `feature/tiktok-live-integration`.
2. With Python 3.12, install the optional dependency:
   `python -m pip install -r backend/requirements-live.txt` from the project root
   (or `pip install -r requirements-live.txt` while in `backend`).
3. Start FastAPI **on localhost only**:
   `cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
4. In another terminal: `cd frontend && npm ci && npm run dev`.
5. Open `http://localhost:5173`, enter the public LIVE account's @username,
   and click **Kết nối LIVE**.
6. When the status says `connected`, viewers can type English answers in
   TikTok comments. Correct answers earn 10 points once per question per
   TikTok unique_id; incorrect comments do not score.
7. Keep OBS Browser Source on `http://localhost:5173/?overlay=1`.

REST endpoints: `GET /api/tiktok/status`, `POST /api/tiktok/connect`
(JSON `{"username":"example"}`), `POST /api/tiktok/disconnect`.
Start/stop endpoints accept **loopback clients only** and have **no authentication**;
do not expose the backend to your LAN or the public internet. Demo mode remains
available. Status updates are sent through the existing WebSocket. The current
implementation retries failed connections up to three times; persistent
connections and automated reconnection need further real-stream testing.

No TikTok credentials, cookies, or passwords are required by this integration.
