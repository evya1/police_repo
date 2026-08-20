from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from common.transport.canonical import canonical_bytes

SCHEMA_VERSION = "internal-1"


class ArtifactError(Exception):
    pass


class SchemaError(ArtifactError):
    pass


class SignatureError(ArtifactError):
    pass


class IdentifierMismatchError(ArtifactError):
    pass


class FinalizedLogMutationError(ArtifactError):
    pass


def _validate_field_types(artifact_dict: dict[str, Any], expected_types: dict[str, Any]) -> None:
    # Check for missing required fields and type correctness
    for field_name, expected_type in expected_types.items():
        if field_name not in artifact_dict:
            raise SchemaError(f"Required field '{field_name}' is missing")
        value = artifact_dict[field_name]
        if isinstance(expected_type, tuple):
            if not isinstance(value, expected_type):
                type_names = ", ".join(t.__name__ for t in expected_type)
                raise SchemaError(
                    f"Field '{field_name}' must be one of ({type_names}), got {type(value).__name__}"
                )
        else:
            if not isinstance(value, expected_type):
                raise SchemaError(
                    f"Field '{field_name}' must be of type {expected_type.__name__}, got {type(value).__name__}"
                )

    # Check for unexpected extra fields
    extra_fields = set(artifact_dict.keys()) - set(expected_types.keys())
    if extra_fields:
        raise SchemaError(f"Disallowed extra field(s): {', '.join(sorted(extra_fields))}")


_SECRET_KEY_TOKENS = (
    "password",
    "passwd",
    "secret",
    "credential",
    "api_key",
    "apikey",
    "private_key",
    "privatekey",
    "access_key",
    "accesskey",
    "refresh_token",
    "refreshtoken",
    "access_token",
    "accesstoken",
    "auth_token",
    "authtoken",
    "bearer",
    "client_secret",
    "clientsecret",
    "oauth",
)


def _scan_secrets(name: str, value: Any) -> None:
    """Recursively reject any secret-bearing key anywhere in the artifact."""
    lname = name.lower()
    if any(tok in lname for tok in _SECRET_KEY_TOKENS):
        raise SchemaError(f"Disallowed secret-bearing field: {name}")
    if isinstance(value, dict):
        for k, v in value.items():
            _scan_secrets(str(k), v)
    elif isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, dict):
                for k, v in item.items():
                    _scan_secrets(str(k), v)


def _validate_no_secrets(artifact_dict: dict[str, Any]) -> None:
    # Top-level + recursive scan: secrets may hide inside open dict fields such
    # as agreed_terms or inside sub_game_results entries.
    for key, value in artifact_dict.items():
        _scan_secrets(str(key), value)


def _validate_game_uid(game_uid: str) -> None:
    if not isinstance(game_uid, str) or not game_uid:
        raise SchemaError("game_uid must be a non-empty string")


def _validate_game_id(game_id: str) -> None:
    if not isinstance(game_id, str) or not game_id:
        raise SchemaError("game_id must be a non-empty string")


def _validate_git_commit(git_commit: str) -> None:
    if not isinstance(git_commit, str) or not git_commit:
        raise SchemaError("git_commit must be a non-empty string")


def _validate_schema_version(schema_version: str) -> None:
    if schema_version != SCHEMA_VERSION:
        raise SchemaError(f"Invalid schema version: {schema_version}")


@dataclass
class Declaration:
    kind: str = "declaration"
    game_uid: str = ""
    schema_version: str = SCHEMA_VERSION
    team: str = ""
    role: str = ""
    members: list[str] = field(default_factory=list)
    police_repo_url: str = ""
    thief_repo_url: str = ""
    mcp_addresses: list[str] = field(default_factory=list)
    hardware: str = ""
    model: str = ""
    token_budget: int = 0
    start_time: str = ""
    end_time: str = ""
    num_games: int = 6

    def __post_init__(self):
        _validate_game_uid(self.game_uid)
        _validate_schema_version(self.schema_version)

    @property
    def artifact_id(self) -> str:
        return self.game_uid

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "game_uid": self.game_uid,
            "schema_version": self.schema_version,
            "team": self.team,
            "role": self.role,
            "members": self.members,
            "police_repo_url": self.police_repo_url,
            "thief_repo_url": self.thief_repo_url,
            "mcp_addresses": self.mcp_addresses,
            "hardware": self.hardware,
            "model": self.model,
            "token_budget": self.token_budget,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "num_games": self.num_games,
        }


