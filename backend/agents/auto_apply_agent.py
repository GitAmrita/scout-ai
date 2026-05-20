import base64
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, AsyncIterator

from google import genai
from google.genai import types
from playwright.async_api import async_playwright

_sessions: dict[str, dict[str, Any]] = {}

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

RESUME_PDF_PATH = Path(__file__).parent.parent.parent / "data" / "resume.pdf"

ANALYZE_SYSTEM = """You receive a JSON list of form fields extracted directly from a job application page DOM.
Each field has: id, name, type, tag, placeholder, label.

Map candidate data to each field you can confidently fill.

Candidate:
- first_name: Amrita
- last_name: Chowdhury
- full_name: Amrita Chowdhury
- email: amritabtech@gmail.com
- phone: (leave blank if not available)
- linkedin: https://www.linkedin.com/in/amrita-chowdhury
- github: https://github.com/GitAmrita
- location: United States
- work_authorization: Yes, authorized to work in the US
- years_experience: 15+
- current_title: Senior Software Engineer
- referral_source: LinkedIn

Return valid JSON only — no markdown fences:
{
  "fields": [
    {
      "id": "exact id attribute from DOM (empty string if none)",
      "name": "exact name attribute from DOM (empty string if none)",
      "label": "human-readable label for display",
      "type": "the field type",
      "tag": "input|textarea|select",
      "value": "what to fill",
      "confidence": "high|medium|low",
      "skip": false
    }
  ],
  "has_resume_upload": true,
  "notes": "any notes"
}

Rules:
- Only include fields you can map to candidate data — skip unknowns
- For file/resume fields: set type "file", value ""
- For cover letter / open-ended text: set value "" (user fills manually)
- For salary: set value "" and skip: true
- Set skip: true for captcha, hidden, or irrelevant fields"""

# JS to extract all visible form fields with their real DOM attributes
_EXTRACT_FIELDS_JS = """
() => {
    const results = [];
    const seen = new Set();
    const els = document.querySelectorAll(
        'input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="reset"]), textarea, select'
    );
    els.forEach(el => {
        const key = (el.id || '') + '|' + (el.name || '');
        if (seen.has(key) && key !== '|') return;
        seen.add(key);

        let labelText = '';
        if (el.id) {
            const lbl = document.querySelector('label[for="' + el.id + '"]');
            if (lbl) labelText = lbl.innerText.trim().replace(/\\s+/g, ' ');
        }
        if (!labelText) {
            labelText = el.getAttribute('aria-label') || el.placeholder || el.name || '';
        }

        results.push({
            id: el.id || '',
            name: el.name || '',
            type: el.type || el.tagName.toLowerCase(),
            tag: el.tagName.toLowerCase(),
            placeholder: el.placeholder || '',
            label: labelText
        });
    });
    return results;
}
"""


async def analyze_form(job_url: str) -> AsyncIterator[dict]:
    yield {"type": "auto_apply_start", "message": "Opening application page..."}

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=False)
    page = await browser.new_page()

    await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2000)

    current_url = page.url
    yield {"type": "auto_apply_navigated", "message": f"Loaded: {current_url}"}

    dom_fields = await page.evaluate(_EXTRACT_FIELDS_JS)
    screenshot_bytes = await page.screenshot(full_page=False)
    screenshot_b64 = base64.b64encode(screenshot_bytes).decode()

    # Keep browser open — session persists through fill and submit
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {"pw": pw, "browser": browser, "page": page, "url": current_url}

    yield {"type": "auto_apply_analyzing", "message": f"Found {len(dom_fields)} DOM fields, mapping with AI..."}

    response = await client.aio.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"Form fields from DOM:\n{json.dumps(dom_fields, indent=2)}",
        config=types.GenerateContentConfig(system_instruction=ANALYZE_SYSTEM),
    )

    mapping = _parse_json(response.text)
    fields = mapping.get("fields", [])

    yield {
        "type": "auto_apply_analyzed",
        "session_id": session_id,
        "fields": fields,
        "screenshot": screenshot_b64,
        "notes": mapping.get("notes", ""),
        "has_resume_upload": mapping.get("has_resume_upload", False),
        "form_url": current_url,
        "message": f"Mapped {len(fields)} fields.",
    }


