from datetime import date, datetime
from typing import Any

from models import ConversationRecord, MessageRecord

VALID_ROLES = set({"user", "assistant", "system"})


class ValidationError(ValueError):
    pass


def _require_str(d: dict, key: str) -> str:
    val = d.get(key)
    if not isinstance(val, str) or not val:
        raise ValidationError(f"'{key}' must be a non-empty string, got {val}")
    return val


def _require_nonneg_int(d: dict, key: str) -> int:
    val = d.get(key)
    if not isinstance(val, int) or val < 0:
        raise ValidationError(f"'{key}' must be an integer >= 0, got {val}")
    return val


def _parse_timestamp(val: Any, field_name: str) -> datetime:
    if not isinstance(val, str):
        raise ValidationError(f"'{field_name}' must be an ISO 8601 string, got {val}")
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except ValueError:
        raise ValidationError(f"'{field_name}' is not a valid timestamp: {val}")


def validate_message(raw: Any, conversation_id: str) -> MessageRecord:
    if not isinstance(raw, dict):
        raise ValidationError(f"message must be a dict, got {type(raw).__name__}")
    role = _require_str(raw, "role")
    if role not in VALID_ROLES:
        raise ValidationError(f"role {role} is not one of {sorted(VALID_ROLES)}")
    return MessageRecord(
        message_id=_require_str(raw, "message_id"),
        conversation_id=conversation_id,
        role=role,
        content=_require_str(raw, "content"),
        timestamp=_parse_timestamp(raw.get("timestamp"), "timestamp"),
        tokens_in=_require_nonneg_int(raw, "tokens_in"),
        tokens_out=_require_nonneg_int(raw, "tokens_out"),
        latency_ms=_require_nonneg_int(raw, "latency_ms"),
    )


def validate_conversation(raw: dict, load_date: date) -> ConversationRecord:
    conv_id = _require_str(raw, "conversation_id")

    messages_raw = raw.get("messages")
    if not isinstance(messages_raw, list) or len(messages_raw) == 0:
        raise ValidationError("'messages' must be a non-empty list")

    messages: list[MessageRecord] = []
    for i, msg_raw in enumerate(messages_raw):
        msg = validate_message(msg_raw, conv_id)
        messages.append(msg)

    return ConversationRecord(
        conversation_id=conv_id,
        load_date=load_date,
        user_id=_require_str(raw, "user_id"),
        started_at=_parse_timestamp(raw.get("started_at"), "started_at"),
        model_version=_require_str(raw, "model_version"),
        messages=messages,
    )
