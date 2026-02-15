"""
Extractor Contract (v0.1) — placeholder.

This repo intentionally separates:
- Probabilistic extraction (Text -> JSON slots, UNKNOWN-by-default)
- Deterministic verification (Python code) producing PASS/BLOCK/ABSTAIN + reason codes

Boundaries:
- Research/evaluation tooling only. No clinical deployment.
- PASS != safe advice.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Protocol


class Extractor(Protocol):
    """Interface for any extractor backend (LLM, small model, etc.)."""

    def extract(self, dialogue: str, *, schema_version: str) -> Dict[str, Any]:
        """Return slots JSON conforming to the extractor contract schema."""
        raise NotImplementedError


@dataclass(frozen=True)
class ContractMeta:
    schema_version: str
    guideline_ref: str
    taxonomy_version: str
