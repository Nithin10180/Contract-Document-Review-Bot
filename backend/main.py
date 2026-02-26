"""
Contract & Document Review Bot — Vercel Compatible
FastAPI + Claude API with embedded HTML
"""

import os
import json
import re
import tempfile
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import anthropic

try:
    import fitz
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

app = FastAPI(title="Contract Review Bot")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

HTML_CONTENT = open(os.path.join(os.path.dirname(__file__), "../frontend/index.html")).read() if os.path.exists(os.path.join(os.path.dirname(__file__), "../frontend/index.html")) else """<!DOCTYPE html><html><body><h1>Loading...</h1></body></html>"""

SYSTEM_PROMPT = """You are an expert contract lawyer. Respond with valid JSON only. No markdown, no code blocks, no extra text."""

ANALYSIS_PROMPT = """Analyze this contract. Return ONLY this JSON structure, nothing else:
{
  "summary": "plain English summary",
  "parties": [{"name": "name", "role": "role"}],
  "key_dates": [{"label": "label", "value": "value"}],
  "payment_terms": {"amount": "amount", "schedule": "schedule", "penalties": "penalties"},
  "termination_clauses": [{"type": "type", "description": "desc", "notice_required": "notice"}],
  "renewal_terms": {"auto_renews": false, "renewal_period": "period", "opt_out_deadline": "deadline"},
  "risk_flags": [{"category": "category", "severity": "high", "title": "title", "description": "desc", "clause_reference": "quote"}],
  "overall_risk_level": "high",
  "recommendations": ["rec1", "rec2"]
}

CONTRACT:
"""

def get_html():
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../frontend/index.html")
    if os.path.exists(html_path):
        with open(html_path) as f:
            return f.read()
    return "<h1>Frontend not found</h1>"

@app.get("/", response_class=HTMLResponse)
def root():
    return HTMLResponse(content=get_html())

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/analyze")
async def analyze_contract(
    file: UploadFile = File(None),
    text: str = Form(None),
    api_key: str = Form(...),
):
    contract_text = ""
    if file and file.filename:
        raw = await file.read()
        if file.filename.lower().endswith(".pdf"):
            if not PDF_SUPPORT:
                raise HTTPException(status_code=400, detail="PDF not supported on this server. Please paste text instead.")
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(raw)
                tmp_path = tmp.name
            doc = fitz.open(tmp_path)
            contract_text = "\n".join(page.get_text() for page in doc)
            doc.close()
            os.unlink(tmp_path)
        else:
            contract_text = raw.decode("utf-8", errors="replace")
    elif text and text.strip():
        contract_text = text.strip()
    else:
        raise HTTPException(status_code=400, detail="No contract provided.")

    if len(contract_text) < 50:
        raise HTTPException(status_code=400, detail="Contract text too short.")

    contract_text = contract_text[:100_000]
    client = anthropic.Anthropic(api_key=api_key)

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": ANALYSIS_PROMPT + contract_text}],
        )
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limit hit. Please wait.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Claude API error: {str(e)}")

    raw = message.content[0].text.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"^```\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw).strip()
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        raw = match.group(0)

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Parse error: {str(e)}")
