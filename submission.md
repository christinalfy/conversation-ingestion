# Conversation Ingestion Pipeline

Daily pipeline for AI assistant conversation logs: 
1. read input JSONL file
2. validate
3. process (parse + validate + dedup)
4. write to Postgres

---

## Schema

Two tables plus a failed-records table. Full DDL in [writer.py](writer.py).

```sql
conversations   -- one row per conversation
messages        -- one row per message (FK → conversations, ON DELETE CASCADE)
failed_conversations  -- records that failed JSON parsing or validation
```

`conversations` is keyed on `conversation_id` (globally unique). 
`messages` is keyed on `message_id`. 

---

## Key Decisions

| Decision | What we chose | Alternative | Why |
|----------|--------------|-------------|-----|
| Table structure | 2 tables: conversations + messages | single table | Conversations and messages are distinct entities — each table stores only what belongs to that entity. |
| Idempotency on reruns | `DELETE WHERE load_date = X` + `INSERT` in one transaction | `UPSERT` | Full-day replacement semantics: if a corrected file removes a conversation entirely, UPSERT silently leaves the old row. DELETE+INSERT guarantees the warehouse matches exactly what's in the file. On failure, the transaction rolls back and the previous load stays intact. |
| Validation | Fail the whole conversation | Fail only the invalid message | A conversation with one invalid message has unreliable token totals even if other messages look fine. Failing the whole unit gives a clean, monitorable rejection rate; an upstream fix clears it on re-run. |

---

## Ingestion Pipeline

| Stage | File | Description |
|-------|------|-------------|
| `read_lines(path)` | [reader.py](reader.py) | yields raw text lines |
| `parse_line(line)` | [reader.py](reader.py) | dict \| parse error |
| `validate_conversation()` | [validator.py](validator.py) | ConversationRecord \| ValidationError |
| `process_file(lines)` | [conversation_pipeline.py](conversation_pipeline.py) | (valid_records, failed_records) — entire file before any DB writes |
| `write_batch(conn, ...)` | [writer.py](writer.py) | atomic DELETE + batch INSERT |

### `load_day(path, load_date, conn) -> LoadStats`

```
LoadStats
  lines_seen            total lines read
  conversations_loaded  successfully inserted
  messages_loaded       successfully inserted
  parse_errors          lines that failed json.loads
  validation_errors     parsed but structurally invalid
```

---

## Validation Rules

| Case | Rule | Why |
|------|------|-----|
| Malformed JSON | Catch `json.JSONDecodeError` | Cannot extract any fields |
| Missing required field | `_require_str()` / `_require_nonneg_int()` raises |  |
| Wrong type (`tokens_in: "five"`) | `isinstance(val, int)` check | Value error |
| Negative tokens / latency | `val < 0` check | Value error |
| Unknown role | Check against `{"user", "assistant", "system"}` | Business invariant |
| Empty messages list | `len(messages) == 0` check | A conversation with no messages is structurally meaningless |

---

## Future Improvements

- **Monitoring** Wire `LoadStats.validation_errors / lines_seen` into alerting/dashboard

- **`COPY` over `executemany` for large files.** `psycopg2.copy_expert` / `psycopg3` COPY is 5–10x faster than `executemany` by bypassing the query planner per row. Validation must be complete before the COPY call — which is already the design here.

