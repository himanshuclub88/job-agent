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

1. RESPONSIBILITIES
   - Include ONLY emails where the user needs to reply, respond,
     provide information, contact someone, or take a direct action
     on the email.
   - A responsibility must represent an actual pending action for the user.
   - Do NOT include general job updates, application status updates,
     job opportunities, interviews, or informational emails here.
   - Prefer events where need_to_reply = true.
   - If the email does not require a response or action from the user,
     do not put it in responsibilities.

2. UPDATES
   - Include meaningful changes to existing applications or job processes.
   - Examples: application submitted/received, application status changed,
     recruiter decision, rejection, offer, assessment result, interview
     result, or other important application progress.
   - These are informational updates and do NOT require the user to reply.
   - Do not put these in responsibilities unless a separate action is required.

3. OPPORTUNITIES
   - Include ONLY new job opportunities where the user may apply.
   - These should represent actual job openings, recruiter job leads,
     referrals, or job recommendations that contain a usable application
     or job URL when available.
   - Do not put normal application updates or recruiter conversations here.
   - Do not tell the user whether they should apply; only surface the opportunity.

4. UPCOMING
   - Include interviews, assessments, deadlines, meetings, or other
     future events that the user should know about.
   - Only include genuinely upcoming items.
   - Do not include completed or outdated events.

Priority:
1. Responsibilities requiring a reply/action today.
2. Interviews, assessments, and deadlines today.
3. Upcoming events and deadlines.
4. Meaningful application-status updates.
5. New job opportunities.

Resolve completed actions using later events.

If an earlier assessment was requested but a later email says
it was completed, it must not remain a pending responsibility.

Thread/application context matters.
Group related events into the current state.

Do not report stale tasks when later evidence resolves them.

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