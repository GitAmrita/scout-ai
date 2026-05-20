import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from models import DiscoverRequest, ApplyRequest, AutoApplyAnalyzeRequest, AutoApplyFillRequest, AutoApplySubmitRequest
from agents.discovery_agent import run_discovery_agent
from agents.intelligence_agent import run_intelligence_agent
from agents.application_agent import run_application_agent
from agents.auto_apply_agent import analyze_form, fill_form, submit_form

RESUME_PDF_PATH = Path(__file__).parent.parent / "data" / "resume.pdf"

app = FastAPI()

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/discover")
async def discover(request: DiscoverRequest):
    async def event_stream():
        companies = []
        async for event in run_discovery_agent(request.prompt):
            yield {"data": json.dumps(event)}
            if event.get("type") == "company_found" and event.get("company"):
                companies.append(event["company"])

        if companies:
            async for event in run_intelligence_agent(companies):
                yield {"data": json.dumps(event)}

    return EventSourceResponse(event_stream())


@app.post("/api/apply")
async def apply(request: ApplyRequest):
    async def event_stream():
        async for event in run_application_agent(request.company, request.analysis):
            yield {"data": json.dumps(event)}

    return EventSourceResponse(event_stream())


@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    RESUME_PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    RESUME_PDF_PATH.write_bytes(content)
    return {"status": "ok", "filename": file.filename}


@app.post("/api/auto-apply/analyze")
async def auto_apply_analyze(request: AutoApplyAnalyzeRequest):
    async def event_stream():
        async for event in analyze_form(request.job_url):
            yield {"data": json.dumps(event)}

    return EventSourceResponse(event_stream())


@app.post("/api/auto-apply/fill")
async def auto_apply_fill(request: AutoApplyFillRequest):
    async def event_stream():
        async for event in fill_form(request.session_id, request.fields):
            yield {"data": json.dumps(event)}

    return EventSourceResponse(event_stream())


@app.post("/api/auto-apply/submit")
async def auto_apply_submit(request: AutoApplySubmitRequest):
    async def event_stream():
        async for event in submit_form(request.session_id):
            yield {"data": json.dumps(event)}

    return EventSourceResponse(event_stream())


@app.get("/health")
async def health():
    return {"status": "ok"}
