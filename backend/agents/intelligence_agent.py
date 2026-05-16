import json
import os
import re
from pathlib import Path
from typing import AsyncIterator

from google import genai
from google.genai import types

from tools.scraper import scrape_url

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

RESUME_PATH = Path(__file__).parent.parent.parent / "data" / "resume.md"

SYSTEM_PROMPT = """You are the Intelligence Agent for Scout, an AI career intelligence system.

Your job: Analyze how well a candidate matches a specific company and role.

Fit scoring — score 0 to 100 based on domain overlap across these categories:
- Backend engineering (APIs, microservices, distributed systems): up to 25 points
- Data pipelines & ETL (ingestion, normalization, transformation at scale): up to 25 points
- Healthcare data experience (claims, EHR, clinical workflows, interoperability): up to 20 points
- Cloud infrastructure (AWS, GCP, or Azure): up to 20 points
- AI/ML-adjacent engineering (building infra around models): up to 10 points
- Language overlap bonus (if specific languages match): up to 5 bonus points

Rules:
- Be honest about gaps — do not inflate scores
- Language mismatch is NOT a gap, it is neutral
- Focus on domain depth, not keyword matching

Output valid JSON only — no markdown fences, no explanation outside the JSON:
{
  "name": "<company name>",
  "fit_score": <0-100>,
  "fit_label": "<Strong Match | Good Match | Partial Match | Weak Match>",
  "tech_stack": ["inferred technology 1", "inferred technology 2"],
  "fit_reasons": ["specific reason 1", "specific reason 2", "specific reason 3"],
  "gaps": ["gap 1", "gap 2"],
  "recommendation": "<High priority | Worth exploring | Low priority>"
}"""


async def run_intelligence_agent(companies: list[dict]) -> AsyncIterator[dict]:
    resume = RESUME_PATH.read_text()

    yield {"type": "analysis_start", "message": f"Intelligence Agent is analyzing {len(companies)} companies..."}

    analyses = []

    for company in companies:
        job_context = ""
        for job in company.get("jobs", [])[:2]:
            url = job.get("url", "")
            if url and url != company.get("careers_url", ""):
                try:
                    content = await scrape_url(url)
                    job_context += f"\nJob listing ({job.get('title', '')}):\n{content[:2000]}\n"
                except Exception:
                    pass

        user_message = (
            f"Candidate resume:\n{resume}\n\n"
            f"Company to analyze:\n{json.dumps(company, indent=2)}\n"
            f"{job_context}\n"
            "Analyze the fit and return JSON."
        )

        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
            ),
        )

        analysis = _parse_analysis(response.text, company["name"])
        analyses.append(analysis)
        yield {"type": "company_analyzed", "analysis": analysis}

    analyses.sort(key=lambda x: x.get("fit_score", 0), reverse=True)
    yield {
        "type": "analysis_done",
        "message": f"Analyzed {len(analyses)} companies.",
        "analyses": analyses,
    }


def _parse_analysis(text: str, company_name: str) -> dict:
    text = re.sub(r"```json\s*|\s*```", "", text).strip()
    try:
        result = json.loads(text)
        result["name"] = company_name
        return result
    except json.JSONDecodeError:
        return {
            "name": company_name,
            "fit_score": 0,
            "fit_label": "Unknown",
            "tech_stack": [],
            "fit_reasons": [],
            "gaps": ["Could not analyze fit"],
            "recommendation": "Unknown",
        }
