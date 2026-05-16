# Deployment

Scout AI is deployed across two services:

| Service | Platform | URL |
|---|---|---|
| Frontend (Next.js) | Vercel | https://scout-ai-mu.vercel.app |
| Backend (FastAPI) | Render | https://scout-ai-backend-bczu.onrender.com |

## Environment Variables

### Vercel (Frontend)
| Key | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://scout-ai-backend-bczu.onrender.com` |

### Render (Backend)
| Key | Value |
|---|---|
| `GEMINI_API_KEY` | your Gemini API key |
| `ALLOWED_ORIGINS` | `https://scout-ai-mu.vercel.app` |

## Deploy Process

Both services auto-deploy on every push to `main`.

- **Frontend changes** (inside `frontend/`) → push to `main` → Vercel deploys automatically
- **Backend changes** (inside `backend/`) → push to `main` → Render deploys automatically

> Note: Changes outside `backend/` (e.g. frontend files) do not trigger a Render redeploy since its root directory is set to `backend/`.

## Render Cold Start

Render's free tier spins down after 15 minutes of inactivity. The first request after idle takes ~30-60 seconds to wake up. Open `https://scout-ai-backend-bczu.onrender.com/docs` before a demo to pre-warm it.

## Local Development

See [README.md](README.md) for local setup instructions.
