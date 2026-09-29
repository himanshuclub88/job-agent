from __future__ import annotations

import json
import time
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr
import base64
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI app
app = FastAPI(
    title="AI Power Assistant API",
    description="Backend API for Job Search Daily Intelligence Agent",
    version="1.0.0",
)

# Enable CORS safely for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False, # Changed to False to prevent strict browser CORS blocks
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory status tracker for the long-running pipeline
pipeline_state: dict[str, Any] = {
    "is_running": False,
    "message": "Idle",
    "duration_str": None,
    "last_run": None,
    "logs": [],          
    "current_step": "Phase 1/4"
}


def emit_log(msg: str, step: str | None = None) -> None:
    """Appends actual server events with local timestamps for the frontend to poll."""
    global pipeline_state
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_log = f"[{timestamp}] {msg}"
    print(formatted_log)
    pipeline_state["logs"].append(formatted_log)
    if step:
        pipeline_state["current_step"] = step


def get_settings():
    from config import settings
    return settings


def load_json_file(file_path: Path) -> dict[str, Any]:
    if not file_path.exists():
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to read {file_path.name}: {str(e)}"
        )


def execute_pipeline() -> None:
    """Core extraction and classification pipeline running as a background task."""
    global pipeline_state
    pipeline_state["is_running"] = True
    pipeline_state["message"] = "Engine running: fetching and analyzing emails..."
    pipeline_state["duration_str"] = None
    pipeline_state["logs"] = []
    
    emit_log("Engine session started.", "Phase 1/4")
    start_time = time.perf_counter()

    try:
        # Import pipeline components inside task
        from classifier import classify_emails
        from config import settings
        from extractor import extract_job_events_from_emails
        from future_events import FutureEventStore
        from gmail_client import GmailClient
        from html_generator import generate_html
        from responsibility import analyze_today
        from state import StateStore

        emit_log("Authenticating and connecting to Gmail API...", "Phase 1/4")
        gmail = GmailClient(settings)
        today = gmail.today()
        start_date, end_date = gmail.context_dates(today)
        emit_log(f"Fetching mailbox context: {start_date:%d %b} → {end_date:%d %b %Y}", "Phase 1/4")

        emails = gmail.fetch_messages(start_date, end_date)
        emit_log(f"Retrieved {len(emails)} messages from Gmail.", "Phase 1/4")

        if not emails:
            emit_log("No emails found in this timeframe. Pipeline terminating early.", "Done")
            pipeline_state["is_running"] = False
            pipeline_state["message"] = "No emails found in the current window."
            pipeline_state["duration_str"] = "0 seconds"
            return

        emit_log("Checking state store cache to filter previously processed emails...", "Phase 2/4")
        state = StateStore(settings.state_file)
        candidates = state.filter_for_processing(emails)
        emit_log(f"Identified {len(candidates)} new candidate email(s) for classification.", "Phase 2/4")

        emit_log(f"Invoking LLM classification chain (Batch size: 15)...", "Phase 2/4")
        classifications = classify_emails(candidates, settings)
        relevant = [c for c in classifications if c.is_job_related]
        emit_log(f"Classification completed: {len(relevant)} job-related email(s) flagged.", "Phase 2/4")

        # if not relevant: #i am running still since want it to regenrate all the data and dealine ex if today not recived but it will update upcoming and all
        #     emit_log("No job-related emails detected. Ending run.", "Done")
        #     pipeline_state["is_running"] = False
        #     pipeline_state["message"] = "No job-related emails found."
        #     pipeline_state["duration_str"] = "0 seconds"
        #     return

        emit_log(f"Extracting structured job events via LLM from {len(relevant)} email(s)...", "Phase 3/4")
        events = extract_job_events_from_emails(emails, relevant, settings)
        emit_log(f"Extracted {len(events)} discrete job events.", "Phase 3/4")

        cached = state.load_events_for_current_window(events, start_date, end_date)
        all_events = state.merge_events(cached, events)
        emit_log(f"Merged with 7-day window cache. Total events: {len(all_events)}.", "Phase 3/4")

        emit_log("Loading commitments from future_events.json...", "Phase 4/4")
        future_store = FutureEventStore(settings.future_events_file)
        future_events = future_store.load()

        emit_log("Running daily responsibility & opportunity analysis chain...", "Phase 4/4")
        daily = analyze_today(all_events, today, future_events, settings)

        emit_log("Persisting updated events to state.json and future_events.json...", "Phase 4/4")
        state.save(emails, all_events)
        future_store.save(daily.upcoming)

        end_time = time.perf_counter()
        elapsed = end_time - start_time
        hours, remainder = divmod(int(elapsed), 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if hours: parts.append(f"{hours} hour" + ("s" if hours != 1 else ""))
        if minutes: parts.append(f"{minutes} minute" + ("s" if minutes != 1 else ""))
        if seconds or not parts: parts.append(f"{seconds} second" + ("s" if seconds != 1 else ""))
        duration_str = ", ".join(parts)

        run_timestamp = datetime.now(settings.tz).strftime("%d %b %Y, %I:%M %p")

        emit_log("Serializing JSON and writing payload...", "Phase 4/4")
        
        summary_dict = daily.model_dump(mode="json")
        summary_dict["last_run"] = run_timestamp
        summary_dict["last_run_duration"] = duration_str

        settings.output_file_json.parent.mkdir(parents=True, exist_ok=True)
        with open(settings.output_file_json, "w", encoding="utf-8") as f:
            json.dump(summary_dict, f, indent=2)

        emit_log(f"Writing static HTML fallback to {settings.output_file_html.name}...", "Phase 4/4")
        generate_html(daily, today, settings.output_file_html)

        emit_log(f"Run completed successfully in {duration_str}.", "Done")

        pipeline_state["is_running"] = False
        pipeline_state["message"] = "Job completed successfully."
        pipeline_state["duration_str"] = duration_str
        pipeline_state["last_run"] = run_timestamp

    except Exception as e:
        emit_log(f"ERROR: {str(e)}", "Failed")
        pipeline_state["is_running"] = False
        pipeline_state["message"] = f"Pipeline execution failed: {str(e)}"
        pipeline_state["duration_str"] = "Failed"


# ==========================================
# REPLY GENERATOR
# ==========================================

class ReplyRequest(BaseModel):
    message_id: str
    thread_id: str
    generate_again: bool = False
    force: bool = False


class ReplyContentRequest(BaseModel):
    message_id: str
    thread_id: str
    reply: str


def get_reply_state_path(settings) -> Path:
    return settings.state_file.parent / "reply_state.json"


def load_reply_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"messages": {}}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {"messages": {}}
    except (OSError, json.JSONDecodeError):
        return {"messages": {}}


