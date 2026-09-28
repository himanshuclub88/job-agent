from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    gmail_credentials_file: Path
    gmail_token_file: Path
    output_file: Path
    output_file_html: Path
    state_file: Path
    future_events_file: Path
    timezone: str

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


settings = Settings(
    llm_api_key=required("LLM_API_KEY"),
    llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
    llm_model=required("LLM_MODEL"),
    gmail_credentials_file=Path(os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")),
    gmail_token_file=Path(os.getenv("GMAIL_TOKEN_FILE", "token.json")),
    output_file=Path(os.getenv("OUTPUT_FILE", "output/summary.md")),
    output_file_html=Path(os.getenv("OUTPUT_FILE_HTML", "output/summary.html")),
    state_file=Path(os.getenv("STATE_FILE", "state.json")),
    future_events_file = Path("FUTURE_STATE_FILE","future_events.json"),
    timezone=os.getenv("TIMEZONE", "Asia/Kolkata"),
)
