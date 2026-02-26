# Clause — AI Contract Review Bot

An AI-powered contract analysis tool built with the Claude API. Upload or paste any contract (NDA, service agreement, employment letter, vendor agreement) and get a structured analysis with risk flags — in plain English.

---

## Features

- **PDF & Text Upload** — drag-and-drop PDF or paste raw text
- **Claude-Powered Analysis** — key parties, dates, payment terms, termination clauses
- **Risk Flag System** — color-coded HIGH / MEDIUM / LOW flags for auto-renewals, indemnity traps, liability caps, IP risks, and missing exit clauses
- **Plain-English Summary** — non-lawyer friendly output
- **Recommendations** — actionable next steps

---

## Tech Stack

| Layer | Tool |
|-------|------|
| AI | Claude API (`claude-sonnet-4-6`) |
| Backend | Python + FastAPI |
| Frontend | Vanilla HTML/CSS/JS (single file) |
| PDF Parsing | PyMuPDF (`fitz`) |

---

## Setup & Run (< 5 minutes)

### Prerequisites
- Python 3.9+
- Anthropic API key from [console.anthropic.com](https://console.anthropic.com)

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/contract-review-bot.git
cd contract-review-bot
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Start the server
```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 4. Open the app
Visit [http://localhost:8000](http://localhost:8000) in your browser.

### 5. Analyze a contract
1. Enter your Anthropic API key
2. Upload a PDF or paste contract text
3. Click **Analyze Contract →**
4. View the structured analysis with risk flags

---

## Testing

A sample NDA is included in `/sample/sample_nda.txt` — paste its contents to test the app immediately.

---

## Project Structure

```
contract-review-bot/
├── backend/
│   └── main.py          # FastAPI app + Claude integration
├── frontend/
│   └── index.html       # Single-file UI
├── sample/
│   └── sample_nda.txt   # Test contract
├── requirements.txt
└── README.md
```

---

## Deploy on Vercel

This app uses a Python backend which Vercel supports via Serverless Functions.

1. Add a `vercel.json` at the root:
```json
{
  "builds": [{ "src": "backend/main.py", "use": "@vercel/python" }],
  "routes": [{ "src": "/(.*)", "dest": "backend/main.py" }]
}
```
2. Push to GitHub and import to Vercel.
3. Done — Vercel auto-detects FastAPI.

---

## API Reference

### `POST /analyze`

**Form Data:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `api_key` | string | ✅ | Anthropic API key |
| `file` | file | one of | PDF or TXT file |
| `text` | string | one of | Raw contract text |

**Response:** JSON object with summary, parties, dates, payment terms, termination, renewal, risk flags, and recommendations.

---

## Notes

- API keys are sent directly to Anthropic's API and are **never stored or logged**
- Contracts are truncated at 100,000 characters to stay within context limits
- Requires `pymupdf` for PDF support (included in `requirements.txt`)
