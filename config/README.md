# Configuration area — Police

This directory separates the shared match constitution from local choices. No supplied attachment defines a complete official field-level template, so this scaffold does not fabricate one.

## Known official artifacts

| Artifact | Classification | Lifecycle | Rules |
|---|---|---|---|
| `config/game.json` | Shared | Agreed and locked before play | Byte-for-byte identical at both peers, contains all agreed Appendix F values, and overrides a duplicate private key. Commit a uniquely named per-game copy for Replay and reporting. |
| `config/game.toml` | Private/local | Loaded locally before play | Never crosses the network; contains only local choices and cannot weaken a shared signed value. It must not contain secrets. |
| `declaration_<game_id>.json` | Shared reporting artifact | Generated before the series | The runtime instance is produced at this lifecycle point; its exact official template/schema remains a MISSING OFFICIAL INPUT. |
| `config_<game_id>_g<NN>.json` | Shared reporting artifact | Generated and locked before each sub-game | The runtime instance represents approved per-sub-game terms; its exact official template/schema remains a MISSING OFFICIAL INPUT. |
| `log_<game_id>_g<NN>.json` | Shared reporting artifact | Recorded during and finalized after each sub-game | The runtime instance records steps and integrity evidence; its exact official template/schema remains a MISSING OFFICIAL INPUT. |
| `result_<game_id>.json` | Shared reporting artifact | Generated after verified series settlement | The runtime instance summarizes verified outcomes and scores; its exact official template/schema remains a MISSING OFFICIAL INPUT. |

The missing input is the official field-level and canonical-signing contract, not a pre-completed match instance. T016 adopts that contract; T018 generates and reconciles the instances at the lifecycle points above.

## Binding parameter classes

- **Fixed:** immutable. Movement set, scent center/decay/field, six sub-games, fixed scores, diversity reward, and counted-match bounds include Fixed values.
- **Minimum:** never below the official threshold; any change must follow the approved interpretation of “harder.” OPEN-005 blocks ambiguous operational maxima.
- **Negotiated:** parties may agree freely; the official value is the default when there is no agreement.

Use `docs/spec/CANONICAL_REQUIREMENTS.md` CFG-004 through CFG-008 as the normalized register; do not substitute a sample number for the Appendix F authority.

## Negotiated contract shape (non-official)

`config/game.example.json` and `config/game.toml.example` (T028) demonstrate the nested-section layout and canonical key names recorded in `docs/decisions/ADR-001-shared-game-contract-shape.md`. This shape is our own negotiable engineering choice, not an attested official schema — no reconstruction of the project specification states a mandatory field structure for `config/game.json`, only that it must carry every Appendix F value (`CFG-004`) and remain byte-identical/locked (`CFG-001`). Both example files are labeled `EXAMPLE — NOT AN OFFICIAL ATTACHED TEMPLATE` and must not be presented as, or replaced by, an actual official template until `OPEN-001` is resolved.

## Private values and secrets

Runtime secrets belong in environment variables or local files ignored by Git. Never put OAuth credentials, tokens, keys, passwords, personal identifiers, or private member data in either JSON or TOML. `.env.example` contains placeholders only. `credentials.json`, `token.json`, `.env`, and key material are forbidden in commits.

Confirmed public team metadata is team name `ZeroOne`, team number `01`, GitHub handles `evya1` and `Us5rName`, and final-project group code `ZeroOne1`. Any optional language-model provider remains a P2 team decision; no provider-specific credential or model setting is predefined before selection.

## Missing official inputs

- Four official JSON templates/schemas and their exact canonical signing rules.
- Official Moodle Word form.
- Exact signing-key generation/distribution/rotation procedure.
- Valid eight-character final-project group code, repository URLs, public MCP URLs, opponent identifiers, match times, and any private identity fields required only by the official form.
- Lecturer/team resolution for OPEN-004, OPEN-005, OPEN-007, OPEN-008, and OPEN-009, including scent saturation/merge, role scheduling, and tie aggregation.

T001 records arrival and verification in `docs/inputs/INPUT_REGISTER.md`, then updates affected entries in `docs/spec/OPEN_QUESTIONS.md`. An example may be added only after approval and must be labeled `EXAMPLE — NOT AN OFFICIAL ATTACHED TEMPLATE`. Input receipt creates a Change Request only if an approved canonical product requirement must materially change.
