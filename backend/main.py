"""
Contract & Document Review Bot — Backend
FastAPI + Claude API (claude-sonnet-4-6)
"""

import os
import json
import re
import tempfile
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import anthropic

try:
    import fitz
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

app = FastAPI(title="Contract Review Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="../frontend"), name="static")

@app.get("/")
def root():
    return FileResponse("../frontend/index.html")

@app.get("/health")
def health():
    return {"status": "ok", "pdf_support": PDF_SUPPORT}


def extract_text_from_pdf(file_bytes: bytes) -> str:
    if not PDF_SUPPORT:
        raise HTTPException(status_code=400, detail="PDF support not installed.")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    doc = fitz.open(tmp_path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    os.unlink(tmp_path)
    return text.strip()


SYSTEM_PROMPT = """You are an expert contract lawyer and legal analyst.
You MUST respond with valid JSON only.
Do NOT include any text before or after the JSON.
Do NOT use markdown code blocks.
Do NOT write ```json or ``` anywhere.
Just output the raw JSON object and nothing else."""

ANALYSIS_PROMPT = """Analyze this contract and return ONLY a JSON object with EXACTLY this structure. No other text:

{
  "summary": "1-2 paragraph plain-English summary",
  "parties": [
    { "name": "party name", "role": "their role" }
  ],
  "key_dates": [
    { "label": "date label", "value": "date value" }
  ],
  "payment_terms": {
    "amount": "payment amount or N/A",
    "schedule": "payment schedule or N/A",
    "penalties": "late penalties or N/A"
  },
  "termination_clauses": [
    { "type": "termination type", "description": "description", "notice_required": "notice period" }
  ],
  "renewal_terms": {
    "auto_renews": false,
    "renewal_period": "period or N/A",
    "opt_out_deadline": "deadline or N/A"
  },
  "risk_flags": [
    {
      "category": "auto_renewal",
      "severity": "high",
      "title": "risk title",
      "description": "plain English explanation",
      "clause_reference": "relevant quote from contract"
    }
  ],
  "overall_risk_level": "high",
  "recommendations": [
    "recommendation 1",
    "recommendation 2"
  ]
}

CONTRACT TEXT:
""" + "{contract_text}"


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
            contract_text = extract_text_from_pdf(raw)
        else:
            contract_text = raw.decode("utf-8", errors="replace")
    elif text and text.strip():
        contract_text = text.strip()
    else:
        raise HTTPException(status_code=400, detail="No contract provided.")

    if len(contract_text) < 50:
        raise HTTPException(status_code=400, detail="Contract text is too short.")

    contract_text = contract_text[:100_000]

    client = anthropic.Anthropic(api_key=api_key)
    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": ANALYSIS_PROMPT.replace("{contract_text}", contract_text),
                }
            ],
        )
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limit hit. Please wait and retry.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Claude API error: {str(e)}")

    raw_response = message.content[0].text.strip()

    # Remove markdown fences if present
    raw_response = re.sub(r"^```json\s*", "", raw_response)
    raw_response = re.sub(r"^```\s*", "", raw_response)
    raw_response = re.sub(r"\s*```$", "", raw_response)
    raw_response = raw_response.strip()

    # Extract JSON object if there's extra text
    match = re.search(r'\{.*\}', raw_response, re.DOTALL)
    if match:
        raw_response = match.group(0)

    try:
        result = json.loads(raw_response)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse response as JSON: {str(e)}"
        )

    return result