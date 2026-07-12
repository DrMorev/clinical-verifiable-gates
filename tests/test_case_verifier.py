from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from core.case_verifier import (
    RC_DIALOGUE_INVALID,
    RC_EVIDENCE_NOT_FOUND,
    CaseVerificationResult,
    verify_case,
)
from core.contract_validation import (
    RC_CONTRACT_MISSING_FIELDS,
    RC_CONTRACT_SCHEMA_INVALID,
)
from core.evidence_match import EvidenceVerificationState
from core.result import AbstainMode, Decision
from core.verifier import (
    CRITICAL_AD_SLOTS,
    INSTABILITY_SLOTS,
    RC_AD_CRITICAL_SLOT_MISSING,
    RC_AD_RED_FLAG_PRESENT,
    RC_INSTABILITY_BYPASS,
    RC_INSTABILITY_SLOT_MISSING,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPOSITORY_ROOT / "eval" / "data" / "ad_verdict_fixtures_v0.1.json"


@pytest.fixture(scope="module")
def approved_cases() -> dict[str, dict[str, Any]]:
    fixture_set = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {case["id"]: case for case in fixture_set["cases"]}


def payload_for(
    approved_cases: dict[str, dict[str, Any]], case_id: str = "pass_all_critical_no_001"
) -> dict[str, Any]:
    return copy.deepcopy(approved_cases[case_id]["extractor_output"])


def dialogue_for(
    approved_cases: dict[str, dict[str, Any]], case_id: str = "pass_all_critical_no_001"
) -> list[dict[str, Any]]:
    return copy.deepcopy(approved_cases[case_id]["dialogue"])


def set_instability_unknown(payload: dict[str, Any], slot: str) -> None:
    payload["instability"][slot] = {"value": "UNKNOWN", "evidence": None}


def set_ad_unknown(payload: dict[str, Any], slot: str) -> None:
    payload["ad_gate"][slot] = {"value": "UNKNOWN", "evidence": None}


def reverse_mapping_order(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: reverse_mapping_order(value[key])
            for key in reversed(tuple(value))
        }
    if isinstance(value, list):
        return [reverse_mapping_order(item) for item in value]
    return value


def test_contract_failure_precedes_malformed_dialogue(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    del payload["audit"]

    result = verify_case(payload, None)

    assert result.verdict.decision is Decision.BLOCK
    assert result.verdict.reason_codes == (RC_CONTRACT_MISSING_FIELDS,)
    assert result.evidence.state is EvidenceVerificationState.CONTRACT_INVALID


def test_multiple_contract_reason_order_is_unchanged(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    del payload["audit"]
    payload["ad_gate"][CRITICAL_AD_SLOTS[0]]["value"] = "MAYBE"

    result = verify_case(payload, None)

    assert result.verdict.reason_codes == (
        RC_CONTRACT_MISSING_FIELDS,
        RC_CONTRACT_SCHEMA_INVALID,
    )


def test_malformed_dialogue_produces_only_dialogue_invalid(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    result = verify_case(payload_for(approved_cases), [])

    assert result.verdict.decision is Decision.BLOCK
    assert result.verdict.abstain_mode is None
    assert result.verdict.reason_codes == (RC_DIALOGUE_INVALID,)
    assert result.evidence.state is EvidenceVerificationState.DIALOGUE_INVALID


@pytest.mark.parametrize(
    ("case_id", "decision", "mode", "codes"),
    (
        ("golden_001", Decision.ABSTAIN, AbstainMode.ESCALATE, (RC_AD_RED_FLAG_PRESENT,)),
        ("folk_001", Decision.ABSTAIN, AbstainMode.ESCALATE, (RC_AD_RED_FLAG_PRESENT,)),
        (
            "silence_001",
            Decision.ABSTAIN,
            AbstainMode.ASK_ONCE,
            (RC_INSTABILITY_SLOT_MISSING, RC_AD_CRITICAL_SLOT_MISSING),
        ),
        ("pass_all_critical_no_001", Decision.PASS, None, ()),
        (
            "instability_present_001",
            Decision.ABSTAIN,
            AbstainMode.ESCALATE,
            (RC_INSTABILITY_BYPASS,),
        ),
        (
            "instability_unknown_001",
            Decision.ABSTAIN,
            AbstainMode.ASK_ONCE,
            (RC_INSTABILITY_SLOT_MISSING,),
        ),
        (
            "contract_missing_fields_001",
            Decision.BLOCK,
            None,
            (RC_CONTRACT_MISSING_FIELDS,),
        ),
        (
            "contract_invalid_enum_001",
            Decision.BLOCK,
            None,
            (RC_CONTRACT_SCHEMA_INVALID,),
        ),
        (
            "hallucinated_critical_fill_001",
            Decision.ABSTAIN,
            AbstainMode.ESCALATE,
            (RC_AD_RED_FLAG_PRESENT,),
        ),
    ),
)
def test_all_nine_fixtures_have_explicit_runtime_execution(
    approved_cases: dict[str, dict[str, Any]],
    case_id: str,
    decision: Decision,
    mode: AbstainMode | None,
    codes: tuple[str, ...],
) -> None:
    case = approved_cases[case_id]
    result = verify_case(
        copy.deepcopy(case["extractor_output"]),
        copy.deepcopy(case["dialogue"]),
    )

    assert result.verdict.decision is decision
    assert result.verdict.abstain_mode is mode
    assert result.verdict.reason_codes == codes


def test_hallucinated_fixture_runtime_records_ungrounded_c1(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    result = verify_case(
        payload_for(approved_cases, "hallucinated_critical_fill_001"),
        dialogue_for(approved_cases, "hallucinated_critical_fill_001"),
    )

    assert result.verdict.reason_codes == (RC_AD_RED_FLAG_PRESENT,)
    assert tuple(item.slot for item in result.evidence.runtime_failures) == (
        CRITICAL_AD_SLOTS[0],
    )


def test_ungrounded_instability_escalation_remains_structural(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "instability_present_001")
    slot = INSTABILITY_SLOTS[0]
    payload["instability"][slot]["evidence"]["quote_text"] = "unsupported evidence"

    result = verify_case(
        payload, dialogue_for(approved_cases, "instability_present_001")
    )

    assert result.verdict.abstain_mode is AbstainMode.ESCALATE
    assert result.verdict.reason_codes == (RC_INSTABILITY_BYPASS,)
    assert result.evidence.has_runtime_failure is True


def test_ungrounded_critical_yes_escalation_remains_structural(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "golden_001")
    payload["ad_gate"][CRITICAL_AD_SLOTS[0]]["evidence"][
        "quote_text"
    ] = "unsupported evidence"

    result = verify_case(payload, dialogue_for(approved_cases, "golden_001"))

    assert result.verdict.abstain_mode is AbstainMode.ESCALATE
    assert result.verdict.reason_codes == (RC_AD_RED_FLAG_PRESENT,)
    assert result.evidence.has_runtime_failure is True


def test_pass_plus_runtime_failure_becomes_ask_once(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    payload["ad_gate"][CRITICAL_AD_SLOTS[0]]["evidence"][
        "quote_text"
    ] = "unsupported evidence"

    result = verify_case(payload, dialogue_for(approved_cases))

    assert result.verdict.decision is Decision.ABSTAIN
    assert result.verdict.abstain_mode is AbstainMode.ASK_ONCE
    assert result.verdict.reason_codes == (RC_EVIDENCE_NOT_FOUND,)


def test_instability_missingness_then_evidence_failure_order(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    set_instability_unknown(payload, INSTABILITY_SLOTS[0])
    payload["ad_gate"][CRITICAL_AD_SLOTS[0]]["evidence"][
        "quote_text"
    ] = "unsupported evidence"

    result = verify_case(payload, dialogue_for(approved_cases))

    assert result.verdict.reason_codes == (
        RC_INSTABILITY_SLOT_MISSING,
        RC_EVIDENCE_NOT_FOUND,
    )


def test_ad_missingness_then_evidence_failure_order(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    set_ad_unknown(payload, CRITICAL_AD_SLOTS[0])
    payload["instability"][INSTABILITY_SLOTS[0]]["evidence"][
        "quote_text"
    ] = "unsupported evidence"

    result = verify_case(payload, dialogue_for(approved_cases))

    assert result.verdict.reason_codes == (
        RC_AD_CRITICAL_SLOT_MISSING,
        RC_EVIDENCE_NOT_FOUND,
    )


def test_combined_missingness_then_evidence_failure_order(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    set_instability_unknown(payload, INSTABILITY_SLOTS[0])
    set_ad_unknown(payload, CRITICAL_AD_SLOTS[0])
    payload["ad_gate"][CRITICAL_AD_SLOTS[1]]["evidence"][
        "quote_text"
    ] = "unsupported evidence"

    result = verify_case(payload, dialogue_for(approved_cases))

    assert result.verdict.reason_codes == (
        RC_INSTABILITY_SLOT_MISSING,
        RC_AD_CRITICAL_SLOT_MISSING,
        RC_EVIDENCE_NOT_FOUND,
    )


def test_multiple_runtime_failures_deduplicate_verdict_code_but_not_report(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    payload["instability"][INSTABILITY_SLOTS[0]]["evidence"][
        "quote_text"
    ] = "unsupported instability"
    payload["ad_gate"][CRITICAL_AD_SLOTS[0]]["evidence"][
        "quote_text"
    ] = "unsupported ad"

    result = verify_case(payload, dialogue_for(approved_cases))

    assert result.verdict.reason_codes == (RC_EVIDENCE_NOT_FOUND,)
    assert tuple(
        (item.section, item.slot) for item in result.evidence.runtime_failures
    ) == (
        ("instability", INSTABILITY_SLOTS[0]),
        ("ad_gate", CRITICAL_AD_SLOTS[0]),
    )


def test_audit_only_failure_does_not_alter_pass(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    payload["audit"]["A1_focal_neuro_deficit"]["evidence"][
        "quote_text"
    ] = "unsupported audit"

    result = verify_case(payload, dialogue_for(approved_cases))

    assert result.verdict.decision is Decision.PASS
    assert result.verdict.reason_codes == ()
    assert result.evidence.has_audit_failure is True
    assert result.evidence.has_runtime_failure is False


def test_case_result_validates_field_types(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    valid = verify_case(payload_for(approved_cases), dialogue_for(approved_cases))
    with pytest.raises(TypeError):
        CaseVerificationResult("PASS", valid.evidence)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        CaseVerificationResult(valid.verdict, object())  # type: ignore[arg-type]


def test_inputs_are_not_mutated_and_repeated_calls_are_equal(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    dialogue = dialogue_for(approved_cases)
    before_payload = copy.deepcopy(payload)
    before_dialogue = copy.deepcopy(dialogue)

    first = verify_case(payload, dialogue)
    second = verify_case(payload, dialogue)

    assert first == second
    assert payload == before_payload
    assert dialogue == before_dialogue


def test_dictionary_and_dialogue_order_do_not_affect_output(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    dialogue = dialogue_for(approved_cases)

    assert verify_case(payload, dialogue) == verify_case(
        reverse_mapping_order(payload), list(reversed(dialogue))
    )
