import json
import re
from pathlib import Path
from typing import AsyncIterator

from openai import OpenAI

from tools.search import search_web
from tools.scraper import scrape_url

client = OpenAI()

RESUME_PATH = Path(__file__).parent.parent.parent / "data" / "resume.md"
COMPANIES_PATH = Path(__file__).parent.parent.parent / "data" / "companies.md"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": (
                "Search the web for healthcare AI startups, job openings, funding news, and hiring signals. "
                "Use targeted queries like 'healthcare AI startup hiring backend engineer 2025' or "
                "'YC healthcare AI companies careers'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scrape_url",
            "description": (
                "Fetch and read the content of a URL. Use for company careers pages, "
                "about pages, and individual job listings."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL to fetch"}
                },
                "required": ["url"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are the Discovery Agent for Scout, an autonomous AI career intelligence system.

Your mission: Find healthcare AI startups that are actively hiring backend/software engineers matching the candidate's profile.

Strategy:
1. Search for healthcare AI startup lists — YC batches, recent funding rounds, industry directories
2. Identify 5-8 strong candidate companies
3. For each company, locate and scrape their careers page for open engineering roles
4. Gather hiring signals: funding stage, team growth, recent news

Target companies that:
- Build AI/ML products in healthcare (diagnostics, clinical workflows, health data, EHR, billing)
- Have Python / backend / data engineering / platform roles open
- Are Seed to Series B stage
- Show active hiring signals

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

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"User goal: {user_prompt}\n\n"
                f"Candidate resume:\n{resume}\n\n"
                "Find healthcare AI companies actively hiring engineers that match this candidate."
            ),
        },
    ]

    yield {"type": "agent_start", "message": "Discovery Agent is searching for opportunities..."}

    for _ in range(15):  # cap iterations
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOLS,
        )

        choice = response.choices[0]
        message = choice.message
        messages.append(message)

        if message.content:
            yield {"type": "agent_thinking", "message": message.content[:300]}

        tool_calls = message.tool_calls or []

        if choice.finish_reason == "stop" or not tool_calls:
            final_text = message.content or ""
            companies = _parse_companies(final_text)
            for company in companies:
                yield {"type": "company_found", "company": company}
            _save_companies(companies)
            yield {"type": "done", "message": f"Found {len(companies)} companies.", "companies": companies}
            return

        for tool_call in tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
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

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": content[:8000],
            })

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
