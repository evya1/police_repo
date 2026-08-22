---
artifact: adr
id: ADR-007
status: accepted
date: 2026-08-22
owners: orchestrator
related_requirements: [ARCH-007, NET-001, ARCH-002, ARCH-003]
related_tasks: [T037, T038, T041]
supersedes:
---

# ADR-007 — How Each Repository Obtains Both Role Policies After Role Alternation

## Context

Match play requires each peer to run against the opposing role's strategy (self-play/KPI harnesses, league pairing where a repository may need to simulate or evaluate the opposing role locally). `thief_repo` owns the Thief policy; `police_repo` owns the Police policy. `AGENTS.md` in both repositories prohibits "shared live memory/module with the sibling peer" and requires "no direct numeric-position replacement" or hidden coupling; there is no runtime cross-repo import mechanism, and none should be built.

## Decision

1. Each role-owned policy is landed first, in its owning repository, under its own task (W3 in `thief_repo`, W4 in `police_repo`), fully reviewed and merged there.
2. Only after a role policy is accepted in its owning repository does the **sibling** repository receive it, via a **separately reviewed static port** — a plain code copy (not an import, not a git submodule, not a shared package) placed under a clearly labeled path in the sibling repo (e.g. `src/<role>_peer/opponents/reference_<other_role>.py`), used only for local KPI/self-play evaluation and league-pairing simulation, never for the sibling's own move selection.
3. The static port is a point-in-time copy with explicit provenance (source repo, source commit SHA, port date) recorded in a header comment and in the porting task's evidence. It is never live-synced; a later change to the owning repository's policy does not silently propagate — re-porting is its own reviewed task.
4. No runtime cross-repo imports, no shared live process/module, no network call between the two repositories' processes for this purpose. The only inter-peer communication remains the existing MCP wire protocol.
5. This port step is tracked as its own task (`T041` in both repositories) so it is reviewed independently of both W3 and W4's core-policy work and does not silently expand either wave's write-set.

## Alternatives considered

- **Runtime cross-repo import (e.g. `pip install -e ../thief_repo`).** Rejected outright: violates AGENTS.md's "no shared live memory/module with the sibling peer" prohibition and breaks the two-process independence the referee-less design depends on.
- **A third shared repository/package holding both policies.** Rejected: no such shared package exists in the current architecture (`common/` holds only role-agnostic protocol/domain code per ADR-005), and introducing one is a durable architecture change beyond this task's scope.
- **Skip the port; evaluate self-play only against a stand-in/greedy opponent.** Rejected as the sole approach: KPI harnesses already use stand-ins (e.g. `GreedyCapturingPolice` in `thief_repo`'s PR #36 work) for baseline evaluation, but the two owning repositories should also be able to evaluate against the *real* sibling policy once it is stable — that is the purpose of the static port, used in addition to, not instead of, stand-in opponents.

## Consequences

- W3/W4 stay scoped to each repository's own strategy core; the port is a separate, later, reviewed task (`T041`) with its own write-set.
- Divergence risk: a static port can go stale. Mitigation: the port's provenance header names the exact source SHA, and `T041`'s acceptance criteria require re-porting (not silent drift) whenever the owning repository's policy changes materially.
- No change to production runtime composition (`sdk.py` in either repo continues to wire only its own role's real brain; the ported sibling policy is evaluation-only).

## Validation

- The ported file is byte-inspectable against the named source SHA in the owning repository at port time.
- `uv run pytest` in the receiving repository passes with the ported policy exercised only from KPI/self-play/league-simulation test paths, never from `sdk.py`'s production wiring.

## Approval

- Decision owner: orchestrator (governance/task-preparation session, 2026-08-22)
- Approved by: project team — recorded per this session's explicit instruction
- Approval date: 2026-08-22
