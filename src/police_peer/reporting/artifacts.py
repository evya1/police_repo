from __future__ import annotations

from dataclasses import dataclass

from police_peer.reporting.schemas import (
    Declaration,
    SchemaError,
    SeriesResult,
    SubGameConfig,
    SubGameLog,
    artifact_filename,
    serialize,
    validate_identifiers,
    validate_schema,
)


@dataclass
class ReportingArtifactBundle:
    declaration: Declaration
    sub_game_configs: list[SubGameConfig]
    sub_game_logs: list[SubGameLog]
    series_result: SeriesResult

    def validate_bundle(self) -> None:
        if len(self.sub_game_configs) != 6:
            raise SchemaError(f"Bundle must contain exactly 6 sub-game configs, got {len(self.sub_game_configs)}")
        if len(self.sub_game_logs) != 6:
            raise SchemaError(f"Bundle must contain exactly 6 sub-game logs, got {len(self.sub_game_logs)}")

        # Validate declaration and result schemas
        validate_schema(self.declaration)
        validate_schema(self.series_result)

        # Validate identifiers across declaration and result
        validate_identifiers(self.declaration, self.series_result)

        # Validate each subgame pair
        for cfg, log in zip(self.sub_game_configs, self.sub_game_logs, strict=True):
            validate_schema(cfg)
            validate_schema(log)
            validate_identifiers(self.declaration, cfg, log, self.series_result)
            if not log.finalized:
                raise SchemaError(f"Sub-game log {log.game_id} must be finalized before report generation")

    def to_attachments(self) -> list[tuple[str, bytes]]:
        self.validate_bundle()
        attachments: list[tuple[str, bytes]] = []

        attachments.append((artifact_filename(self.declaration), serialize(self.declaration)))
        for cfg in self.sub_game_configs:
            attachments.append((artifact_filename(cfg), serialize(cfg)))
        for log in self.sub_game_logs:
            attachments.append((artifact_filename(log), serialize(log)))
        attachments.append((artifact_filename(self.series_result), serialize(self.series_result)))

        return attachments
