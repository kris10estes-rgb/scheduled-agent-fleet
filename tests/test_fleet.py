"""Tests for the fleet.

Two kinds. The first proves the good path: the spec loads, the pulse is
right, the evals pass. The second proves the evals bite: hand the harness a
broken pulse and it fails the right rule.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from agent_fleet import (
    ApprovalRequired, Line, Pulse, Record, SourceSet,
    approve_and_send, compose, load_sources, load_spec, parse_spec, rank, run_all, scheduled_run,
)
from agent_fleet import evals
from agent_fleet.cli import main
from agent_fleet.spec import load_all

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "specs" / "daily_pulse.md"
SOURCES = ROOT / "examples" / "sources_weekday.json"


@pytest.fixture
def sources() -> SourceSet:
    return load_sources(SOURCES)


@pytest.fixture
def pulse(sources) -> Pulse:
    return compose(sources)


# ---------- specs ----------

def test_every_spec_forbids_sending_and_cites_sources():
    specs = load_all(ROOT / "specs")
    assert len(specs) == 3
    for s in specs:
        assert not s.may_send, s.name
        assert s.cites_sources, s.name


def test_daily_spec_front_matter():
    s = load_spec(SPEC)
    assert s.name == "daily_pulse"
    assert s.sources == ("boards", "calendar", "docs", "chat")
    assert s.output == "pulse"


@pytest.mark.parametrize("text,message", [
    ("# no front matter", "must start"),
    ("---\nname: x\n", "not closed"),
    ("---\nname: x\n---\n", "missing front-matter keys"),
    ("---\nname: x\nschedule: y\nsources: email\noutput: z\nsend: never\n---\n", "unknown sources"),
])
def test_bad_specs_are_rejected(text, message):
    with pytest.raises(ValueError, match=message):
        parse_spec(text)


def test_run_refuses_a_spec_that_may_send(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text("---\nname: bad\nschedule: x\nsources: boards\noutput: y\nsend: yes\n---\ncite the source\n")
    with pytest.raises(ValueError, match="allows sending"):
        scheduled_run(bad, SOURCES)


# ---------- priority logic ----------

def test_sample_pulse_sections(pulse):
    assert [l.source_id for l in pulse.needs_decision] == ["board:rollout-04", "chat:sla-thread"]
    assert [l.source_id for l in pulse.on_track][0] == "board:migration-b2"
    assert [l.source_id for l in pulse.deadlines] == ["cal:pricing-update"]


def test_blocking_decision_ranks_first(sources):
    ranked = rank(sources)
    assert ranked.needs_decision[0].blocking_client


def test_unchanged_items_are_dropped(sources):
    ranked = rank(sources)
    dropped = {r.id for r in ranked.dropped}
    assert {"doc:sop-naming", "board:evergreen-refresh"} <= dropped


def test_deadline_outside_window_is_not_flagged(sources):
    ranked = rank(sources)
    assert "cal:next-week-review" not in {r.id for r in ranked.deadlines}


@pytest.mark.parametrize("hours,flagged", [(0, True), (47, True), (48, True), (49, False), (-1, False)])
def test_48_hour_boundary(hours, flagged):
    as_of = datetime(2026, 9, 16, 6, 0)
    rec = Record("cal:x", "calendar", "Thing", "scheduled", changed=False, due=as_of + timedelta(hours=hours))
    ranked = rank(SourceSet(as_of, (rec,)))
    assert (rec in ranked.deadlines) is flagged


# ---------- output ----------

def test_every_rendered_line_ends_with_a_citation(pulse):
    for line in pulse.lines:
        assert line.render().endswith(f"[{line.source_id}]")


def test_render_footer_reports_reads_and_unsent(pulse):
    text = pulse.render()
    assert "read: 4 boards, 2 calendar, 2 docs, 2 chat" in text
    assert text.rstrip().endswith("drafted by the agent, unsent")
    assert pulse.status == "draft"


def test_empty_sources_still_render():
    p = compose(SourceSet(datetime(2026, 9, 16, 6, 0), ()))
    text = p.render()
    assert "NEEDS A DECISION (0)" in text
    assert "nothing today" in text


# ---------- the human gate ----------

def test_approval_requires_a_name(pulse):
    with pytest.raises(ApprovalRequired):
        approve_and_send(pulse, "")
    with pytest.raises(ApprovalRequired):
        approve_and_send(pulse, "   ")


def test_approval_sends_once(pulse):
    sent = approve_and_send(pulse, "Operations lead")
    assert sent.status == "sent, approved by Operations lead"
    with pytest.raises(ApprovalRequired):
        approve_and_send(sent, "Operations lead")


# ---------- evals: the good path ----------

def test_all_evals_pass_on_sample(pulse, sources):
    results = run_all(pulse, sources)
    assert [r.code for r in results] == ["E1", "E2", "E3", "E4", "E5"]
    assert all(r.passed for r in results), evals.render(results)


# ---------- evals: the harness bites ----------

def test_e1_catches_a_claim_without_a_source(pulse, sources):
    broken = replace(pulse, on_track=pulse.on_track + (Line("Invented win", "board:does-not-exist"),))
    r = evals.e1_every_claim_cites(broken, sources)
    assert not r.passed and "unknown source" in r.detail


def test_e2_catches_a_sent_pulse(pulse):
    sent = approve_and_send(pulse, "someone")
    r = evals.e2_nothing_sends(sent)
    assert not r.passed and "not draft" in r.detail


def test_e2_catches_a_scheduled_module_importing_approval(tmp_path, pulse):
    (tmp_path / "run.py").write_text("from .approval import approve_and_send\n")
    r = evals.e2_nothing_sends(pulse, package_dir=tmp_path)
    assert not r.passed and "imports approval" in r.detail


def test_e3_catches_a_blocking_item_ranked_low(pulse, sources):
    swapped = replace(pulse, needs_decision=tuple(reversed(pulse.needs_decision)))
    r = evals.e3_blocking_first(swapped, sources)
    assert not r.passed


def test_e4_catches_a_missing_deadline(pulse, sources):
    stripped = replace(pulse, deadlines=())
    r = evals.e4_deadlines_flagged(stripped, sources)
    assert not r.passed and "cal:pricing-update" in r.detail


def test_e5_catches_noise_in_the_pulse(pulse, sources):
    leaked = replace(pulse, on_track=pulse.on_track + (Line("Naming SOP", "doc:sop-naming"),))
    r = evals.e5_noise_dropped(leaked, sources)
    assert not r.passed


# ---------- cli ----------

def test_cli_run_and_eval_exit_zero(capsys):
    assert main(["run", str(SPEC), str(SOURCES)]) == 0
    assert main(["eval", str(SPEC), str(SOURCES)]) == 0
    assert "PASS  E1" in capsys.readouterr().out


def test_cli_specs_validates_folder():
    assert main(["specs", str(ROOT / "specs")]) == 0


def test_cli_bad_path_exits_two():
    assert main(["run", str(SPEC), "nope.json"]) == 2
