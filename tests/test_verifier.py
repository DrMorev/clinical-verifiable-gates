from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from core.contract_validation import (
    RC_CONTRACT_MISSING_FIELDS,
    RC_CONTRACT_SCHEMA_INVALID,
)
from core.result import AbstainMode, Decision, VerifierResult
from core.verifier import (
    CRITICAL_AD_SLOTS,
    INSTABILITY_SLOTS,
    RC_AD_CRITICAL_SLOT_MISSING,
    RC_AD_RED_FLAG_PRESENT,
    RC_INSTABILITY_BYPASS,
    RC_INSTABILITY_SLOT_MISSING,
    adjudicate_contract,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPOSITORY_ROOT / "eval" / "data" / "ad_verdict_fixtures_v0.1.json"

P3_EXECUTABLE_FIXTURE_IDS = (
    "golden_001",
    "folk_001",
    "silence_001",
    "pass_all_critical_no_001",
    "instability_present_001",
    "instability_unknown_001",
    "contract_missing_fields_001",
    "contract_invalid_enum_001",
)
DEFERRED_EVIDENCE_FIXTURE_ID = "hallucinated_critical_fill_001"


@pytest.fixture(scope="module")
def approved_cases() -> dict[str, dict[str, Any]]:
    fixture_set = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {case["id"]: case for case in fixture_set["cases"]}


def payload_for(
    approved_cases: dict[str, dict[str, Any]], case_id: str
) -> dict[str, Any]:
    return copy.deepcopy(approved_cases[case_id]["extractor_output"])


def pass_payload(approved_cases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return payload_for(approved_cases, "pass_all_critical_no_001")


def set_instability_value(
    payload: dict[str, Any], slot: str, value: str
) -> None:
    payload["instability"][slot]["value"] = value
    if value == "UNKNOWN":
        payload["instability"][slot]["evidence"] = None


def set_critical_value(payload: dict[str, Any], slot: str, value: str) -> None:
    payload["ad_gate"][slot]["value"] = value
    if value == "UNKNOWN":
        payload["ad_gate"][slot]["evidence"] = None


def assert_result(
    result: VerifierResult,
    decision: Decision,
    abstain_mode: AbstainMode | None,
    reason_codes: tuple[str, ...],
) -> None:
    assert result.decision is decision
    assert result.abstain_mode is abstain_mode
    assert result.reason_codes == reason_codes


def assert_escalation(result: VerifierResult, reason_code: str) -> None:
    assert_result(
        result,
        Decision.ABSTAIN,
        AbstainMode.ESCALATE,
        (reason_code,),
    )


def assert_ask_once(
    result: VerifierResult, reason_codes: tuple[str, ...]
) -> None:
    assert_result(
        result,
        Decision.ABSTAIN,
        AbstainMode.ASK_ONCE,
        reason_codes,
    )


def reverse_mapping_order(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: reverse_mapping_order(value[key])
            for key in reversed(tuple(value))
        }
    if isinstance(value, list):
        return [reverse_mapping_order(item) for item in value]
    return value


def test_fixture_roster_has_exactly_one_deferred_evidence_case(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    assert len(approved_cases) == 9
    assert set(P3_EXECUTABLE_FIXTURE_IDS) == (
        set(approved_cases) - {DEFERRED_EVIDENCE_FIXTURE_ID}
    )
    assert DEFERRED_EVIDENCE_FIXTURE_ID not in P3_EXECUTABLE_FIXTURE_IDS


@pytest.mark.parametrize("case_id", P3_EXECUTABLE_FIXTURE_IDS)
def test_p3_fixture_regression_matches_approved_expected_result(
    approved_cases: dict[str, dict[str, Any]], case_id: str
) -> None:
    case = approved_cases[case_id]
    expected = case["expected"]
    expected_mode = (
        None
        if expected["abstain_mode"] is None
        else AbstainMode(expected["abstain_mode"])
    )

    result = adjudicate_contract(copy.deepcopy(case["extractor_output"]))

    assert_result(
        result,
        Decision(expected["decision"]),
        expected_mode,
        tuple(expected["reason_codes"]),
    )


def test_missing_field_fixture_returns_existing_contract_block(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    result = adjudicate_contract(
        payload_for(approved_cases, "contract_missing_fields_001")
    )

    assert_result(
        result,
        Decision.BLOCK,
        None,
        (RC_CONTRACT_MISSING_FIELDS,),
    )


def test_invalid_enum_fixture_returns_existing_contract_block(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    result = adjudicate_contract(
        payload_for(approved_cases, "contract_invalid_enum_001")
    )

    assert_result(
        result,
        Decision.BLOCK,
        None,
        (RC_CONTRACT_SCHEMA_INVALID,),
    )


def test_malformed_contract_with_apparent_triggers_still_returns_contract_block(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = pass_payload(approved_cases)
    del payload["audit"]
    set_instability_value(payload, INSTABILITY_SLOTS[0], "PRESENT")
    set_critical_value(payload, CRITICAL_AD_SLOTS[0], "YES")

    result = adjudicate_contract(payload)

    assert_result(
        result,
        Decision.BLOCK,
        None,
        (RC_CONTRACT_MISSING_FIELDS,),
    )


def test_non_object_root_returns_contract_block() -> None:
    result = adjudicate_contract([])

    assert_result(
        result,
        Decision.BLOCK,
        None,
        (RC_CONTRACT_SCHEMA_INVALID,),
    )


def test_contract_reason_code_order_remains_unchanged(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = pass_payload(approved_cases)
    del payload["audit"]
    payload["ad_gate"][CRITICAL_AD_SLOTS[0]]["value"] = "MAYBE"

    result = adjudicate_contract(payload)

    assert_result(
        result,
        Decision.BLOCK,
        None,
        (RC_CONTRACT_MISSING_FIELDS, RC_CONTRACT_SCHEMA_INVALID),
    )


@pytest.mark.parametrize("slot", INSTABILITY_SLOTS)
@pytest.mark.parametrize("value", ("PRESENT", "POSSIBLE"))
def test_each_instability_bypass_value_escalates(
    approved_cases: dict[str, dict[str, Any]], slot: str, value: str
) -> None:
    payload = pass_payload(approved_cases)
    set_instability_value(payload, slot, value)

    assert_escalation(adjudicate_contract(payload), RC_INSTABILITY_BYPASS)


def test_multiple_instability_bypass_slots_return_one_reason_code(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = pass_payload(approved_cases)
    set_instability_value(payload, INSTABILITY_SLOTS[0], "PRESENT")
    set_instability_value(payload, INSTABILITY_SLOTS[1], "POSSIBLE")

    assert_escalation(adjudicate_contract(payload), RC_INSTABILITY_BYPASS)


def test_instability_bypass_overrides_critical_ad_yes(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = pass_payload(approved_cases)
    set_instability_value(payload, INSTABILITY_SLOTS[0], "PRESENT")
    set_critical_value(payload, CRITICAL_AD_SLOTS[0], "YES")

    assert_escalation(adjudicate_contract(payload), RC_INSTABILITY_BYPASS)


def test_instability_bypass_overrides_instability_unknown(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = pass_payload(approved_cases)
    set_instability_value(payload, INSTABILITY_SLOTS[0], "PRESENT")
    set_instability_value(payload, INSTABILITY_SLOTS[1], "UNKNOWN")

    assert_escalation(adjudicate_contract(payload), RC_INSTABILITY_BYPASS)


def test_instability_bypass_overrides_critical_ad_unknown(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = pass_payload(approved_cases)
    set_instability_value(payload, INSTABILITY_SLOTS[0], "POSSIBLE")
    set_critical_value(payload, CRITICAL_AD_SLOTS[0], "UNKNOWN")

    assert_escalation(adjudicate_contract(payload), RC_INSTABILITY_BYPASS)


@pytest.mark.parametrize("slot", CRITICAL_AD_SLOTS)
def test_each_critical_ad_yes_escalates(
    approved_cases: dict[str, dict[str, Any]], slot: str
) -> None:
    payload = pass_payload(approved_cases)
    set_critical_value(payload, slot, "YES")

    assert_escalation(adjudicate_contract(payload), RC_AD_RED_FLAG_PRESENT)


def test_multiple_critical_ad_yes_values_return_one_reason_code(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = pass_payload(approved_cases)
    set_critical_value(payload, CRITICAL_AD_SLOTS[0], "YES")
    set_critical_value(payload, CRITICAL_AD_SLOTS[1], "YES")

    assert_escalation(adjudicate_contract(payload), RC_AD_RED_FLAG_PRESENT)


def test_critical_ad_yes_overrides_instability_missingness(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = pass_payload(approved_cases)
    set_instability_value(payload, INSTABILITY_SLOTS[0], "UNKNOWN")
    set_critical_value(payload, CRITICAL_AD_SLOTS[0], "YES")

    assert_escalation(adjudicate_contract(payload), RC_AD_RED_FLAG_PRESENT)


def test_critical_ad_yes_overrides_critical_ad_missingness(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = pass_payload(approved_cases)
    set_critical_value(payload, CRITICAL_AD_SLOTS[0], "YES")
    set_critical_value(payload, CRITICAL_AD_SLOTS[1], "UNKNOWN")

    assert_escalation(adjudicate_contract(payload), RC_AD_RED_FLAG_PRESENT)


@pytest.mark.parametrize("slot", INSTABILITY_SLOTS)
def test_each_instability_unknown_asks_once(
    approved_cases: dict[str, dict[str, Any]], slot: str
) -> None:
    payload = pass_payload(approved_cases)
    set_instability_value(payload, slot, "UNKNOWN")

    assert_ask_once(
        adjudicate_contract(payload),
        (RC_INSTABILITY_SLOT_MISSING,),
    )


def test_multiple_instability_unknown_values_return_one_reason_code(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = pass_payload(approved_cases)
    set_instability_value(payload, INSTABILITY_SLOTS[0], "UNKNOWN")
    set_instability_value(payload, INSTABILITY_SLOTS[1], "UNKNOWN")

    assert_ask_once(
        adjudicate_contract(payload),
        (RC_INSTABILITY_SLOT_MISSING,),
    )


@pytest.mark.parametrize("slot", CRITICAL_AD_SLOTS)
def test_each_critical_ad_unknown_asks_once(
    approved_cases: dict[str, dict[str, Any]], slot: str
) -> None:
    payload = pass_payload(approved_cases)
    set_critical_value(payload, slot, "UNKNOWN")

    assert_ask_once(
        adjudicate_contract(payload),
        (RC_AD_CRITICAL_SLOT_MISSING,),
    )


def test_multiple_critical_ad_unknown_values_return_one_reason_code(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = pass_payload(approved_cases)
    set_critical_value(payload, CRITICAL_AD_SLOTS[0], "UNKNOWN")
    set_critical_value(payload, CRITICAL_AD_SLOTS[1], "UNKNOWN")

    assert_ask_once(
        adjudicate_contract(payload),
        (RC_AD_CRITICAL_SLOT_MISSING,),
    )


def test_combined_missingness_uses_canonical_reason_code_order(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = pass_payload(approved_cases)
    set_instability_value(payload, INSTABILITY_SLOTS[-1], "UNKNOWN")
    set_critical_value(payload, CRITICAL_AD_SLOTS[0], "UNKNOWN")

    assert_ask_once(
        adjudicate_contract(payload),
        (
            RC_INSTABILITY_SLOT_MISSING,
            RC_AD_CRITICAL_SLOT_MISSING,
        ),
    )


def test_approved_pass_control_returns_pass(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    result = adjudicate_contract(pass_payload(approved_cases))

    assert_result(result, Decision.PASS, None, ())


def test_audit_unknown_does_not_prevent_pass(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = pass_payload(approved_cases)
    payload["audit"]["A1_focal_neuro_deficit"] = {
        "value": "UNKNOWN",
        "evidence": None,
    }

    assert_result(adjudicate_contract(payload), Decision.PASS, None, ())


def test_input_dictionary_order_does_not_affect_output(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = pass_payload(approved_cases)
    reordered = reverse_mapping_order(payload)

    assert adjudicate_contract(payload) == adjudicate_contract(reordered)


def test_repeated_adjudication_gives_equivalent_results(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "silence_001")

    assert adjudicate_contract(payload) == adjudicate_contract(payload)


def test_serialized_results_are_byte_for_byte_deterministic(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "silence_001")

    first = adjudicate_contract(payload).to_json().encode("utf-8")
    second = adjudicate_contract(payload).to_json().encode("utf-8")

    assert first == second


def test_adjudication_does_not_mutate_input(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "golden_001")
    before = copy.deepcopy(payload)

    adjudicate_contract(payload)

    assert payload == before
