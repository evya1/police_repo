# `llm-provider` partner branch — hunk-level reconciliation

## Scope and status

The restored partner branch `origin/llm-provider` is **provenance, not a merge base**. It
was inspected read-only. No merge, rebase or cherry-pick from it exists in this branch's
history, and none is proposed.

| Item | Value |
|---|---|
| Partner tip | `f4509da95fd372656ee4469e1c6b39f64bd296e8` |
| Unique partner commits | `ed13ca1`, `d2ae021`, `f4509da` |
| Reconciled against | `claude/replay-llm-completion-20260823` |
| Ancestry | `git merge-base --is-ancestor origin/llm-provider HEAD` → exit **1** (not an ancestor) |
| Date | 2026-08-23 |

Reproduce:

```sh
git fetch --all --tags --prune
git rev-parse origin/llm-provider
git merge-base --is-ancestor origin/llm-provider HEAD; echo $?
git log --left-right --cherry-pick --oneline HEAD...origin/llm-provider
git diff --find-renames --stat origin/llm-provider HEAD
```

The two branches diverged from a shared ancestor; the partner commits are parallel
siblings, not cherries of this branch. `--cherry-pick` therefore drops nothing.

## Disposition table

| Partner file / behavior | Commit | Disposition | Where it lives now, or why not |
|---|---|---|---|
| `strategy/providers/language_model.py` — `OpenAIProvider`, `OllamaProvider` classes | `ed13ca1` | **REJECT_ARCHITECTURE** | A provider class inside `strategy/` is exactly what AGENTS.md forbids: strategy must not know a vendor. Superseded by `infra/llm_provider.py::LanguageModelAdapter` behind the `infra/llm_client.py::CompletionClient` protocol. Being stdlib-only does not make it acceptable — the objection is the layer, not the dependency. |
| Same file — provider returning a verdict/action-shaped dict | `ed13ca1` | **REJECT_ARCHITECTURE** | A provider returns text plus provider/model/token metadata and nothing else. Movement, barrier, truth/lie, capture, verdict and score stay with the deterministic algorithm. |
| Same file — raw position passed to the provider | `ed13ca1` | **REJECT_ARCHITECTURE** | The privacy allowlist excludes it. Handing objective own-state to an external service is the leak the hidden-state game exists to prevent. |
| Same file — `provider`, `model`, `every_n_steps`, template fallback, word cap | `ed13ca1` | **PORT_SEMANTICALLY** | The *concepts* are right; the location was not. They belong in frozen settings parsed once at the composition root (T051), never read below it. |
| `strategy/providers/transports.py` — OpenAI-compatible and Ollama HTTP request/response mapping | `ed13ca1` | **KEEP_AS_PROVENANCE_ONLY** | Real, reusable transport knowledge. It stays documented here and is **not** carried as dead runtime code. When PLANQ-003 actually names a vendor, T050 turns it into exactly one isolated `CompletionClient`; the partner's strategy modules are never restored. |
| `strategy/inject.py` — `resolve_text_provider(config)` | `ed13ca1` | **ALREADY_REPLACED** | `resolve_brain(..., llm: TextProvider \| None)` is the current seam. `resolve_text_provider` must not be reintroduced. |
| `wire/strategy_settings.py`, `config/game.toml.example` — private provider config | `ed13ca1` | **PORT_SEMANTICALLY** | As frozen settings at the composition root. No secret in committed config, no environment read below composition. This is not an open "config vs injection" question — the layering is settled by AGENTS.md. |
| `test_language_model.py` — timeout, 429, outage, malformed, cadence, cap cases | `ed13ca1` | **PORT_SEMANTICALLY** | Reproduced against fake `CompletionClient`s and the Gatekeeper. No network, no credentials. Cases asserting provider-supplied verdicts or coordinates are **not** ported. |
| `wire/session.py` — add the engine's own post-move `position` to the sealed payload | `d2ae021` | **PORT_SEMANTICALLY — PORTED** | This was a genuine defect the partner found first. Now bound in `wire/sealed_payload.py` at the single construction boundary, before the commit is computed. Absent from `PUBLIC_TURN_KEYS` and from any provider prompt. Never appended to the envelope after hashing. |
| `audit_physics.py` — prefer explicit `position`, fall back to legacy `state` | `d2ae021` | **PORT_SEMANTICALLY — PORTED** | `check_physics` now prefers a strictly-parsed explicit position. Strict on purpose: a malformed or foreign value degrades to the `state` fallback, never a loose re-read, never a manufactured tamper claim. |
| `turnseal.py` — top-level audit `sender`; nested record envelope | `d2ae021` | **Split: sender/nesting PORTED at the boundary; global rewrite REJECT_ARCHITECTURE** | The kit's top-level `sender` and nested records are real requirements — but they belong in the `KitAuditWire` adapter (`common/transport/audit_wire.py`), applied to the *already-committed* payload. Rewriting the internal flat record shape globally would create a second record representation and risk a second commitment path. The internal shape is unchanged and correct. |
| `audit.py` — understand nested kit records | `d2ae021` | **ALREADY_REPLACED, now production-wired** | T052 built `unwrap_inbound*`; T054 invokes it in the live receive path, *before* the existing verifier. `_signed_payload` is not copied — one decoder, one verdict taxonomy. |
| `subgame.py` — thief settles from its own terminal knowledge | `d2ae021` | **ALREADY_REPLACED** | The current lifecycle already contains terminal settlement with regression coverage. No duplicate branch added. |
| Configurable OpenAI base URL | `f4509da` | **REQUIRES_EXTERNAL_DECISION** | Blocked on PLANQ-003. If approved, the value is passed into one client constructor from composition — never read inside a strategy or client method. |
| Quality/fixture cleanup, formatting | `f4509da` | **ALREADY_REPLACED / mechanical** | Current gates pass on their own. Historical formatting changes are not cherry-picked. |

