from __future__ import annotations

import base64
import re
from datetime import date, datetime, time, timedelta
from email.utils import parseaddr
from pathlib import Path
import time as tme
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
from email_parser import clean_email
from models import EmailMessage

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


class GmailClient:
    def __init__(self, settings):
        self.settings = settings
        self.service = self._authenticate()

    def _authenticate(self):
        token = self.settings.gmail_token_file
        creds = Credentials.from_authorized_user_file(str(token), SCOPES) if token.exists() else None

        # Existing tokens may still have the old readonly scope.
        # Force OAuth again so draft/send permissions are actually granted.
        required_scope = SCOPES[0]
        if creds and creds.scopes and required_scope not in creds.scopes:
            creds = None

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        if not creds or not creds.valid:
            if not self.settings.gmail_credentials_file.exists():
                raise FileNotFoundError(
                    f"Gmail OAuth credentials not found: {self.settings.gmail_credentials_file}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.settings.gmail_credentials_file), SCOPES
            )
            creds = flow.run_local_server(port=0)
            token.write_text(creds.to_json(), encoding="utf-8")

        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    def today(self) -> date:
        return datetime.now(self.settings.tz).date()

    @staticmethod
    def context_dates(today: date) -> tuple[date, date]:
        return today - timedelta(days=7), today

    def fetch_messages(self, start_date: date, end_date: date) -> list[EmailMessage]:
        # Gmail's after/before search is UTC-ish and can be surprising around midnight.
        # Fetch a slightly wider range, then apply the configured local timezone exactly.
        query = f"after:{start_date - timedelta(days=1):%Y/%m/%d} before:{end_date + timedelta(days=1):%Y/%m/%d}"
        ids: list[dict] = []
        token = None

        while True:
            response = self.service.users().messages().list(
                userId="me",
                q=query,
                maxResults=500,
                pageToken=token,
            ).execute()
            ids.extend(response.get("messages", []))
            token = response.get("nextPageToken")
            if not token:
                break

        messages = []
        for item in ids:
            for attempt in range(3):
                try:
                    raw = self.service.users().messages().get(
                        userId="me",
                        id=item["id"],
                        format="full",
                    ).execute()

                    parsed = self._parse_message(raw)

                    local_date = (
                        parsed.received_at
                        .astimezone(self.settings.tz)
                        .date()
                    )

                    if start_date <= local_date <= end_date:
                        messages.append(parsed)

                    break

                except Exception as e:
                    if attempt == 2:
                        print(
                            f"Failed to fetch Gmail message "
                            f"{item['id']}: {type(e).__name__}: {e}"
                        )
                        continue

                    wait = 2 ** attempt
                    print(
                        f"Gmail request failed for {item['id']} "
                        f"(attempt {attempt + 1}/3). "
                        f"Retrying in {wait}s..."
                    )
                    tme.sleep(wait)

        messages.sort(key=lambda x: x.received_at)
        return messages
    

    def _parse_message(self, raw: dict) -> EmailMessage:
        headers = {
            h["name"].lower(): h["value"]
            for h in raw.get("payload", {}).get("headers", [])
        }

        sender_name, sender_email = parseaddr(headers.get("from", ""))
        body = self._extract_body(raw.get("payload", {}))
        received_ms = int(raw.get("internalDate", "0"))
        received_at = datetime.fromtimestamp(received_ms / 1000, tz=self.settings.tz)

        return clean_email(EmailMessage(
            message_id=raw["id"],
            thread_id=raw.get("threadId", raw["id"]),
            received_at=received_at,
            sender_name=sender_name or None,
            sender_email=sender_email or None,
            to=[x.strip() for x in headers.get("to", "").split(",") if x.strip()],
            subject=headers.get("subject", ""),
            body=body[:30000],
            snippet=raw.get("snippet", ""),
        ))

    def _extract_body(self, payload: dict) -> str:
        parts = payload.get("parts", [])
        if parts:
            plain = next((p for p in parts if p.get("mimeType") == "text/plain"), None)
            if plain:
                return self._decode_part(plain)
            html = next((p for p in parts if p.get("mimeType") == "text/html"), None)
            if html:
                soup = BeautifulSoup(self._decode_part(html), "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a.get("href", "").strip()
                    label = a.get_text(" ", strip=True)
                    if href:
                        if label:
                            a.replace_with(f"{label}: {href}")
                        else:
                            a.replace_with(href)
                return soup.get_text("\n")

            for part in parts:
                nested = self._extract_body(part)
                if nested:
                    return nested

        if payload.get("mimeType") in {"text/plain", "text/html"} and payload.get("body", {}).get("data"):
            text = self._decode_part(payload)
            if payload.get("mimeType") == "text/html":
                soup = BeautifulSoup(text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a.get("href", "").strip()
                    label = a.get_text(" ", strip=True)
                    if href:
                        if label:
                            a.replace_with(f"{label}: {href}")
                        else:
                            a.replace_with(href)
                text = soup.get_text("\n")
            return text

        return ""

    @staticmethod
    def _decode_part(part: dict) -> str:
        data = part.get("body", {}).get("data", "")
        if not data:
            return ""
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode(
            "utf-8", errors="replace"
        )

if __name__ == "__main__":
    from config import settings

    MESSAGE_ID = "1a0e747b68851849"

    gmail = GmailClient(settings)

    try:
        raw = (
            gmail.service.users()
            .messages()
            .get(
                userId="me",
                id=MESSAGE_ID,
                format="full",
            )
            .execute()
        )

        # Same parsing/scrubbing used by fetch_messages()
        message = clean_email(gmail._parse_message(raw))

        with open("mail.txt", "w", encoding="utf-8") as f:
            f.write(message.body)

        print("Saved email body to mail.txt")

    except Exception as e:
        print(
            f"Failed to fetch Gmail message "
            f"{MESSAGE_ID}: {type(e).__name__}: {e}"
        )