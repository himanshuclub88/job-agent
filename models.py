from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Category = Literal[
    "APPLICATION",
    "RECRUITER",
    "INTERVIEW",
    "INTERVIEW_RESCHEDULE",
    "ASSESSMENT",
    "APPLICATION_UPDATE",
    "REJECTION",
    "OFFER",
    "BACKGROUND_CHECK",
    "JOINING",
    "JOB_ALERT",
    "JOB_RECOMMENDATION",
    "REFERRAL",
    "OTHER_JOB_RELATED",
]


class EmailMessage(BaseModel):
    message_id: str
    thread_id: str
    received_at: datetime
    sender_name: str | None = None
    sender_email: str | None = None
    to: list[str] = Field(default_factory=list)
    subject: str = ""
    body: str = ""
    snippet: str = ""


class Classification(BaseModel):
    message_id: str
    is_job_related: bool
    category: Category | None = None
    reason: str | None = None


class JobEvent(BaseModel):
    message_id: str
    thread_id: str
    received_at: datetime
    category: Category

    company: str | None = None
    job_title: str | None = None
    status: str | None = None

    application_url: str | None = None

    recruiter_name: str | None = None
    recruiter_email: str | None = None

    action_required: bool = False
    action: str | None = None
    action_deadline: str | None = None

    interview_date: str | None = None
    interview_time: str | None = None
    interview_timezone: str | None = None
    interview_url: str | None = None

    assessment_url: str | None = None
    assessment_deadline: str | None = None

    opportunity: bool = False
    opportunity_url: str | None = None
    location: str | None = None

    summary: str


class DailyResponsibility(BaseModel):
    company: str | None = None
    job_title: str | None = None
    text: str
    deadline: str | None = None
    link: str | None = None
    recruiter: str | None = None
    email_subject: str | None = None
    email_sender: str | None = None


class UpcomingItem(BaseModel):
    company: str | None = None
    job_title: str | None = None
    text: str
    date: str | None = None
    time: str | None = None
    link: str | None = None
    email_subject: str | None = None
    email_sender: str | None = None


class ImportantUpdate(BaseModel):
    text: str
    email_subject: str | None = None
    email_sender: str | None = None


class Opportunity(BaseModel):
    company: str | None = None
    job_title: str | None = None
    location: str | None = None
    url: str | None = None
    source: str | None = None
    email_subject: str | None = None
    email_sender: str | None = None


class DailySummary(BaseModel):
    responsibilities: list[DailyResponsibility] = Field(default_factory=list)
    upcoming: list[UpcomingItem] = Field(default_factory=list)
    updates: list[ImportantUpdate] = Field(default_factory=list)
    opportunities: list[Opportunity] = Field(default_factory=list)
    dont_miss: list[str] = Field(default_factory=list)
