"""The priority logic, as code.

Four rules from the spec, applied in order:

1. Anything blocking a client deliverable comes first.
2. Flag every deadline inside 48 hours.
3. Drop the noise. No status with no change.
4. Lead with what leadership must act on.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .sources import Record, SourceSet

DEADLINE_WINDOW = timedelta(hours=48)


@dataclass(frozen=True)
class Ranked:
    needs_decision: tuple[Record, ...]
    on_track: tuple[Record, ...]
    deadlines: tuple[Record, ...]
    dropped: tuple[Record, ...]


def inside_window(record: Record, as_of: datetime) -> bool:
    return record.due is not None and as_of <= record.due <= as_of + DEADLINE_WINDOW


def rank(sources: SourceSet) -> Ranked:
    as_of = sources.as_of
    kept = [r for r in sources.records if not r.is_noise]
    dropped = [r for r in sources.records if r.is_noise]

    # Rule 4 picks the section; rule 1 orders inside it.
    decisions = [r for r in kept if r.needs_decision]
    decisions.sort(key=lambda r: (not r.blocking_client, r.id))

    deadlines = [r for r in kept if inside_window(r, as_of) and not r.needs_decision]
    deadlines.sort(key=lambda r: (r.due, r.id))  # type: ignore[arg-type]

    seen = {r.id for r in decisions} | {r.id for r in deadlines}
    on_track = [r for r in kept if r.id not in seen and r.changed]
    on_track.sort(key=lambda r: (not r.blocking_client, r.id))

    return Ranked(
        needs_decision=tuple(decisions),
        on_track=tuple(on_track),
        deadlines=tuple(deadlines),
        dropped=tuple(dropped),
    )
