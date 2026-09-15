"""Source records: what the agent read.

In production these come over MCP from project boards, a calendar, a docs
wiki, and a chat tool. Here they are a JSON file so the pipeline runs with
no credentials and no tokens. Every record carries an id, and every claim
the agent makes must point back at one.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

SOURCE_KINDS = ("boards", "calendar", "docs", "chat")


@dataclass(frozen=True)
class Record:
    id: str
    kind: str
    title: str
    status: str
    changed: bool
    blocking_client: bool = False
    needs_decision: bool = False
    due: datetime | None = None
    detail: str = ""

    @property
    def is_noise(self) -> bool:
        return not self.changed and not self.needs_decision and self.due is None


@dataclass(frozen=True)
class SourceSet:
    as_of: datetime
    records: tuple[Record, ...]

    def by_id(self) -> dict[str, Record]:
        return {r.id: r for r in self.records}

    def counts(self) -> dict[str, int]:
        out = {k: 0 for k in SOURCE_KINDS}
        for r in self.records:
            out[r.kind] += 1
        return out


def _parse_dt(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"bad datetime: {value!r}")
    return datetime.fromisoformat(value)


def load_sources(path: str | Path) -> SourceSet:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "as_of" not in data or "records" not in data:
        raise ValueError("source file needs 'as_of' and 'records'")
    as_of = _parse_dt(data["as_of"])
    assert as_of is not None
    records: list[Record] = []
    seen: set[str] = set()
    for raw in data["records"]:
        rid = raw["id"]
        if rid in seen:
            raise ValueError(f"duplicate record id: {rid}")
        seen.add(rid)
        kind = raw["kind"]
        if kind not in SOURCE_KINDS:
            raise ValueError(f"unknown source kind: {kind}")
        records.append(Record(
            id=rid,
            kind=kind,
            title=raw["title"],
            status=raw.get("status", ""),
            changed=bool(raw.get("changed", False)),
            blocking_client=bool(raw.get("blocking_client", False)),
            needs_decision=bool(raw.get("needs_decision", False)),
            due=_parse_dt(raw.get("due")),
            detail=raw.get("detail", ""),
        ))
    return SourceSet(as_of=as_of, records=tuple(records))
