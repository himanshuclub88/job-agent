from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from llm import build_structured_chain
from models import DailySummary, JobEvent, UpcomingItem, EmailMessage


class ResponsibilityResult(BaseModel):
    summary: DailySummary


SYSTEM = """
You are a personal job-search responsibility assistant.

You receive job-related email events from the previous seven
calendar days.

The current date is supplied separately.

Do NOT summarize the seven days.

Determine only what is relevant to the user TODAY.

Return information in exactly these four sections:

RESPONSIBILITIES:
- Include ONLY emails that explicitly require the user to reply, respond,
  send something, confirm something, provide information, or take a direct
  action requested by the sender.
- Read the email BODY to determine whether an explicit action is requested.
- If the email only contains a job opening, Apply button, application URL,
  job description, job alert, or job recommendation, DO NOT put it in
  RESPONSIBILITIES. Put it in OPPORTUNITIES when it is a usable job opportunity,
  otherwise treat it as an UPDATE.
- If the user has already replied/completed the requested action, keep the
  responsibility only when the latest thread context shows that the same
  communication/action is still relevant. Do not create a new responsibility
  for the reply itself.
- Use the latest email/thread state when deciding what is currently relevant.
- Do not create duplicate responsibilities for the same requested action.

UPDATES:
- Use for meaningful changes, status updates, recruiter responses, or
  information that does not require the user to reply or take a direct action.

OPPORTUNITIES:
- Use for actual job opportunities with an Apply/application URL or clear
  application path.

UPCOMING
   - Include interviews, assessments, deadlines, meetings, or other
     future events that the user should know about.
   - Only include genuinely upcoming items.
   - Do not include completed or outdated events.

Priority:
1. Responsibilities requiring a reply/action today (if action already show lates one from thread).
2. Interviews, assessments, and deadlines today.
3. Upcoming events and deadlines.
4. Meaningful application-status updates.
5. New job opportunities.


Thread/application context matters.
Group related events into the current state.


Be aggressively concise.
Do not repeat the same fact in multiple sections.
Do not include generic career advice.
Do not invent facts.
A single email should normally appear in only one section.

IMPORTANT SECTION RULE:
- Responsibilities = "I need to reply/do something."
- Updates = "Something changed; no action is required."
- Opportunities = "There is a job I can apply for."
- Upcoming = "Something is scheduled or due in the future."

Do not move an item between these meanings merely because it is
job-related.
"""


def analyze_today(
    events: list[JobEvent],
    today: date,
    emails: list[EmailMessage],
    future_events: list[UpcomingItem] | None = None,
    settings=None,
) -> DailySummary:

    if not events:
        return DailySummary()

    chain = build_structured_chain(
        SYSTEM,
        ResponsibilityResult,
    )
    emap= { email.message_id:email.body  for email in emails }

    event_text = "\n\n".join(
        {**event.model_dump(), "body": emap.get(event.message_id, "")}.__str__()
        for event in events
    )

    future_text = "\n\n".join(
        event.model_dump_json()
        for event in future_events
    )

    user_input = f"""
CURRENT_DATE: {today.isoformat()}

CURRENT 7-DAY JOB EVENTS:
{event_text}

SAVED FUTURE EVENTS:
{future_text}

Use both the current job events and the saved future events
to determine the current job-search state relevant TODAY.

Important:
- Saved future events may have come from previous runs.
- If a newer event changes, cancels, completes, or reschedules
  a saved future event, use the newer event.
- Do not blindly duplicate saved future events.
- Keep only genuinely upcoming items in the upcoming section.
"""

    result: ResponsibilityResult = chain.invoke(
        {"input": user_input}
    )

    return result.summary