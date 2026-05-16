# scout-ai
Scout is an autonomous multi-agent career intelligence system that helps users discover high-potential companies, analyze career fit, and prepare personalized job applications.

## Local Setup

**Prerequisites:** Python 3.11+, Node.js 18+

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then fill in your GEMINI_API_KEY
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
# .env.local is already configured for local dev (points to localhost:8000)
npm run dev
```

Open `http://localhost:3000` in your browser.