@dataclass
class SubGameConfig:
    kind: str = "sub_game_config"
    game_uid: str = ""
    game_id: str = ""
    schema_version: str = SCHEMA_VERSION
    sub_game_index: int = 0
    role_for_this_sub_game: str = ""
    agreed_terms: dict[str, Any] = field(default_factory=dict)
    git_commit: str = ""

    def __post_init__(self):
        _validate_game_uid(self.game_uid)
        _validate_game_id(self.game_id)
        _validate_git_commit(self.git_commit)
        _validate_schema_version(self.schema_version)

    @property
    def artifact_id(self) -> str:
        return f"{self.game_uid}:{self.game_id}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "game_uid": self.game_uid,
            "game_id": self.game_id,
            "schema_version": self.schema_version,
            "sub_game_index": self.sub_game_index,
            "role_for_this_sub_game": self.role_for_this_sub_game,
            "agreed_terms": self.agreed_terms,
            "git_commit": self.git_commit,
        }


@dataclass
class SubGameLog:
    kind: str = "log"
    game_uid: str = ""
    game_id: str = ""
    schema_version: str = SCHEMA_VERSION
    steps: list[dict[str, Any]] = field(default_factory=list)
    finalized: bool = False
    signature: str | None = None

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "finalized", False):
            raise FinalizedLogMutationError(
                f"Cannot modify content field '{name}' of finalized log"
            )
        super().__setattr__(name, value)

    def __post_init__(self):
        _validate_game_uid(self.game_uid)
        _validate_game_id(self.game_id)
        _validate_schema_version(self.schema_version)

    @property
    def artifact_id(self) -> str:
        return f"{self.game_uid}:{self.game_id}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "game_uid": self.game_uid,
            "game_id": self.game_id,
            "schema_version": self.schema_version,
            "steps": self.steps,
            "finalized": self.finalized,
            "signature": self.signature,
        }


@dataclass
class SeriesResult:
    kind: str = "result"
    game_uid: str = ""
    schema_version: str = SCHEMA_VERSION
    sub_game_results: list[dict[str, Any]] = field(default_factory=list)
    total_police_score: int = 0
    total_thief_score: int = 0
    tie_applied: bool = False
    repo_links: dict[str, str] = field(default_factory=dict)
    total_llm_tokens_per_series: int = 0
    sub_game_git_commits: dict[str, str] = field(default_factory=dict)
    total_llm_tokens_per_sub_game: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        _validate_game_uid(self.game_uid)
        _validate_schema_version(self.schema_version)

    @property
    def artifact_id(self) -> str:
        return self.game_uid

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "game_uid": self.game_uid,
            "schema_version": self.schema_version,
            "sub_game_results": self.sub_game_results,
            "total_police_score": self.total_police_score,
            "total_thief_score": self.total_thief_score,
            "tie_applied": self.tie_applied,
            "repo_links": self.repo_links,
            "total_llm_tokens_per_series": self.total_llm_tokens_per_series,
            "sub_game_git_commits": self.sub_game_git_commits,
            "total_llm_tokens_per_sub_game": self.total_llm_tokens_per_sub_game,
        }


def build_declaration(
    *,
    game_uid: str,
    team: str,
    role: str,
    members: list[str],
    police_repo_url: str,
    thief_repo_url: str,
    mcp_addresses: list[str],
    hardware: str,
    model: str,
    token_budget: int,
    start_time: str,
    end_time: str,
    num_games: int = 6,
) -> Declaration:
    return Declaration(
        game_uid=game_uid,
        team=team,
        role=role,
        members=members,
        police_repo_url=police_repo_url,
        thief_repo_url=thief_repo_url,
        mcp_addresses=mcp_addresses,
        hardware=hardware,
        model=model,
        token_budget=token_budget,
        start_time=start_time,
        end_time=end_time,
        num_games=num_games,
    )


