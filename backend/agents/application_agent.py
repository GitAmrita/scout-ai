import json
import os
import re
from pathlib import Path
from typing import AsyncIterator

from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

RESUME_PATH = Path(__file__).parent.parent.parent / "data" / "resume.md"
APPLICATIONS_PATH = Path(__file__).parent.parent.parent / "data" / "applications.md"

SYSTEM_PROMPT = """You are the Application Agent for Scout, an AI career intelligence system.

Your job: Generate personalized application materials for a specific company and role.

Rules:
- Ground everything in the candidate's actual experience — never invent facts or achievements
- Tailored bullets: reframe existing resume achievements to highlight relevance to this company's domain and needs. Keep the original impact numbers intact.
- Why this company: specific and authentic — reference the company's actual mission, product, and technology. No generic statements.
- Application tips: tactical advice specific to this company and role, not generic job advice

Output valid JSON only — no markdown fences, no explanation outside the JSON:
{
  "why_this_company": "2-3 sentences...",
  "tailored_bullets": ["bullet 1", "bullet 2", "bullet 3", "bullet 4"],
  "application_tips": ["tip 1", "tip 2", "tip 3"]
}"""


async def run_application_agent(company: dict, analysis: dict) -> AsyncIterator[dict]:
    resume = RESUME_PATH.read_text()

    yield {"type": "application_start", "message": f"Preparing your application for {company['name']}..."}

    user_message = (
        f"Candidate resume:\n{resume}\n\n"
        f"Company:\n{json.dumps(company, indent=2)}\n\n"
        f"Fit analysis:\n{json.dumps(analysis, indent=2)}\n\n"
        "Generate personalized application materials."
    )

    response = await client.aio.models.generate_content(
        model="gemini-2.0-flash",
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
        ),
    )

    materials = _parse_materials(response.text)
    _save_application(company["name"], materials)

    yield {"type": "application_ready", "materials": materials}
    yield {"type": "application_done", "message": f"Application materials ready for {company['name']}."}


def _parse_materials(text: str) -> dict:
    text = re.sub(r"```json\s*|\s*```", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "why_this_company": "Could not generate materials.",
            "tailored_bullets": [],
            "application_tips": [],
        }


def _save_application(company_name: str, materials: dict) -> None:
    entry = f"\n## {company_name}\n\n"
    entry += f"### Why This Company\n{materials.get('why_this_company', '')}\n\n"

    bullets = materials.get("tailored_bullets", [])
    if bullets:
        entry += "### Tailored Resume Bullets\n"
        for b in bullets:
            entry += f"- {b}\n"
        entry += "\n"

    tips = materials.get("application_tips", [])
    if tips:
        entry += "### Application Tips\n"
        for t in tips:
            entry += f"- {t}\n"
        entry += "\n"

    existing = APPLICATIONS_PATH.read_text() if APPLICATIONS_PATH.exists() else "# Application Materials\n"
    APPLICATIONS_PATH.write_text(existing + entry)
