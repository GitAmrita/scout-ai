# Scout AI

## Local Setup

When the user says "set up locally", run these commands:

**Terminal 1 — Backend:**
```bash
cd /Users/amy/Documents/Code/scout-ai/backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd /Users/amy/Documents/Code/scout-ai/frontend
npm run dev
```

Then open `http://localhost:3000`.

## Project Structure

- `backend/` — FastAPI app, entry point is `main.py`
- `backend/agents/` — discovery, intelligence, and application agents
- `backend/tools/` — `scraper.py` (fetch + clean web pages) and `search.py` (DuckDuckGo search)
- `frontend/` — Next.js 16 app, main UI is `frontend/app/page.tsx`

## Environment Variables

**Backend (`backend/.env`):**
- `GEMINI_API_KEY` — Google Gemini API key
- `ALLOWED_ORIGINS` — comma-separated CORS origins (e.g. `http://localhost:3000,https://scout-ai-mu.vercel.app`)

**Frontend (`frontend/.env.local`):**
- `NEXT_PUBLIC_API_URL` — backend base URL (e.g. `http://localhost:8000` locally, `https://scout-ai-backend-bczu.onrender.com` in prod)

## Deployment (Vercel + Render)

See `docs/DEPLOYMENT.md` for full deployment details. Do not commit `.env` or `.env.local`.
