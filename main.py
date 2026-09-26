from __future__ import annotations
import time
import argparse
from pathlib import Path
from md import md_to_html
from config import settings
from gmail_client import GmailClient
from classifier import classify_emails
from extractor import extract_job_events_from_emails
from responsibility import analyze_today
from markdown_generator import render_markdown
from state import StateStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal Gmail job-search daily responsibility agent")
    parser.add_argument("--print", action="store_true", dest="print_output",
                        help="Print the generated Markdown to stdout")
    args = parser.parse_args()

    print("Connecting to Gmail...")
    gmail = GmailClient(settings)

    today = gmail.today()
    start_date, end_date = gmail.context_dates(today)

    print(f"Current date: {today:%d %B %Y}")
    print(f"Reading Gmail context: {start_date:%d %B} → {end_date:%d %B %Y}")

    emails = gmail.fetch_messages(start_date, end_date)
    print(f"Emails found: {len(emails)}")

    state = StateStore(settings.state_file)
    candidates = state.filter_for_processing(emails)

    classifications = classify_emails(candidates, settings)
    relevant = [c for c in classifications if c.is_job_related]
    print(f"Job-related emails: {len(relevant)}")

    events = extract_job_events_from_emails(emails, relevant, settings)

    # Keep the final decision based on the full current 7-day window.
    # Cached events are only an optimization; they never replace current context.
    cached = state.load_events_for_current_window(events, start_date, end_date)
    all_events = state.merge_events(cached, events)

    print("Analyzing current responsibilities...")
    daily = analyze_today(all_events, today, settings)

    markdown = render_markdown(daily, today)
    settings.output_file.parent.mkdir(parents=True, exist_ok=True)
    settings.output_file.write_text(markdown, encoding="utf-8")

    state.save(emails, all_events)

    print(f"Generating {settings.output_file}...")
    print("Done.")

    print("CONVERTING TO HTML")
    print(f"Generating {settings.output_file_html}...")
    md_to_html(settings.output_file,settings.output_file_html)
    print("Done.")

    if args.print_output:
        print("\n" + markdown)



if __name__ == "__main__":
    start_time = time.perf_counter()

    print("Job started...")

    main()

    end_time = time.perf_counter()
    elapsed = end_time - start_time

    hours, remainder = divmod(int(elapsed), 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []

    if hours:
        parts.append(f"{hours} hour" + ("s" if hours != 1 else ""))

    if minutes:
        parts.append(f"{minutes} minute" + ("s" if minutes != 1 else ""))

    if seconds or not parts:
        parts.append(f"{seconds} second" + ("s" if seconds != 1 else ""))

    duration = ", ".join(parts)

    print(f"Job completed in {duration}.")