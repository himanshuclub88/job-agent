from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from llm import LLM
from models import DailySummary, JobEvent


class ResponsibilityResult(BaseModel):
    summary: DailySummary


SYSTEM = """
You are a personal job-search responsibility assistant.

You receive job-related email events from the previous seven calendar days.
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

Resolve completed actions using later events. If an earlier assessment was requested
but a later email says it was completed, it must not remain a pending task.

Thread/application context matters. Group related events into the current state.
Do not report stale tasks when later evidence resolves them.

Be aggressively concise. Do not repeat the same fact in multiple sections.
Do not include generic career advice.
Do not invent facts.
Do not tell the user whether they should apply to an opportunity; only surface it.
Return JSON matching the schema.
"""


def analyze_today(events: list[JobEvent], today: date, settings) -> DailySummary:
    if not events:
        return DailySummary()

    llm = LLM(settings)
    event_text = "\n\n".join(e.model_dump_json() for e in events)

    user = f"""
CURRENT_DATE: {today.isoformat()}

EVENTS FROM CURRENT 7-DAY CONTEXT:
{event_text}

Determine the current job-search state relevant TODAY.
"""

    result = llm.structured(SYSTEM, user, ResponsibilityResult)
    return result.summary
