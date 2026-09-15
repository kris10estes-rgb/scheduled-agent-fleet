"""The eval harness.

Two rules the fleet lives by, checked on every run, plus the priority
logic the spec promises:

  E1  Every claim cites a source, and the source exists.
  E2  Nothing sends without a human. The run leaves a draft, and the
      scheduled path never imports the approval module.
  E3  Nothing blocking a client sits below something that is not.
  E4  Every deadline inside 48 hours appears.
  E5  Nothing unchanged appears.

A failed eval is a failed run. The pulse is still written, so a human can
see what went wrong, but the exit code is non-zero.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from .priority import inside_window
from .pulse import Pulse
from .sources import SourceSet

CITATION = re.compile(r"\[([A-Za-z0-9_.:-]+)\]\s*$")
SCHEDULED_MODULES = ("spec.py", "sources.py", "priority.py", "pulse.py", "run.py")


@dataclass(frozen=True)
class EvalResult:
    code: str
    passed: bool
    detail: str


def e1_every_claim_cites(pulse: Pulse, sources: SourceSet) -> EvalResult:
    known = sources.by_id()
    bad: list[str] = []
    for line in pulse.lines:
        m = CITATION.search(line.render())
        if not m:
            bad.append(f"no citation: {line.text}")
        elif m.group(1) not in known:
            bad.append(f"unknown source {m.group(1)}: {line.text}")
    return EvalResult("E1", not bad, "; ".join(bad) or f"{len(pulse.lines)} lines, all cited")


def e2_nothing_sends(pulse: Pulse, package_dir: Path | None = None) -> EvalResult:
    problems: list[str] = []
    if pulse.status != "draft":
        problems.append(f"pulse status is {pulse.status!r}, not draft")
    package_dir = package_dir or Path(__file__).resolve().parent
    for name in SCHEDULED_MODULES:
        path = package_dir / name
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and "approval" in node.module:
                problems.append(f"{name} imports approval")
            if isinstance(node, ast.Import) and any("approval" in a.name for a in node.names):
                problems.append(f"{name} imports approval")
    return EvalResult("E2", not problems, "; ".join(problems) or "draft only, no send path in the scheduled run")


def e3_blocking_first(pulse: Pulse, sources: SourceSet) -> EvalResult:
    known = sources.by_id()
    for section in (pulse.needs_decision, pulse.on_track):
        seen_non_blocking = False
        for line in section:
            rec = known.get(line.source_id)
            if rec is None:
                continue
            if rec.blocking_client and seen_non_blocking:
                return EvalResult("E3", False, f"blocking item {rec.id} ranked below a non-blocking one")
            if not rec.blocking_client:
                seen_non_blocking = True
    return EvalResult("E3", True, "blocking items lead every section")


def e4_deadlines_flagged(pulse: Pulse, sources: SourceSet) -> EvalResult:
    cited = {line.source_id for line in pulse.lines}
    missing = [r.id for r in sources.records if inside_window(r, sources.as_of) and r.id not in cited]
    return EvalResult("E4", not missing, "; ".join(f"missing deadline {m}" for m in missing) or "every 48h deadline appears")


def e5_noise_dropped(pulse: Pulse, sources: SourceSet) -> EvalResult:
    known = sources.by_id()
    leaked = [line.source_id for line in pulse.lines if known.get(line.source_id) and known[line.source_id].is_noise]
    return EvalResult("E5", not leaked, "; ".join(f"unchanged item {x} appeared" for x in leaked) or "no unchanged items in the pulse")


def run_all(pulse: Pulse, sources: SourceSet) -> list[EvalResult]:
    return [
        e1_every_claim_cites(pulse, sources),
        e2_nothing_sends(pulse),
        e3_blocking_first(pulse, sources),
        e4_deadlines_flagged(pulse, sources),
        e5_noise_dropped(pulse, sources),
    ]


def render(results: list[EvalResult]) -> str:
    out = []
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        out.append(f"{mark}  {r.code}  {r.detail}")
    return "\n".join(out) + "\n"