## Corrections to the automated inventory

A first-pass mechanical inventory of these branches reached three conclusions that are
**wrong** and are recorded here so they are not repeated:

1. It labelled the `turnseal.py` flat→nested rewrite `REQUIRES_EXTERNAL_DECISION` and called
   the current flat record a blocker for kit interoperability. It is not. Kit nesting is an
   edge concern, applied by the boundary adapter to a payload that is already sealed. The
   internal flat shape is deliberate and stays.
2. It reported **zero** `REJECT_ARCHITECTURE` hunks, reasoning that the partner's provider
   classes use only the standard library. The objection was never the dependency; it is that
   `strategy/` must not contain a vendor provider at all.
3. It listed "port the partner's vendor clients" as a blocker. T050 is blocked by
   PLANQ-003, which is still `PARTIALLY RESOLVED` and names no provider, model, budget,
   cadence or rate policy. No vendor client is implemented in this run.

## Duplication audit

```sh
git grep -nE 'class (OpenAIProvider|OllamaProvider)|resolve_text_provider'   # expect: no matches
git grep -n 'class LanguageModelAdapter'                                     # expect: exactly one
git grep -n 'class CompletionClient'                                         # expect: exactly one
git grep -nE 'OPENAI_API_KEY|OPENAI_BASE_URL|OLLAMA' -- src                  # expect: no matches
```

No rejected partner provider class survives, one provider-neutral adapter exists, one narrow
`CompletionClient` contract exists, and there is one commitment authority for turn and audit
records.

## Easy later activation, without dead code

`CompletionClient` is the single production extension seam. Strategy knows only
`TextProvider`. When PLANQ-003 resolves, T050 adds exactly one isolated client module that
implements `CompletionClient` — not a strategy rewrite, and not a restoration of the
partner's classes. Until then `template` is the only configured production default, at
0/0 tokens, and this document is where the partner's transport knowledge is preserved.
