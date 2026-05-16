import json
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from models import DiscoverRequest
from agents.discovery_agent import run_discovery_agent
from agents.intelligence_agent import run_intelligence_agent

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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


@app.get("/health")
async def health():
    return {"status": "ok"}
