from datetime import date

from models import ConversationRecord, FailedRecord

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id  TEXT        NOT NULL PRIMARY KEY,
    load_date        DATE        NOT NULL,
    user_id          TEXT        NOT NULL,
    started_at       TIMESTAMPTZ NOT NULL,
    model_version    TEXT        NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_conversations_load_date ON conversations (load_date);

CREATE TABLE IF NOT EXISTS messages (
    message_id      TEXT        NOT NULL PRIMARY KEY,
    conversation_id TEXT        NOT NULL
        REFERENCES conversations (conversation_id) ON DELETE CASCADE,
    role            TEXT        NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT        NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL,
    tokens_in       INTEGER     NOT NULL CHECK (tokens_in >= 0),
    tokens_out      INTEGER     NOT NULL CHECK (tokens_out >= 0),
    latency_ms      INTEGER     NOT NULL CHECK (latency_ms >= 0)
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages (conversation_id);

CREATE TABLE IF NOT EXISTS failed_conversations (
    id              BIGSERIAL   PRIMARY KEY,
    load_date       DATE        NOT NULL,
    raw_line        TEXT        NOT NULL,
    conversation_id TEXT,
    reason          TEXT        NOT NULL,
    detail          TEXT        NOT NULL
);
"""


def write_batch(
    conn,
    load_date: date,
    valid: list[ConversationRecord],
    failed: list[FailedRecord],
) -> None:
    conn.execute("DELETE FROM conversations WHERE load_date = %s", (load_date,))
    conn.execute("DELETE FROM failed_conversations WHERE load_date = %s", (load_date,))
    _insert_conversations(conn, valid)
    _insert_messages(conn, valid)
    _insert_failed(conn, load_date, failed)


def _insert_conversations(conn, records: list[ConversationRecord]) -> None:
    if not records:
        return
    conn.executemany(
        """
        INSERT INTO conversations (conversation_id, load_date, user_id, started_at, model_version)
        VALUES (%s, %s, %s, %s, %s)
        """,
        [
            (r.conversation_id, r.load_date, r.user_id, r.started_at, r.model_version)
            for r in records
        ],
    )


def _insert_messages(conn, records: list[ConversationRecord]) -> None:
    rows = [
        (m.message_id, m.conversation_id, m.role, m.content,
         m.timestamp, m.tokens_in, m.tokens_out, m.latency_ms)
        for r in records
        for m in r.messages
    ]
    if not rows:
        return
    conn.executemany(
        """
        INSERT INTO messages
            (message_id, conversation_id, role, content, timestamp,
             tokens_in, tokens_out, latency_ms)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        rows,
    )


def _insert_failed(conn, load_date: date, records: list[FailedRecord]) -> None:
    if not records:
        return
    conn.executemany(
        """
        INSERT INTO failed_conversations (load_date, raw_line, conversation_id, reason, detail)
        VALUES (%s, %s, %s, %s, %s)
        """,
        [
            (load_date, r.raw_line, r.conversation_id, r.reason, r.detail)
            for r in records
        ],
    )
