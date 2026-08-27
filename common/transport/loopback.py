"""Both peers in one process, over the same four-tool surface as the wire.

This is not a mock. It is the same message dicts, the same tool names, the same
the same replies; only the hop is a function call. That is what lets the entire series —
handshake, six sub-games, mutual audits, artifacts — run in CI with **no dependencies installed**,
and it is why the fault injector in ``faults.py`` can prove the receiver contract without a
network to be flaky.

The four tools mirror the reference's surface exactly, including the argument-name asymmetry that
catches people out on a first meeting: ``negotiate``, ``receive_turn`` and ``receive_control``
take ``message``; ``submit_audit`` takes ``payload``.
"""

from __future__ import annotations

import threading
from collections import deque
from collections.abc import Mapping

from common.transport.canonical import canonical_bytes
from common.transport.tool_replies import accepted_audit_response


class Inboxes:
    """One peer's four queues. A handler's whole job is to validate, enqueue, and return."""

    def __init__(self) -> None:
        self.agreements: deque[dict] = deque()
        self.turns: deque[dict] = deque()
        self.audits: deque[dict] = deque()
        self.controls: deque[dict] = deque()
        # Optional live-wire compatibility responder.  The professor's mailbox
        # contract needs only {"ok": true}; some league peers additionally use
        # the immediate tool result as their counter-signature evidence.
        self.agreement_reply = None
        # Set by the outbound channel immediately before disclosing our audit.
        # The server may return the same reveal to peers that consume audit
        # evidence from the synchronous tool result as well as the symmetric push.
        self.audit_reply = None
        self._seen_audits: set[bytes] = set()
        # FastMCP dispatches sync tool handlers onto worker threads, so two
        # concurrent submit_audit calls can interleave here. The lock makes
        # deduplicate-or-enqueue one indivisible step for every caller.
        self._audit_lock = threading.Lock()

    def enqueue_audit(self, payload: dict) -> bool:
        """Enqueue one exact audit once; absorb at-least-once redelivery."""
        fingerprint = canonical_bytes(payload)
        with self._audit_lock:
            if fingerprint in self._seen_audits:
                return False
            self._seen_audits.add(fingerprint)
            self.audits.append(payload)
            return True

    def drain(self) -> None:
        with self._audit_lock:
            for q in (self.agreements, self.turns, self.audits, self.controls):
                q.clear()
            self._seen_audits.clear()


class LoopbackPeer:
    """The callable surface one peer exposes to the other."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.inboxes = Inboxes()

    # The four tools. Each does exactly three things and returns — never blocking on game
    # progress, because two peers each awaiting the other inside a handler is an instant
    # deadlock, and that is the highest-severity failure available in this design.
    def negotiate(self, message: dict) -> dict:
        self.inboxes.agreements.append(message)
        return {"ok": True}

    def receive_turn(self, message: dict) -> dict:
        self.inboxes.turns.append(message)
        return {"ok": True}

    def submit_audit(self, payload: dict) -> dict:
        self.inboxes.enqueue_audit(payload)
        reply = self.inboxes.audit_reply
        required = {"sender", "records", "result_claim"}
        if isinstance(reply, Mapping) and required <= reply.keys():
            return accepted_audit_response(reply)
        return {"ok": True}

    def receive_control(self, message: dict) -> dict:
        self.inboxes.controls.append(message)
        return {"ok": True}


class LoopbackTransport:
    """What a peer uses to reach the other side."""

    def __init__(self, ours: LoopbackPeer, theirs: LoopbackPeer) -> None:
        self.ours = ours
        self.theirs = theirs

    # --- outbound ---------------------------------------------------------------------------
    def send_agreement(self, message: dict) -> dict:
        return self.theirs.negotiate(message)

    def send_turn(self, message: dict) -> dict:
        return self.theirs.receive_turn(message)

    def send_audit(self, payload: dict) -> dict:
        self.ours.inboxes.audit_reply = payload
        return self.theirs.submit_audit(payload)

    def send_control(self, message: dict) -> dict:
        return self.theirs.receive_control(message)

    # --- inbound ----------------------------------------------------------------------------
    def poll_agreement(self) -> dict | None:
        return self.ours.inboxes.agreements.popleft() if self.ours.inboxes.agreements else None

    def poll_turn(self) -> dict | None:
        return self.ours.inboxes.turns.popleft() if self.ours.inboxes.turns else None

    def poll_audit(self) -> dict | None:
        return self.ours.inboxes.audits.popleft() if self.ours.inboxes.audits else None

    def poll_control(self) -> dict | None:
        return self.ours.inboxes.controls.popleft() if self.ours.inboxes.controls else None


def pair(a_name: str = "A", b_name: str = "B") -> tuple[LoopbackTransport, LoopbackTransport]:
    a, b = LoopbackPeer(a_name), LoopbackPeer(b_name)
    return LoopbackTransport(a, b), LoopbackTransport(b, a)