def build_sub_game_config(
    *,
    game_uid: str,
    game_id: str,
    sub_game_index: int,
    role_for_this_sub_game: str,
    agreed_terms: dict[str, Any],
    git_commit: str,
) -> SubGameConfig:
    return SubGameConfig(
        game_uid=game_uid,
        game_id=game_id,
        sub_game_index=sub_game_index,
        role_for_this_sub_game=role_for_this_sub_game,
        agreed_terms=agreed_terms,
        git_commit=git_commit,
    )


def build_sub_game_log(
    *, game_uid: str, game_id: str, steps: list[dict[str, Any]] | None = None
) -> SubGameLog:
    return SubGameLog(
        game_uid=game_uid,
        game_id=game_id,
        steps=steps or [],
    )


def build_series_result(
    *,
    game_uid: str,
    sub_game_results: list[dict[str, Any]],
    total_police_score: int,
    total_thief_score: int,
    tie_applied: bool,
    repo_links: dict[str, str],
    total_llm_tokens_per_series: int,
    sub_game_git_commits: dict[str, str] | None = None,
    total_llm_tokens_per_sub_game: dict[str, int] | None = None,
) -> SeriesResult:
    return SeriesResult(
        game_uid=game_uid,
        sub_game_results=sub_game_results,
        total_police_score=total_police_score,
        total_thief_score=total_thief_score,
        tie_applied=tie_applied,
        repo_links=repo_links,
        total_llm_tokens_per_series=total_llm_tokens_per_series,
        sub_game_git_commits=sub_game_git_commits or {},
        total_llm_tokens_per_sub_game=total_llm_tokens_per_sub_game or {},
    )


def assert_lifecycle_ok(artifact: Any, stage: str) -> None:
    stages = {"pre_series", "pre_sub_game", "during_sub_game", "post_settlement"}
    if stage not in stages:
        raise SchemaError(f"Invalid lifecycle stage: {stage}")

    if isinstance(artifact, Declaration):
        if stage != "pre_series":
            raise SchemaError("Declaration must be built at pre_series stage")
    elif isinstance(artifact, SubGameConfig):
        if stage != "pre_sub_game":
            raise SchemaError("SubGameConfig must be built at pre_sub_game stage")
    elif isinstance(artifact, SubGameLog):
        if stage not in ("pre_sub_game", "during_sub_game"):
            raise SchemaError("SubGameLog must be built at pre_sub_game or during_sub_game stage")
    elif isinstance(artifact, SeriesResult):
        if stage != "post_settlement":
            raise SchemaError("SeriesResult must be built at post_settlement stage")
    else:
        raise SchemaError(f"Unsupported artifact type for lifecycle check: {type(artifact).__name__}")


def validate_schema(artifact: Any) -> None:
    if not hasattr(artifact, "as_dict"):
        raise SchemaError(f"Artifact {type(artifact).__name__} does not have as_dict method")

    artifact_dict = artifact.as_dict()
    _validate_no_secrets(artifact_dict)

    if isinstance(artifact, Declaration):
        expected_types: dict[str, Any] = {
            "kind": str,
            "game_uid": str,
            "schema_version": str,
            "team": str,
            "role": str,
            "members": list,
            "police_repo_url": str,
            "thief_repo_url": str,
            "mcp_addresses": list,
            "hardware": str,
            "model": str,
            "token_budget": int,
            "start_time": str,
            "end_time": str,
            "num_games": int,
        }
        _validate_field_types(artifact_dict, expected_types)
        if not isinstance(artifact.num_games, int) or artifact.num_games < 0:
            raise SchemaError("num_games must be a non-negative integer")

    elif isinstance(artifact, SubGameConfig):
        expected_types = {
            "kind": str,
            "game_uid": str,
            "game_id": str,
            "schema_version": str,
            "sub_game_index": int,
            "role_for_this_sub_game": str,
            "agreed_terms": dict,
            "git_commit": str,
        }
        _validate_field_types(artifact_dict, expected_types)

    elif isinstance(artifact, SubGameLog):
        expected_types = {
            "kind": str,
            "game_uid": str,
            "game_id": str,
            "schema_version": str,
            "steps": list,
            "finalized": bool,
            "signature": (str, type(None)),
        }
        _validate_field_types(artifact_dict, expected_types)

    elif isinstance(artifact, SeriesResult):
        expected_types = {
            "kind": str,
            "game_uid": str,
            "schema_version": str,
            "sub_game_results": list,
            "total_police_score": int,
            "total_thief_score": int,
            "tie_applied": bool,
            "repo_links": dict,
            "total_llm_tokens_per_series": int,
            "sub_game_git_commits": dict,
            "total_llm_tokens_per_sub_game": dict,
        }
        _validate_field_types(artifact_dict, expected_types)
    else:
        raise SchemaError(f"Unsupported artifact type: {type(artifact).__name__}")


