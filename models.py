from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class MessageRecord:
    message_id: str
    conversation_id: str
    role: str
    content: str
    timestamp: datetime
    tokens_in: int
    tokens_out: int
    latency_ms: int


@dataclass
class ConversationRecord:
    conversation_id: str
    load_date: date
    user_id: str
    started_at: datetime
    model_version: str
    messages: list[MessageRecord]


@dataclass
class FailedRecord:
    raw_line: str
    conversation_id: str | None
    reason: str   # "json_parse_error" | "validation_error"
    detail: str


@dataclass
class LoadStats:
    load_date: date
    lines_seen: int = 0
    conversations_loaded: int = 0
    messages_loaded: int = 0
    parse_errors: int = 0
    validation_errors: int = 0
