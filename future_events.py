import json
from pathlib import Path

from models import UpcomingItem


class FutureEventStore:
    """
    Stores upcoming job-search events so they survive
    beyond the current 7-day Gmail window.
    """

    def __init__(self, path: Path):
        self.path = path
        self.data: list[dict] = []

        if self.path.exists():
            try:
                self.data = json.loads(
                    self.path.read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError):
                self.data = []

    def load(self) -> list[UpcomingItem]:
        result = []

        for raw in self.data:
            try:
                result.append(UpcomingItem.model_validate(raw))
            except Exception:
                continue

        return result

    def save(self, upcoming: list[UpcomingItem]) -> None:
        print("PATH OF FUTRE EVENTS STORE",self.path)
        self.data = [
            item.model_dump(mode="json")
            for item in upcoming
        ]

        self.path.write_text(
            json.dumps(self.data, indent=2),
            encoding="utf-8",
        )