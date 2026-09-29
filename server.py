import json
import time
from datetime import date
from pathlib import Path
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
    title="Job Search AI Pipeline API",
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
    "duration_str": None
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
    pipeline_state["message"] = "Starting pipeline..."
    pipeline_state["duration_str"] = None
    
    print("Job started (via API)...")
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
            print("No Job-related emails found.")
            return

        events = extract_job_events_from_emails(emails, relevant, settings)
        cached = state.load_events_for_current_window(events, start_date, end_date)
        all_events = state.merge_events(cached, events)
        future_store = FutureEventStore(settings.future_events_file)
        future_events = future_store.load()

        daily = analyze_today(all_events, today, future_events, settings)

        state.save(emails, all_events)
        future_store.save(daily.upcoming)

        settings.output_file_json.parent.mkdir(parents=True, exist_ok=True)
        settings.output_file_json.write_text(daily.model_dump_json(indent=2), encoding="utf-8")
        generate_html(daily, today, settings.output_file_html)

    except Exception as e:
        print(f"Pipeline Error: {e}")
    finally:
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        hours, remainder = divmod(int(elapsed), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if hours: parts.append(f"{hours} hour" + ("s" if hours != 1 else ""))
        if minutes: parts.append(f"{minutes} minute" + ("s" if minutes != 1 else ""))
        if seconds or not parts: parts.append(f"{seconds} second" + ("s" if seconds != 1 else ""))
        
        duration = ", ".join(parts)
        print(f"Job completed in {duration}.")
        
        # Signal frontend that the job is done and provide the exact string
        pipeline_state["is_running"] = False
        pipeline_state["message"] = f"Job completed successfully."
        pipeline_state["duration_str"] = duration

@app.post("/api/run-pipeline")
def run_pipeline(background_tasks: BackgroundTasks):
    global pipeline_state
    if pipeline_state["is_running"]:
        return {"status": "error", "message": "Pipeline is already running."}
        
    background_tasks.add_task(execute_pipeline)
    return {"status": "success", "message": "Pipeline triggered."}

@app.get("/api/pipeline-status")
def get_pipeline_status():
    return pipeline_state

@app.get("/api/summary")
def get_full_summary():
    return load_json_file(settings.output_file_json)

@app.get("/api/future-events")
def get_future_events():
    return load_json_file(settings.future_events_file)