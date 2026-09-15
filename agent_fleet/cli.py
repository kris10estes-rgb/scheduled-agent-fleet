"""Command line.

    python -m agent_fleet run   specs/daily_pulse.md examples/sources_weekday.json
    python -m agent_fleet eval  specs/daily_pulse.md examples/sources_weekday.json
    python -m agent_fleet specs specs/
"""

from __future__ import annotations

import argparse
import sys

from . import evals
from .run import scheduled_run
from .spec import load_all


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agent_fleet")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="draft the pulse")
    p_run.add_argument("spec")
    p_run.add_argument("sources")

    p_eval = sub.add_parser("eval", help="draft the pulse and run the evals")
    p_eval.add_argument("spec")
    p_eval.add_argument("sources")

    p_specs = sub.add_parser("specs", help="validate every spec in a folder")
    p_specs.add_argument("directory")

    args = parser.parse_args(argv)

    try:
        if args.command == "specs":
            specs = load_all(args.directory)
            for s in specs:
                flag = "send: never" if not s.may_send else "SEND ALLOWED"
                print(f"{s.name:24} {s.schedule:24} {flag}")
            bad = [s.name for s in specs if s.may_send or not s.cites_sources]
            if bad:
                print(f"error: specs failing the standard: {', '.join(bad)}", file=sys.stderr)
                return 1
            return 0

        _, sources, pulse = scheduled_run(args.spec, args.sources)
        print(pulse.render())
        if args.command == "run":
            return 0
        results = evals.run_all(pulse, sources)
        print(evals.render(results))
        return 0 if all(r.passed for r in results) else 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
