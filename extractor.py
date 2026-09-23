from __future__ import annotations

from pydantic import BaseModel, Field

from email_parser import compact_for_llm
from llm import LLM
from models import Classification, EmailMessage, JobEvent


class ExtractionResult(BaseModel):
    events: list[JobEvent] = Field(default_factory=list)


SYSTEM = """
Extract factual job-search events from the supplied emails.

Return JSON matching the requested schema.
Do not invent facts. Use null for unavailable fields.
Preserve URLs exactly when possible.
Dates/times may be represented in ISO-like text if the email provides them.
Use the email's message_id, thread_id, and received_at exactly.
Classify each email with one of the allowed categories.

Important:
- Job alerts/recommendations are opportunities, not applications.
- An action_required flag means the user actually needs to do something.
- If the email merely confirms an application, action_required should normally be false.
- If an email says an earlier task was completed, capture the completed status in summary/status.
"""


def extract_job_events(classifications: list[Classification], settings) -> list[JobEvent]:
    if not classifications:
        return []

    # Re-fetching the body is unnecessary here if the caller passes the relevant messages.
    # This function is fed via the enriched helper below.
    raise RuntimeError("extract_job_events requires extract_job_events_from_emails")


def extract_job_events_from_emails(
    emails: list[EmailMessage], classifications: list[Classification], settings
) -> list[JobEvent]:
    by_id = {e.message_id: e for e in emails}
    relevant = [
        (c, by_id[c.message_id])
        for c in classifications
        if c.is_job_related and c.message_id in by_id
    ]

    if not relevant:
        return []

    llm = LLM(settings)
    result: list[JobEvent] = []

    batch_size = 10
    for i in range(0, len(relevant), batch_size):
        batch = relevant[i:i + batch_size]
        text = []
        for c, e in batch:
            text.append(
                f"CLASSIFICATION: {c.category}\n"
                f"REASON: {c.reason or ''}\n"
                f"{compact_for_llm(e)}"
            )

        user = "Extract one JobEvent for each email below.\n\n" + "\n--- EMAIL ---\n".join(text)
        parsed = llm.structured(SYSTEM, user, ExtractionResult)
        result.extend(parsed.events)

    return result
