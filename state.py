from __future__ import annotations

import json
from datetime import datetime, date
from pathlib import Path

from models import EmailMessage, JobEvent


class StateStore:
    """
    Small local cache. It is an optimization only.
    The current run still fetches the complete seven-day Gmail window.
    """

    def __init__(self, path: Path):
        self.path = path
        self.data = {"messages": {}, "events": {}}
        if path.exists():
            try:
                self.data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass

    def filter_for_processing(self, emails: list[EmailMessage]) -> list[EmailMessage]:
        return [
            e for e in emails
            if e.message_id not in self.data.get("messages", {})
        ]

    def load_events_for_current_window(
        self, current_events: list[JobEvent], start_date: date, end_date: date
    ) -> list[JobEvent]:
        result = []
        for raw in self.data.get("events", {}).values():
            try:
                event = JobEvent.model_validate(raw)
                d = event.received_at.date()
                if start_date <= d <= end_date:
                    result.append(event)
            except Exception:
                continue
        return result

    @staticmethod
    def merge_events(old: list[JobEvent], new: list[JobEvent]) -> list[JobEvent]:
        by_id = {e.message_id: e for e in old}
        by_id.update({e.message_id: e for e in new})
        return sorted(by_id.values(), key=lambda x: x.received_at)

    def save(self, emails: list[EmailMessage], events: list[JobEvent]) -> None:
        for e in emails:
            self.data.setdefault("messages", {})[e.message_id] = {
                "received_at": e.received_at.isoformat()
            }

        for e in events:
            self.data.setdefault("events", {})[e.message_id] = e.model_dump(mode="json")

        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
