import json
import os
import re
from pathlib import Path
from typing import AsyncIterator

from google import genai
from google.genai import types

from tools.search import search_web
from tools.scraper import scrape_url

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

RESUME_PATH = Path(__file__).parent.parent.parent / "data" / "resume.md"
COMPANIES_PATH = Path(__file__).parent.parent.parent / "data" / "companies.md"

TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="search_web",
                description=(
                    "Search the web for healthcare AI startups, job openings, funding news, and hiring signals. "
                    "Use targeted queries like 'healthcare AI startup hiring backend engineer 2025' or "
                    "'YC healthcare AI companies careers'."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "query": types.Schema(
                            type=types.Type.STRING,
                            description="Search query",
                        )
                    },
                    required=["query"],
                ),
            ),
            types.FunctionDeclaration(
                name="scrape_url",
                description=(
                    "Fetch and read the content of a URL. Use for company careers pages, "
                    "about pages, and individual job listings."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "url": types.Schema(
                            type=types.Type.STRING,
                            description="Full URL to fetch",
                        )
                    },
                    required=["url"],
                ),
            ),
        ]
    )
]

SYSTEM_PROMPT = """You are the Discovery Agent for Scout, an autonomous AI career intelligence system.

Your mission: Find healthcare AI startups that are actively hiring backend/software engineers that match the candidate's technical strengths.

Matching philosophy: Do NOT match on specific programming languages. Instead match on technical domains. The candidate is a strong fit if the role overlaps with any of these strengths:
- Backend engineering (APIs, services, distributed systems) — language doesn't matter, Go/Rust/Java/Python are all fine; language overlap is a nice-to-have bonus, not a requirement
- Data pipelines & ETL (ingestion, normalization, transformation at scale)
- Healthcare data (claims, EHR, clinical data, interoperability)
- Cloud infrastructure (AWS, GCP, or Azure)
- Data modeling & databases (relational, analytical)
- AI/ML-adjacent engineering (building infrastructure around models, not necessarily research)

A role is a match if 2-3 of these domains overlap. Specific language requirements are irrelevant.

Strategy:
1. Start by scraping careers pages for this seed list of known healthcare AI companies:
   - Viz.ai: https://www.viz.ai/careers
   - PathAI: https://www.pathai.com/careers
   - Artera: https://artera.ai/careers
   - Abridge: https://www.abridge.com/careers
   - Ambience Healthcare: https://www.ambiencehealthcare.com/careers
   - Regard: https://www.regard.com/careers
   - Cohere Health: https://coherehealth.com/careers
2. Additionally search the web for 2-3 more healthcare AI startups actively hiring engineers
3. For each company, note open engineering roles and hiring signals
4. Include every company from the seed list — even if you cannot confirm a specific open role, include it as "likely hiring" based on their stage and growth

Aim to return 5-6 companies total.

When you have gathered enough information, output your findings as a JSON array in this exact format wrapped in ```json fences:

```json
[
  {
    "name": "Company Name",
    "website": "https://...",
    "careers_url": "https://.../careers",
    "description": "One or two sentences on what they build.",
    "funding": "Series A / $12M",
    "hiring_signals": ["Recently raised Series A", "Team doubled in past year"],
    "jobs": [
      {
        "title": "Senior Backend Engineer",
        "url": "https://...",
        "description": "Brief role description"
      }
    ]
  }
]
```"""


async def run_discovery_agent(user_prompt: str) -> AsyncIterator[dict]:
    resume = RESUME_PATH.read_text()

    chat = client.aio.chats.create(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=TOOLS,
        ),
    )

    yield {"type": "agent_start", "message": "Discovery Agent is searching for opportunities..."}

    initial_message = (
        f"User goal: {user_prompt}\n\n"
        f"Candidate resume:\n{resume}\n\n"
        "Find healthcare AI companies actively hiring engineers that match this candidate."
    )

    response = await chat.send_message(initial_message)

    for _ in range(15):
        text_parts = []
        function_calls = []

        for part in response.candidates[0].content.parts:
            if part.text:
                text_parts.append(part.text)
            if part.function_call:
                function_calls.append(part.function_call)

        text = "".join(text_parts)
        if text:
            yield {"type": "agent_thinking", "message": text[:300]}

        if not function_calls:
            companies = _parse_companies(text)
            for company in companies:
                yield {"type": "company_found", "company": company}
            _save_companies(companies)
            yield {"type": "done", "message": f"Found {len(companies)} companies.", "companies": companies}
            return

        tool_response_parts = []
        for fc in function_calls:
            name = fc.name
            args = dict(fc.args)
            yield {"type": "tool_call", "tool": name, "input": args}

            try:
                if name == "search_web":
                    result = await search_web(args["query"])
                    content = json.dumps(result)
                elif name == "scrape_url":
                    content = await scrape_url(args["url"])
                else:
                    content = "Unknown tool"
            except Exception as e:
                content = f"Error: {e}"
                yield {"type": "tool_error", "tool": name, "message": str(e)}

            tool_response_parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=name,
                        response={"result": content[:8000]},
                    )
                )
            )

        response = await chat.send_message(tool_response_parts)

    yield {"type": "done", "message": "Discovery complete."}


def _parse_companies(text: str) -> list[dict]:
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if not match:
        return []
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return []


def _save_companies(companies: list[dict]) -> None:
    lines = ["# Discovered Companies\n"]
    for c in companies:
        lines.append(f"## {c.get('name', 'Unknown')}")
        if c.get("website"):
            lines.append(f"**Website**: {c['website']}")
        if c.get("funding"):
            lines.append(f"**Funding**: {c['funding']}")
        if c.get("description"):
            lines.append(f"\n{c['description']}\n")
        signals = c.get("hiring_signals", [])
        if signals:
            lines.append("**Hiring Signals**:")
            for s in signals:
                lines.append(f"- {s}")
        jobs = c.get("jobs", [])
        if jobs:
            lines.append("\n**Open Roles**:")
            for job in jobs:
                title = job.get("title", "Role")
                url = job.get("url", "")
                lines.append(f"- [{title}]({url})" if url else f"- {title}")
        lines.append("")
    COMPANIES_PATH.write_text("\n".join(lines))
