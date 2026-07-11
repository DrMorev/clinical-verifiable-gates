"""Deterministic adjudication over schema-valid extractor contracts."""

from __future__ import annotations

from typing import Any, cast

from core.contract_validation import validate_contract
from core.result import AbstainMode, Decision, VerifierResult


RC_INSTABILITY_BYPASS = "RC_INSTABILITY_BYPASS"
RC_INSTABILITY_SLOT_MISSING = "RC_INSTABILITY_SLOT_MISSING"
RC_AD_RED_FLAG_PRESENT = "RC_AD_RED_FLAG_PRESENT"
RC_AD_CRITICAL_SLOT_MISSING = "RC_AD_CRITICAL_SLOT_MISSING"

INSTABILITY_SLOTS = (
    "syncope_or_collapse",
    "severe_respiratory_distress",
    "cyanosis_or_low_o2",
    "hypotension_or_shock_signs",
    "altered_mental_status",
    "acute_focal_neuro_deficit",
    "severe_pain_at_rest_with_diaphoresis_or_pallor",
)

CRITICAL_AD_SLOTS = (
    "C1_onset_maximal_at_start",
    "C2_back_interscapular_radiation",
    "C4_aortic_high_risk_history_any",
)


def adjudicate_contract(payload: object) -> VerifierResult:
    validation = validate_contract(payload)
    if not validation.is_valid:
        if validation.failure_result is None:  # pragma: no cover - model invariant
            raise RuntimeError("invalid contract is missing its failure result")
        return validation.failure_result

    contract = cast(dict[str, Any], payload)
    instability = cast(dict[str, dict[str, Any]], contract["instability"])
    ad_gate = cast(dict[str, dict[str, Any]], contract["ad_gate"])

    if any(
        instability[slot]["value"] in ("PRESENT", "POSSIBLE")
        for slot in INSTABILITY_SLOTS
    ):
        return VerifierResult(
            decision=Decision.ABSTAIN,
            reason_codes=(RC_INSTABILITY_BYPASS,),
            abstain_mode=AbstainMode.ESCALATE,
        )

    if any(ad_gate[slot]["value"] == "YES" for slot in CRITICAL_AD_SLOTS):
        return VerifierResult(
            decision=Decision.ABSTAIN,
            reason_codes=(RC_AD_RED_FLAG_PRESENT,),
            abstain_mode=AbstainMode.ESCALATE,
        )

    missing_reason_codes: list[str] = []
    if any(instability[slot]["value"] == "UNKNOWN" for slot in INSTABILITY_SLOTS):
        missing_reason_codes.append(RC_INSTABILITY_SLOT_MISSING)
    if any(ad_gate[slot]["value"] == "UNKNOWN" for slot in CRITICAL_AD_SLOTS):
        missing_reason_codes.append(RC_AD_CRITICAL_SLOT_MISSING)

    if missing_reason_codes:
        return VerifierResult(
            decision=Decision.ABSTAIN,
            reason_codes=tuple(missing_reason_codes),
            abstain_mode=AbstainMode.ASK_ONCE,
        )

    if all(
        instability[slot]["value"] == "ABSENT" for slot in INSTABILITY_SLOTS
    ) and all(ad_gate[slot]["value"] == "NO" for slot in CRITICAL_AD_SLOTS):
        return VerifierResult(decision=Decision.PASS, reason_codes=())

    raise RuntimeError("schema-valid contract contains an unsupported slot state")
