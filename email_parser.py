from __future__ import annotations

import re
from urllib.parse import urlparse

from models import EmailMessage


URL_RE = re.compile(r"https?://[^\s<>\"]+")


def clean_email(email: EmailMessage) -> EmailMessage:
    body = re.sub(r"\r\n?", "\n", email.body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    body = re.sub(r"[ \t]{2,}", " ", body)
    return email.model_copy(update={"body": body.strip()})


def extract_urls(text: str) -> list[str]:
    urls = []
    for url in URL_RE.findall(text):
        url = url.rstrip(").,;")
        try:
            if urlparse(url).scheme in {"http", "https"}:
                urls.append(url)
        except ValueError:
            pass
    return list(dict.fromkeys(urls))


def compact_for_llm(email: EmailMessage) -> str:
    email = clean_email(email)
    return (
        f"MESSAGE_ID: {email.message_id}\n"
        f"THREAD_ID: {email.thread_id}\n"
        f"RECEIVED_AT: {email.received_at.isoformat()}\n"
        f"FROM: {email.sender_name or ''} <{email.sender_email or ''}>\n"
        f"SUBJECT: {email.subject}\n"
        f"BODY:\n{email.body}\n"
    )
