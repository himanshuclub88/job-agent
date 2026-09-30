from __future__ import annotations

from pydantic import BaseModel, Field

from email_parser import compact_for_llm
from llm import build_structured_chain
from models import Classification, EmailMessage, JobEvent


class ExtractionResult(BaseModel):
    events: list[JobEvent] = Field(default_factory=list)


SYSTEM = """
Extract factual job-search events from the supplied emails.

Do not invent facts.
Use null for unavailable fields.

Preserve URLs exactly when possible.

Dates/times may be represented in ISO-like text
if the email provides them.

Use the email's message_id, thread_id, and received_at exactly.

Classify each email with one of the allowed categories.

need_to_reply: true only if a direct response is expected; otherwise false.

recruiter_email: Use the alternate email from the mail body, if provided; otherwise, leave it null.

Important:

- Job alerts/recommendations are opportunities, not applications.
- An action_required flag means the user actually needs to do something.
- If the email merely confirms an application,
  action_required should normally be false.
- If an email says an earlier task was completed,
  capture the completed status in summary/status [add in summary need to apply and if any replyed need to reply].
"""


def extract_job_events_from_emails(
    emails: list[EmailMessage],
    classifications: list[Classification],
    settings=None,
) -> list[JobEvent]:

    by_id = {
        email.message_id: email
        for email in emails
    }

    relevant = [
        (classification, by_id[classification.message_id])
        for classification in classifications
        if (
            classification.is_job_related
            and classification.message_id in by_id
        )
    ]

    if not relevant:
        return []

    chain = build_structured_chain(
        SYSTEM,
        ExtractionResult,
    )

    result: list[JobEvent] = []

    batch_size = 10

    for i in range(0, len(relevant), batch_size):

        batch = relevant[i:i + batch_size]

        text = []

        for classification, email in batch:

            text.append(
                f"CLASSIFICATION: {classification.category}\n"
                f"REASON: {classification.reason or ''}\n"
                f"{compact_for_llm(email)}"
            )

        user_input = (
            "Extract one JobEvent for each email below.\n\n"
            + "\n--- EMAIL ---\n".join(text)
        )

        parsed: ExtractionResult = chain.invoke(
            {"input": user_input}
        )

        result.extend(parsed.events)

    return result