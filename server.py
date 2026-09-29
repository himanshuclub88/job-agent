import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from gmail_client import GmailClient
from classifier import classify_emails
from extractor import extract_job_events_from_emails
from responsibility import analyze_today
from html_generator import generate_html
from state import StateStore
from future_events import FutureEventStore

app = FastAPI(
    title="AI Power Assistant API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state to communicate with frontend polling
pipeline_state = {
    "is_running": False,
    "message": "Idle",
    "duration_str": None,
    "last_run": None
}

def load_json_file(file_path: Path):
    if not file_path.exists():
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Error parsing {file_path.name}")

def execute_pipeline():
    global pipeline_state
    pipeline_state["is_running"] = True
    pipeline_state["message"] = "Engine running..."
    pipeline_state["duration_str"] = None

    start_time = time.perf_counter()

    try:
        gmail = GmailClient(settings)
        today = gmail.today()
        start_date, end_date = gmail.context_dates(today)
        emails = gmail.fetch_messages(start_date, end_date)

        if not emails:
            print("No emails found.")
            return

        state = StateStore(settings.state_file)
        candidates = state.filter_for_processing(emails)
        classifications = classify_emails(candidates, settings)
        relevant = [c for c in classifications if c.is_job_related]

        if not relevant:
            print("No job-related emails found.")
            return

        events = extract_job_events_from_emails(emails, relevant, settings)
        cached = state.load_events_for_current_window(events, start_date, end_date)
        all_events = state.merge_events(cached, events)

        future_store = FutureEventStore(settings.future_events_file)
        future_events = future_store.load()

        daily = analyze_today(all_events, today, future_events, settings)

        state.save(emails, all_events)
        future_store.save(daily.upcoming)

        # Calculate execution duration
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        hours, remainder = divmod(int(elapsed), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if hours: parts.append(f"{hours} hour" + ("s" if hours != 1 else ""))
        if minutes: parts.append(f"{minutes} minute" + ("s" if minutes != 1 else ""))
        if seconds or not parts: parts.append(f"{seconds} second" + ("s" if seconds != 1 else ""))
        duration_str = ", ".join(parts)

        # Format run timestamp in user timezone
        run_timestamp = datetime.now(settings.tz).strftime("%d %b %Y, %I:%M %p")

        # Convert daily model to dict and inject run stats & received_at timestamps
        summary_dict = daily.model_dump()
        summary_dict["last_run"] = run_timestamp
        summary_dict["last_run_duration"] = duration_str

        # Build message lookup map to attach received_at to every item
        email_map = {e.message_id: e.received_at.isoformat() for e in emails if getattr(e, "received_at", None)}

        for category in ["responsibilities", "opportunities", "updates", "upcoming"]:
            for item in summary_dict.get(category, []):
                msg_id = item.get("message_id")
                if msg_id and msg_id in email_map:
                    item["received_at"] = email_map[msg_id]

        # Save to output file
        settings.output_file_json.parent.mkdir(parents=True, exist_ok=True)
        with open(settings.output_file_json, "w", encoding="utf-8") as f:
            json.dump(summary_dict, f, indent=2)

        generate_html(daily, today, settings.output_file_html)

        pipeline_state["is_running"] = False
        pipeline_state["message"] = "Completed successfully."
        pipeline_state["duration_str"] = duration_str
        pipeline_state["last_run"] = run_timestamp

    except Exception as e:
        print(f"Pipeline Error: {e}")
        pipeline_state["is_running"] = False
        pipeline_state["message"] = f"Failed: {str(e)}"

@app.post("/api/run-pipeline")
def run_pipeline(background_tasks: BackgroundTasks):
    global pipeline_state
    if pipeline_state["is_running"]:
        return {"status": "error", "message": "Pipeline already active."}
        
    background_tasks.add_task(execute_pipeline)
    return {"status": "success", "message": "Pipeline triggered."}

@app.get("/api/pipeline-status")
def get_pipeline_status():
    return pipeline_state

@app.get("/api/summary")
def get_full_summary():
    return load_json_file(settings.output_file_json)