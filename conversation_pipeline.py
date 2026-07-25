"""
Conversation Ingestion Pipeline

Daily pipeline for AI assistant conversation logs:
  1. Read input JSONL file
  2. Validate each record
  3. Write to Postgres atomically

Usage:
    stats = load_day(path, load_date, conn)
"""

from datetime import date
from typing import Iterator

from models import ConversationRecord, FailedRecord, LoadStats
from reader import parse_line, read_lines
from validator import ValidationError, validate_conversation
from writer import write_batch


def process_file(
    lines: Iterator[str],
    load_date: date,
) -> tuple[list[ConversationRecord], list[FailedRecord], LoadStats]:
    stats = LoadStats(load_date=load_date)
    valid: list[ConversationRecord] = []
    failed: list[FailedRecord] = []

    for raw_line in lines:
        stats.lines_seen += 1

        raw, err = parse_line(raw_line)
        if err:
            stats.parse_errors += 1
            failed.append(FailedRecord(raw_line, None, "json_parse_error", err))
            continue

        conv_id = raw.get("conversation_id")

        try:
            record = validate_conversation(raw, load_date)
        except ValidationError as e:
            stats.validation_errors += 1
            failed.append(FailedRecord(raw_line, conv_id, "validation_error", str(e)))
            continue

        valid.append(record)

    return valid, failed, stats


def load_day(path: str, load_date: date, conn) -> LoadStats:
    valid, failed, stats = process_file(read_lines(path), load_date)

    with conn:  # transaction; commit on exit, rollback on exception
        write_batch(conn, load_date, valid, failed)

    stats.conversations_loaded = len(valid)
    stats.messages_loaded = sum(len(r.messages) for r in valid)
    return stats
