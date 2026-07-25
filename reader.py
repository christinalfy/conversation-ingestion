import json
from typing import Any, Iterator


def read_lines(path: str) -> Iterator[str]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            yield line.rstrip("\n")


def parse_line(raw_line: str) -> tuple[Any, str | None]:
    try:
        return json.loads(raw_line), None
    except json.JSONDecodeError as e:
        return None, str(e)
