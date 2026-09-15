"""The human gate.

The agent produces a draft and stops. Sending is a separate function that
takes a named approver and refuses anything else. There is no code path
from the scheduled run to this function; the eval harness checks for that.
"""

from __future__ import annotations

from dataclasses import replace

from .pulse import Pulse


class ApprovalRequired(RuntimeError):
    pass


def approve_and_send(pulse: Pulse, approver: str) -> Pulse:
    if not approver or not approver.strip():
        raise ApprovalRequired("a named human must approve before anything is sent")
    if pulse.status != "draft":
        raise ApprovalRequired(f"only drafts can be sent; this pulse is {pulse.status}")
    # In production this is where the message goes to its channel.
    return replace(pulse, status=f"sent, approved by {approver.strip()}")
