"""Deterministic verifier result types."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


DEFAULT_SCHEMA_REF = "core/schemas/ad_extractor_contract_v0.1.schema.json"
DEFAULT_TAXONOMY_VERSION = "v0.1"


class Decision(str, Enum):
    PASS = "PASS"
    BLOCK = "BLOCK"
    ABSTAIN = "ABSTAIN"


class AbstainMode(str, Enum):
    ASK_ONCE = "ASK_ONCE"
    ESCALATE = "ESCALATE"


@dataclass(frozen=True, slots=True)
class VerifierResult:
    decision: Decision
    reason_codes: tuple[str, ...]
    abstain_mode: AbstainMode | None = None
    schema_ref: str = DEFAULT_SCHEMA_REF
    taxonomy_version: str = DEFAULT_TAXONOMY_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.decision, Decision):
            raise TypeError("decision must be a Decision enum value")
        if type(self.reason_codes) is not tuple:
            raise TypeError("reason_codes must be a tuple")
        if any(type(code) is not str or not code for code in self.reason_codes):
            raise ValueError("reason_codes must contain non-empty strings")
        if self.abstain_mode is not None and not isinstance(
            self.abstain_mode, AbstainMode
        ):
            raise TypeError("abstain_mode must be an AbstainMode enum value or None")
        if self.schema_ref != DEFAULT_SCHEMA_REF:
            raise ValueError(f"schema_ref must be {DEFAULT_SCHEMA_REF!r}")
        if self.taxonomy_version != DEFAULT_TAXONOMY_VERSION:
            raise ValueError(
                f"taxonomy_version must be {DEFAULT_TAXONOMY_VERSION!r}"
            )

        if self.decision is Decision.ABSTAIN:
            if self.abstain_mode is None:
                raise ValueError("ABSTAIN requires an abstain mode")
            if not self.reason_codes:
                raise ValueError("ABSTAIN requires at least one reason code")
        else:
            if self.abstain_mode is not None:
                raise ValueError("PASS and BLOCK require abstain_mode=None")
            if self.decision is Decision.BLOCK and not self.reason_codes:
                raise ValueError("BLOCK requires at least one reason code")

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason_codes": list(self.reason_codes),
            "abstain_mode": (
                self.abstain_mode.value if self.abstain_mode is not None else None
            ),
            "schema_ref": self.schema_ref,
            "taxonomy_version": self.taxonomy_version,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
        )
