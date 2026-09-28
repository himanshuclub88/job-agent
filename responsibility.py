from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from llm import build_structured_chain
from models import DailySummary, JobEvent, UpcomingItem


class ResponsibilityResult(BaseModel):
    summary: DailySummary


SYSTEM = """
You are a personal job-search responsibility assistant.

You receive job-related email events from the previous seven
calendar days.

The current date is supplied separately.

Do NOT summarize the seven days.

Determine only what is relevant to the user TODAY.

Priorities:

1. Actions due today.
2. Interviews/events today.
3. Deadlines today.
4. Pending recruiter responses.
5. Upcoming events/deadlines worth knowing soon.
6. Meaningful recent application-status changes.
7. New job opportunities.

Resolve completed actions using later events.

If an earlier assessment was requested but a later email says
it was completed, it must not remain a pending task.

Thread/application context matters.
Group related events into the current state.

Do not report stale tasks when later evidence resolves them.

Be aggressively concise.

Do not repeat the same fact in multiple sections.

Do not include generic career advice.

Do not invent facts.

Do not tell the user whether they should apply to an opportunity;
only surface it.
"""


def analyze_today(
    events: list[JobEvent],
    today: date,
    future_events: list[UpcomingItem] | None = None,
    settings=None,
) -> DailySummary:

    if not events:
        return DailySummary()

    chain = build_structured_chain(
        SYSTEM,
        ResponsibilityResult,
    )

    event_text = "\n\n".join(
        event.model_dump_json()
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