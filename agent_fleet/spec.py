"""Agent specs are Markdown files with a small front-matter block.

The front matter is the machine-readable contract: what the agent reads,
what it produces, and whether it may send. The body is the prompt standard a
human reads and reviews. Both live in one file so they cannot drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REQUIRED_KEYS = ("name", "schedule", "sources", "output", "send")
KNOWN_SOURCES = ("boards", "calendar", "docs", "chat")


@dataclass(frozen=True)
class AgentSpec:
    name: str
    schedule: str
    sources: tuple[str, ...]
    output: str
    send: str
    body: str

    @property
    def may_send(self) -> bool:
        return self.send.strip().lower() != "never"

    @property
    def cites_sources(self) -> bool:
        text = self.body.lower()
        return "cite" in text and "source" in text


def parse_spec(text: str) -> AgentSpec:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("spec must start with a front-matter block")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("front-matter block is not closed") from exc

    meta: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"bad front-matter line: {line!r}")
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()

    missing = [k for k in REQUIRED_KEYS if k not in meta]
    if missing:
        raise ValueError(f"spec is missing front-matter keys: {', '.join(missing)}")

    sources = tuple(s.strip() for s in meta["sources"].split(",") if s.strip())
    unknown = [s for s in sources if s not in KNOWN_SOURCES]
    if unknown:
        raise ValueError(f"unknown sources: {', '.join(unknown)}")

    return AgentSpec(
        name=meta["name"],
        schedule=meta["schedule"],
        sources=sources,
        output=meta["output"],
        send=meta["send"],
        body="\n".join(lines[end + 1:]).strip(),
    )


def load_spec(path: str | Path) -> AgentSpec:
    return parse_spec(Path(path).read_text(encoding="utf-8"))


def load_all(directory: str | Path) -> list[AgentSpec]:
    return [load_spec(p) for p in sorted(Path(directory).glob("*.md"))]
