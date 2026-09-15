"""The scheduled run: read, rank, draft. Nothing else.

This module is what the scheduler calls. It has no import of approval.py,
and the eval harness checks it stays that way.
"""

from __future__ import annotations

from pathlib import Path

from .pulse import Pulse, compose
from .sources import SourceSet, load_sources
from .spec import AgentSpec, load_spec


def scheduled_run(spec_path: str | Path, sources_path: str | Path) -> tuple[AgentSpec, SourceSet, Pulse]:
    spec = load_spec(spec_path)
    if spec.may_send:
        raise ValueError(f"spec {spec.name} allows sending; the fleet does not run specs like that")
    sources = load_sources(sources_path)
    pulse = compose(sources)
    return spec, sources, pulse