def save_reply_state(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def generate_email_reply(message_id: str, thread_id: str, settings) -> str:
    from reply_generator import generate_reply
    from gmail_client import GmailClient
    from llm import get_llm

    gmail = GmailClient(settings)
    llm = get_llm()

    def call_llm(prompt: str) -> str:
        result = llm.invoke(prompt)
        return result.content if hasattr(result, "content") else str(result)

    return generate_reply(
        gmail=gmail,
        message_id=message_id,
        thread_id=thread_id,
        llm=call_llm,
    )


def get_reply_target(settings, message_id: str, thread_id: str) -> dict[str, str]:
    """Read the Gmail message headers needed to create an in-thread reply."""
    from gmail_client import GmailClient

    gmail = GmailClient(settings)
    raw = gmail.service.users().messages().get(
        userId="me",
        id=message_id,
        format="full",
    ).execute()

    headers = {
        h["name"].lower(): h["value"]
        for h in raw.get("payload", {}).get("headers", [])
    }

    sender = headers.get("reply-to") or headers.get("from")
    subject = headers.get("subject", "")
    message_thread_id = raw.get("threadId") or thread_id

    if not sender:
        raise ValueError("Could not determine the recipient from the Gmail message.")

    return {
        "to": sender,
        "subject": subject,
        "thread_id": message_thread_id,
        "message_id": message_id,
        "references": headers.get("references", ""),
    }


def build_reply_raw(target: dict[str, str], reply: str) -> str:
    subject = target["subject"]
    if subject and not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    message = EmailMessage()
    message["To"] = target["to"]
    message["Subject"] = subject
    message["In-Reply-To"] = target["message_id"]
    references = target.get("references", "").strip()
    message["References"] = f"{references} {target['message_id']}".strip()
    message.set_content(reply.strip())

    return base64.urlsafe_b64encode(message.as_bytes()).decode()


def create_reply_draft(message_id: str, thread_id: str, reply: str, settings) -> dict[str, Any]:
    from gmail_client import GmailClient

    if not reply.strip():
        raise ValueError("Reply cannot be empty.")

    gmail = GmailClient(settings)
    target = get_reply_target(settings, message_id, thread_id)
    raw = build_reply_raw(target, reply)

    draft = gmail.service.users().drafts().create(
        userId="me",
        body={
            "message": {
                "raw": raw,
                "threadId": target["thread_id"],
            }
        },
    ).execute()

    return {
        "draft_id": draft.get("id"),
        "thread_id": target["thread_id"],
    }


def send_reply(message_id: str, thread_id: str, reply: str, settings) -> dict[str, Any]:
    from gmail_client import GmailClient

    if not reply.strip():
        raise ValueError("Reply cannot be empty.")

    gmail = GmailClient(settings)
    target = get_reply_target(settings, message_id, thread_id)
    raw = build_reply_raw(target, reply)

    sent = gmail.service.users().messages().send(
        userId="me",
        body={
            "raw": raw,
            "threadId": target["thread_id"],
        },
    ).execute()

    return {
        "message_id": sent.get("id"),
        "thread_id": sent.get("threadId") or target["thread_id"],
    }


# ==========================================
# API ENDPOINTS
# ==========================================

@app.get("/", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "AI Power Assistant API"}


@app.get("/api/summary", tags=["Dashboard"])
def get_summary():
    settings = get_settings()
    return load_json_file(settings.output_file_json)


@app.get("/api/future-events", tags=["Dashboard"])
def get_future_events():
    settings = get_settings()
    return load_json_file(settings.future_events_file)


@app.get("/api/reply-status/{message_id}", tags=["Reply"])
def get_reply_status(message_id: str):
    settings = get_settings()
    state = load_json_file(settings.state_file)
    event = state.get("events", {}).get(message_id)

    if event is None:
        return {
            "status": "event_not_found",
            "message_id": message_id,
            "need_to_reply": False,
        }

    need_to_reply = bool(event.get("need_to_reply", False))

    return {
        "status": "reply_needed" if need_to_reply else "reply_not_needed",
        "message_id": message_id,
        "thread_id": event.get("thread_id"),
        "need_to_reply": need_to_reply,
    }


@app.post("/api/generate-reply", tags=["Reply"])
def generate_reply_api(request: ReplyRequest):
    """
    Generate a reply for one Gmail message.

    The frontend supplies only message_id and thread_id.
    generate_again=True forces a fresh LLM generation.
    """
    settings = get_settings()
    reply_path = get_reply_state_path(settings)
    state = load_reply_state(reply_path)
    messages = state.setdefault("messages", {})

    existing = messages.get(request.message_id)

    if existing and existing.get("reply_generated") and not (request.generate_again or request.force):
        return {
            "status": "success",
            "message_id": request.message_id,
            "thread_id": request.thread_id,
            "reply": existing.get("reply", ""),
            "generation_count": existing.get("generation_count", 1),
            "cached": True,
        }

    try:
        reply = generate_email_reply(
            request.message_id,
            request.thread_id,
            settings,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate reply: {type(e).__name__}: {e}",
        )

    generation_count = (
        int(existing.get("generation_count", 0))
        + 1
        if existing
        else 1
    )

    messages[request.message_id] = {
        "thread_id": request.thread_id,
        "reply_generated": True,
        "reply_sent": existing.get("reply_sent", False) if existing else False,
        "generation_count": generation_count,
        "reply": reply,
        "generated_at": datetime.now(settings.tz).isoformat(),
    }

    save_reply_state(reply_path, state)

    return {
        "status": "success",
        "message_id": request.message_id,
        "thread_id": request.thread_id,
        "reply": reply,
        "generation_count": generation_count,
        "cached": False,
    }


@app.post("/api/create-reply-draft", tags=["Reply"])
def create_reply_draft_api(request: ReplyContentRequest):
    settings = get_settings()
    try:
        result = create_reply_draft(
            request.message_id,
            request.thread_id,
            request.reply,
            settings,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Gmail draft: {type(e).__name__}: {e}",
        )

    return {"status": "success", **result}


@app.post("/api/send-reply", tags=["Reply"])
def send_reply_api(request: ReplyContentRequest):
    settings = get_settings()
    reply_path = get_reply_state_path(settings)
    state = load_reply_state(reply_path)
    messages = state.setdefault("messages", {})

    try:
        result = send_reply(
            request.message_id,
            request.thread_id,
            request.reply,
            settings,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send Gmail reply: {type(e).__name__}: {e}",
        )

    existing = messages.get(request.message_id, {})
    messages[request.message_id] = {
        **existing,
        "thread_id": request.thread_id,
        "reply_generated": True,
        "reply_sent": True,
        "reply": request.reply,
        "sent_at": datetime.now(settings.tz).isoformat(),
    }
    save_reply_state(reply_path, state)

    return {"status": "success", **result}


@app.get("/api/pipeline-status", tags=["Pipeline"])
def get_pipeline_status():
    """Returns the status of background task execution including live logs."""
    return pipeline_state


@app.post("/api/run-pipeline", tags=["Pipeline"])
def trigger_pipeline(background_tasks: BackgroundTasks):
    global pipeline_state
    if pipeline_state["is_running"]:
        return {
            "status": "warning",
            "message": "Pipeline is already running in the background.",
        }

    background_tasks.add_task(execute_pipeline)
    return {
        "status": "success",
        "message": "AI email extraction pipeline has been started.",
    }



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8080, reload=True)