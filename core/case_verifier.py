"""High-level deterministic case verification over contract and dialogue."""

from __future__ import annotations

from dataclasses import dataclass

from core.contract_validation import validate_contract
from core.evidence_match import (
    EvidenceVerificationResult,
    EvidenceVerificationState,
    verify_evidence,
)
from core.result import AbstainMode, Decision, VerifierResult
from core.verifier import adjudicate_contract


RC_DIALOGUE_INVALID = "RC_DIALOGUE_INVALID"
RC_EVIDENCE_NOT_FOUND = "RC_EVIDENCE_NOT_FOUND"


@dataclass(frozen=True, slots=True)
class CaseVerificationResult:
    verdict: VerifierResult
    evidence: EvidenceVerificationResult

    def __post_init__(self) -> None:
        if not isinstance(self.verdict, VerifierResult):
            raise TypeError("verdict must be a VerifierResult")
        if not isinstance(self.evidence, EvidenceVerificationResult):
            raise TypeError("evidence must be an EvidenceVerificationResult")


def _complete_case(
    payload: object, evidence: EvidenceVerificationResult
) -> CaseVerificationResult:
    if evidence.state is not EvidenceVerificationState.COMPLETE:
        raise ValueError("complete case composition requires complete evidence")

    structural = adjudicate_contract(payload)
    if (
        structural.decision is Decision.ABSTAIN
        and structural.abstain_mode is AbstainMode.ESCALATE
    ):
        return CaseVerificationResult(verdict=structural, evidence=evidence)

    if not evidence.has_runtime_failure:
        return CaseVerificationResult(verdict=structural, evidence=evidence)

    if structural.decision is Decision.PASS:
        verdict = VerifierResult(
            decision=Decision.ABSTAIN,
            abstain_mode=AbstainMode.ASK_ONCE,
            reason_codes=(RC_EVIDENCE_NOT_FOUND,),
        )
    elif (
        structural.decision is Decision.ABSTAIN
        and structural.abstain_mode is AbstainMode.ASK_ONCE
    ):
        reason_codes = structural.reason_codes
        if RC_EVIDENCE_NOT_FOUND not in reason_codes:
            reason_codes += (RC_EVIDENCE_NOT_FOUND,)
        verdict = VerifierResult(
            decision=Decision.ABSTAIN,
            abstain_mode=AbstainMode.ASK_ONCE,
            reason_codes=reason_codes,
        )
    else:
        verdict = structural

    return CaseVerificationResult(verdict=verdict, evidence=evidence)


def verify_case(payload: object, dialogue: object) -> CaseVerificationResult:
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
        return CaseVerificationResult(
            verdict=validation.failure_result,
            evidence=evidence,
        )

    evidence = verify_evidence(payload, dialogue)
    if evidence.state is EvidenceVerificationState.DIALOGUE_INVALID:
        return CaseVerificationResult(
            verdict=VerifierResult(
                decision=Decision.BLOCK,
                reason_codes=(RC_DIALOGUE_INVALID,),
            ),
            evidence=evidence,
        )

    return _complete_case(payload, evidence)
