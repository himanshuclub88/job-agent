from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
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