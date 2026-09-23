from __future__ import annotations

from pydantic import BaseModel, Field

from email_parser import compact_for_llm
from llm import build_structured_chain
from models import Classification, EmailMessage


class ClassificationResult(BaseModel):
    items: list[Classification] = Field(default_factory=list)


SYSTEM = """
You classify emails for a personal job-search assistant.

Job-related categories:
APPLICATION, RECRUITER, INTERVIEW, INTERVIEW_RESCHEDULE, ASSESSMENT,
APPLICATION_UPDATE, REJECTION, OFFER, BACKGROUND_CHECK, JOINING,
JOB_ALERT, JOB_RECOMMENDATION, REFERRAL, OTHER_JOB_RELATED.

A job alert is NOT an application.

An actual application confirmation/application status belongs to
APPLICATION or APPLICATION_UPDATE.

Only mark is_job_related=true when the email is materially related
to job search/recruiting.

Ignore newsletters, marketing, invoices, social notifications,
and unrelated mail.

Do not infer missing facts.
"""


def classify_emails(
    emails: list[EmailMessage],
    settings=None,
) -> list[Classification]:

    if not emails:
        return []

    chain = build_structured_chain(
        SYSTEM,
        ClassificationResult,
    )

    results: list[Classification] = []

    batch_size = 15

    for i in range(0, len(emails), batch_size):

        batch = emails[i:i + batch_size]

        user_input = (
            "Classify these emails. "
            "Return one item for every message.\n\n"
            + "\n--- EMAIL ---\n".join(
                compact_for_llm(email)
                for email in batch
            )
        )

        result: ClassificationResult = chain.invoke(
            {"input": user_input}
        )

        results.extend(result.items)

    return results