# Gmail Job Search Daily Responsibility Agent

Minimal backend that reads the previous **7 calendar days** of Gmail and produces exactly one useful artifact:

```text
output/summary.md
```

The seven days are context only. The Markdown represents **today's responsibilities, upcoming events, meaningful updates, and job opportunities**.

## 1. Requirements

- Python 3.11+
- A Google Cloud project with Gmail API enabled
- OAuth desktop credentials for the Gmail API
- An OpenAI-compatible LLM endpoint that supports JSON responses

## 2. Install

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

## 3. Gmail OAuth setup

1. Open Google Cloud Console.
2. Create/select a project.
3. Enable **Gmail API**.
4. Configure the OAuth consent screen.
5. Create an OAuth **Desktop app** credential.
6. Download the JSON file as:

```text
credentials.json
```

Put it in the project root, or set `GMAIL_CREDENTIALS_FILE` to another path.

The application requests only:

```text
https://www.googleapis.com/auth/gmail.readonly
```

The first run opens a browser for OAuth. Gmail credentials are not collected by this application.

After successful authorization, the OAuth refresh token is saved to `token.json`.

## 4. Configure the LLM

Copy:

```text
.env.example
```

to:

```text
.env
```

Then set:

```env
LLM_API_KEY=your-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=your-json-capable-model
```

`LLM_BASE_URL` can point to another OpenAI-compatible provider.

## 5. Run

```bash
python main.py
```

Optional:

```bash
python main.py --print
```

Expected console flow:

```text
Connecting to Gmail...
Current date: 23 September 2026
Reading Gmail context: 17 September → 23 September
Emails found: 84
Job-related emails: 17
Analyzing current responsibilities...
Generating output/summary.md...
Done.
```

## 6. Output

Every run overwrites:

```text
output/summary.md
```

There is no weekly Markdown file and no UI.

## Architecture

```text
Gmail API
   ↓
7-calendar-day retrieval
   ↓
Email parsing
   ↓
LLM classification
   ↓
Structured event extraction
   ↓
Current-window state/cache
   ↓
Daily responsibility analysis
   ↓
Deterministic Markdown renderer
   ↓
output/summary.md
```

## Important design details

### Seven-day context

If today is September 23, the exact local-date context is:

```text
September 17 through September 23
```

The configured `TIMEZONE` determines the local date.

### Current-state reasoning

The LLM receives all relevant events in the current window. Later events can resolve earlier actions.

Example:

```text
Sep 17: Complete assessment by Sep 23
Sep 22: Assessment completed
```

The final output should not ask you to complete the assessment.

### Pending recruiter response

If a recruiter asks for interview availability and no later response is present in the current context, the daily analyzer can surface it as a current action.

### Job alerts

Job alerts are treated separately from actual applications.

### Deterministic Markdown

The LLM returns structured data. Python renders the Markdown, so formatting stays predictable.

## Production notes

For Docker/Cloud Run/Azure Container Apps/GitHub Actions:

- Store OAuth credentials and LLM credentials as secrets.
- Persist `token.json` securely if using user OAuth.
- Persist `state.json` only if you want cache reuse.
- For a cloud scheduler, run `python main.py` once per day.
- Keep `TIMEZONE=Asia/Kolkata` for an India-based daily boundary.

For a production multi-user deployment, replace local OAuth token storage with encrypted secret/database storage and use per-user Gmail authorization.

## Files

```text
job-agent/
├── main.py
├── config.py
├── models.py
├── gmail_client.py
├── email_parser.py
├── llm.py
├── classifier.py
├── extractor.py
├── responsibility.py
├── markdown_generator.py
├── state.py
├── output/
│   └── summary.md
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```