def validate_identifiers(*artifacts: Any) -> None:
    # All artifacts in one call must share the same series game_uid, and every
    # sub-game artifact (SubGameConfig/SubGameLog) must share the same game_id.
    # validate_identifiers validates ONE sub-game's artifact set at a time;
    # a multi-sub-game series is validated by calling it per sub-game.
    if not artifacts:
        return
    game_uids = {getattr(a, "game_uid", None) for a in artifacts}
    if len(game_uids) > 1:
        raise IdentifierMismatchError("Mismatched game_uid across artifacts")
    sub_game_ids = {
        getattr(a, "game_id", None)
        for a in artifacts
        if isinstance(a, (SubGameConfig, SubGameLog))
    }
    if len(sub_game_ids) > 1:
        raise IdentifierMismatchError("Mismatched game_id in sub-game artifacts")


def _get_signable_payload(artifact: Any) -> dict[str, Any]:
    payload = artifact.as_dict()
    if "signature" in payload:
        payload = dict(payload)
        payload["signature"] = None
    return payload


def sign_artifact(artifact: Any, signer: Callable[[bytes], str]) -> str:
    if signer is None:
        raise SignatureError("Signer cannot be None")
    payload = _get_signable_payload(artifact)
    data = canonical_bytes(payload)
    return signer(data)


def verify_artifact(
    artifact: Any, signature: str, verifier: Callable[[bytes, str], bool]
) -> bool:
    if verifier is None:
        raise SignatureError("Verifier cannot be None")
    if not isinstance(signature, str) or not signature:
        return False
    payload = _get_signable_payload(artifact)
    data = canonical_bytes(payload)
    return verifier(data, signature)


def finalize_log(log: SubGameLog, signer: Callable[[bytes], str]) -> SubGameLog:
    if log.finalized:
        raise FinalizedLogMutationError("Log already finalized")
    if signer is None:
        raise SignatureError("Signer cannot be None")
    # Mark as finalized first
    object.__setattr__(log, "finalized", True)
    # Sign over the finalized canonical payload (which now has finalized=True, signature=None)
    sig = sign_artifact(log, signer)
    object.__setattr__(log, "signature", sig)
    return log


def serialize(artifact: Any) -> bytes:
    return canonical_bytes(artifact.as_dict())


def artifact_filename(artifact: Any) -> str:
    """Return a deterministic INTERNAL filename for an artifact.

    INTERNAL CONTRACT — NOT OFFICIAL TEMPLATE CONFORMANCE. The four official
    REPORT-006 filenames are binding but gated on INPUT-001; this project-owned
    derivation is deterministic and replayable (same artifact -> same filename)
    and is replaced at the same boundary when official names arrive.
    """
    kind = getattr(artifact, "kind", "artifact")
    game_uid = getattr(artifact, "game_uid", "")
    game_id = getattr(artifact, "game_id", None)
    suffix = game_id if game_id else "series"
    return f"{kind}_{game_uid}_{suffix}.json"
