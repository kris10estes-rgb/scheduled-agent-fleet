"""Compose the pulse.

Every content line ends with a source reference in square brackets. The
pulse is a draft object with no send method; sending lives in approval.py
and requires a named human.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .priority import Ranked, rank
from .sources import Record, SourceSet


@dataclass(frozen=True)
class Line:
    text: str
    source_id: str

    def render(self) -> str:
        return f"{self.text} [{self.source_id}]"


@dataclass(frozen=True)
class Pulse:
    as_of: str
    needs_decision: tuple[Line, ...]
    on_track: tuple[Line, ...]
    deadlines: tuple[Line, ...]
    read_counts: dict[str, int] = field(default_factory=dict)
    status: str = "draft"

    @property
    def lines(self) -> tuple[Line, ...]:
        return self.needs_decision + self.on_track + self.deadlines

    def render(self) -> str:
        out = [f"DAILY OPERATIONAL PULSE · {self.as_of}", ""]
        out.append(f"NEEDS A DECISION ({len(self.needs_decision)})")
        if self.needs_decision:
            for i, line in enumerate(self.needs_decision, 1):
                out.append(f"{i}. {line.render()}")
        else:
            out.append("- nothing today")
        out.append("")
        out.append(f"ON TRACK ({len(self.on_track)})")
        out.extend(f"- {line.render()}" for line in self.on_track) if self.on_track else out.append("- nothing changed")
        out.append("")
        out.append(f"DEADLINES INSIDE 48H ({len(self.deadlines)})")
        out.extend(f"- {line.render()}" for line in self.deadlines) if self.deadlines else out.append("- none listed")
        out.append("")
        counts = ", ".join(f"{n} {k}" for k, n in self.read_counts.items() if n)
        out.append(f"read: {counts}")
        out.append(f"drafted by the agent, {'unsent' if self.status == 'draft' else self.status}")
        return "\n".join(out) + "\n"


def _phrase(record: Record) -> str:
    text = record.title.rstrip(".")
    if record.detail:
        text = f"{text}: {record.detail.rstrip('.')}"
    return text


def _deadline_phrase(record: Record) -> str:
    when = record.due.strftime("%A") if record.due else "not listed"
    return f"{record.title.rstrip('.')} due {when}"


def compose(sources: SourceSet, ranked: Ranked | None = None) -> Pulse:
    ranked = ranked or rank(sources)
    return Pulse(
        as_of=sources.as_of.strftime("%Y-%m-%d %I:%M %p").lstrip("0"),
        needs_decision=tuple(Line(_phrase(r), r.id) for r in ranked.needs_decision),
        on_track=tuple(Line(_phrase(r), r.id) for r in ranked.on_track),
        deadlines=tuple(Line(_deadline_phrase(r), r.id) for r in ranked.deadlines),
        read_counts=sources.counts(),
    )
