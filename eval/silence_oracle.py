"""Evaluation-only trusted Silence-oracle adjudication."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from core.case_verifier import (
    RC_DIALOGUE_INVALID,
    CaseVerificationResult,
    _complete_case,
)
from core.contract_validation import validate_contract
from core.evidence_match import (
    EvidenceVerificationResult,
    EvidenceVerificationState,
    verify_evidence,
)
from core.result import Decision, VerifierResult
from core.verifier import CRITICAL_AD_SLOTS


RC_HALLUCINATED_CRITICAL_FILL = "RC_HALLUCINATED_CRITICAL_FILL"


@dataclass(frozen=True, slots=True)
class SilenceOracleContext:
    unsupported_critical_slots: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.unsupported_critical_slots) is not tuple:
            raise TypeError("unsupported_critical_slots must be a tuple")
        if any(
            type(slot) is not str or slot not in CRITICAL_AD_SLOTS
            for slot in self.unsupported_critical_slots
        ):
            raise ValueError("oracle slots must be canonical critical AD slots")
        if len(set(self.unsupported_critical_slots)) != len(
            self.unsupported_critical_slots
        ):
            raise ValueError("oracle slots cannot contain duplicates")
        canonical = tuple(
            slot
            for slot in CRITICAL_AD_SLOTS
            if slot in self.unsupported_critical_slots
        )
        if self.unsupported_critical_slots != canonical:
            raise ValueError("oracle slots must be in canonical order")


def evaluate_silence_case(
    payload: object,
    dialogue: object,
    oracle: SilenceOracleContext,
) -> CaseVerificationResult:
    if not isinstance(oracle, SilenceOracleContext):
        raise TypeError("oracle must be a SilenceOracleContext")

    validation = validate_contract(payload)
    if not validation.is_valid:
        if validation.failure_result is None:  # pragma: no cover - model invariant
            raise RuntimeError("invalid contract is missing its failure result")
        evidence = EvidenceVerificationResult(
            state=EvidenceVerificationState.CONTRACT_INVALID,
            contract_issues=validation.issues,
            dialogue_issues=(),
            slot_results=(),
        )
        return CaseVerificationResult(validation.failure_result, evidence)

    evidence = verify_evidence(payload, dialogue)
    if evidence.state is EvidenceVerificationState.DIALOGUE_INVALID:
        return CaseVerificationResult(
            VerifierResult(
                decision=Decision.BLOCK,
                reason_codes=(RC_DIALOGUE_INVALID,),
            ),
            evidence,
        )

    contract = cast(dict[str, Any], payload)
    if any(
        contract["ad_gate"][slot]["value"] != "UNKNOWN"
        for slot in oracle.unsupported_critical_slots
    ):
        return CaseVerificationResult(
            VerifierResult(
                decision=Decision.BLOCK,
                reason_codes=(RC_HALLUCINATED_CRITICAL_FILL,),
            ),
            evidence,
        )

    return _complete_case(payload, evidence)
