from __future__ import annotations

from datetime import datetime
from typing import Callable

from gmail_client import GmailClient


def read_thread(gmail: GmailClient, thread_id: str) -> list[dict]:
    """Read all messages from a Gmail thread."""
    response = gmail.service.users().threads().get(
        userId="me",
        id=thread_id,
        format="full",
    ).execute()

    messages = []

    for raw in response.get("messages", []):
        message = gmail._parse_message(raw)
        messages.append(
            {
                "message_id": message.message_id,
                "thread_id": message.thread_id,
                "received_at": message.received_at,
                "sender_name": message.sender_name,
                "sender_email": message.sender_email,
                "to": message.to,
                "subject": message.subject,
                "body": message.body,
                "snippet": message.snippet,
            }
        )

    return messages


def generate_reply(
    gmail: GmailClient,
    message_id: str,
    thread_id: str,
    llm: Callable[[str], str],
) -> str:
    """
    Generate a reply for one email.

    The frontend only needs to provide message_id and thread_id.
    The LLM implementation is passed separately so this generator
    stays independent from the rest of the application.
    """
    thread = read_thread(gmail, thread_id)

    current_message = next(
        (message for message in thread if message["message_id"] == message_id),
        None,
    )

    if current_message is None:
        raise ValueError(f"Message not found in thread: {message_id}")

    today = datetime.now(gmail.settings.tz).strftime("%Y-%m-%d")

    conversation = "\n\n".join(
        f"From: {m['sender_name'] or m['sender_email'] or 'Unknown'}\n"
        f"Date: {m['received_at']}\n"
        f"Subject: {m['subject']}\n"
        f"Body:\n{m['body']}"
        for m in thread
    )

    prompt = f"""Write a natural, professional email reply.

Current date: {today}

Reply to the latest relevant message.
Do not invent facts.
Keep the reply concise.
Return only the email body.

resume link if asked for resume : https://himanshuclub88.github.io/ResumeLatex/
3
IF ASKED BY RECUITER 
CTC : 5 LPA
EXPECTED CTC : 15 LPA
Notice Period : 90 days

Conversation:
{conversation}
"""

    return llm(prompt).strip()