async def fill_form(session_id: str, fields: list[dict]) -> AsyncIterator[dict]:
    """Fill the already-open browser. Browser stays open for manual edits."""
    session = _sessions.get(session_id)
    if not session:
        yield {"type": "auto_apply_error", "message": "Session not found — please re-analyze the form."}
        return

    yield {"type": "auto_apply_filling", "message": "Filling form..."}

    page = session["page"]
    filled, skipped = await _fill_fields(page, fields)

    screenshot_bytes = await page.screenshot(full_page=True)
    screenshot_b64 = base64.b64encode(screenshot_bytes).decode()

    yield {
        "type": "auto_apply_filled",
        "session_id": session_id,
        "screenshot": screenshot_b64,
        "filled_count": len(filled),
        "filled": filled,
        "skipped": skipped,
        "message": f"Filled {len(filled)} fields. Browser is open — complete any remaining fields, then submit.",
    }


async def submit_form(session_id: str) -> AsyncIterator[dict]:
    """Click submit on the already-open browser session."""
    yield {"type": "auto_apply_submitting", "message": "Submitting..."}

    session = _sessions.pop(session_id, None)
    if not session:
        yield {"type": "auto_apply_error", "message": "Session expired — please fill the form again."}
        return

    page = session["page"]
    try:
        submit = page.locator('button[type="submit"], input[type="submit"]').first
        if not await submit.is_visible(timeout=3000):
            submit = page.get_by_role("button", name=re.compile("submit|apply", re.IGNORECASE)).first
        await submit.click()
        await page.wait_for_timeout(3000)

        confirm_bytes = await page.screenshot(full_page=False)
        confirm_b64 = base64.b64encode(confirm_bytes).decode()
        yield {"type": "auto_apply_submitted", "screenshot": confirm_b64, "message": "Application submitted!"}
    except Exception as e:
        yield {"type": "auto_apply_error", "message": f"Could not click submit: {e}"}
    finally:
        await session["browser"].close()
        await session["pw"].stop()


async def _fill_fields(page, fields: list[dict]) -> tuple[list, list]:
    has_pdf = RESUME_PDF_PATH.exists()
    filled, skipped = [], []

    for field in fields:
        if field.get("skip"):
            continue

        field_id = field.get("id", "")
        field_name = field.get("name", "")
        label = field.get("label") or field_id or field_name
        value = field.get("value", "")

        # File upload
        if field.get("type") == "file":
            if has_pdf:
                try:
                    selector = f'#{field_id}' if field_id else f'[name="{field_name}"]'
                    await page.locator(selector).set_input_files(str(RESUME_PDF_PATH))
                    filled.append(label)
                except Exception:
                    skipped.append(label)
            continue

        if not value:
            continue

        # Build selector: id takes priority over name
        if field_id:
            selector = f'#{field_id}'
        elif field_name:
            selector = f'[name="{field_name}"]'
        else:
            skipped.append(label)
            continue

        try:
            locator = page.locator(selector).first
            if not await locator.is_visible(timeout=2000):
                skipped.append(label)
                continue

            tag = field.get("tag", "input")
            field_type = field.get("type", "text")

            if tag == "select":
                try:
                    await locator.select_option(label=value)
                except Exception:
                    await locator.select_option(value=value)
            elif field_type == "checkbox":
                if value.lower() in ("true", "yes", "1"):
                    await locator.check()
            else:
                await locator.fill(value)

            filled.append(label)
        except Exception:
            skipped.append(label)

    return filled, skipped


def _parse_json(text: str) -> dict:
    text = re.sub(r"```json\s*|\s*```", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"fields": [], "has_resume_upload": False, "notes": "Could not parse form."}
