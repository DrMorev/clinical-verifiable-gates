from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from core.contract_validation import (
    RC_CONTRACT_MISSING_FIELDS,
    RC_CONTRACT_SCHEMA_INVALID,
    ContractValidationResult,
    validate_contract,
)
from core.result import Decision


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPOSITORY_ROOT / "eval" / "data" / "ad_verdict_fixtures_v0.1.json"
STRUCTURALLY_VALID_IDS = (
    "golden_001",
    "folk_001",
    "silence_001",
    "pass_all_critical_no_001",
    "instability_present_001",
    "hallucinated_critical_fill_001",
)


@pytest.fixture(scope="module")
def approved_cases() -> dict[str, dict[str, Any]]:
    fixture_set = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {case["id"]: case for case in fixture_set["cases"]}


def payload_for(
    approved_cases: dict[str, dict[str, Any]], case_id: str
) -> dict[str, Any]:
    return copy.deepcopy(approved_cases[case_id]["extractor_output"])


def assert_valid(result: ContractValidationResult) -> None:
    assert result.is_valid is True
    assert result.issues == ()
    assert result.failure_result is None


def assert_blocked(
    result: ContractValidationResult, expected_codes: tuple[str, ...]
) -> None:
    assert result.is_valid is False
    assert result.issues
    assert result.failure_result is not None
    assert result.failure_result.decision is Decision.BLOCK
    assert result.failure_result.abstain_mode is None
    assert result.failure_result.reason_codes == expected_codes


def test_valid_approved_fixture_is_accepted(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    assert_valid(validate_contract(payload_for(approved_cases, "golden_001")))


@pytest.mark.parametrize("case_id", STRUCTURALLY_VALID_IDS)
def test_all_six_structurally_valid_fixtures_are_accepted(
    approved_cases: dict[str, dict[str, Any]], case_id: str
) -> None:
    assert_valid(validate_contract(payload_for(approved_cases, case_id)))


@pytest.mark.parametrize(
    ("case_id", "expected_codes"),
    (
        ("contract_missing_fields_001", (RC_CONTRACT_MISSING_FIELDS,)),
        ("contract_invalid_enum_001", (RC_CONTRACT_SCHEMA_INVALID,)),
    ),
)
def test_intentionally_invalid_fixtures_map_to_approved_failures(
    approved_cases: dict[str, dict[str, Any]],
    case_id: str,
    expected_codes: tuple[str, ...],
) -> None:
    assert_blocked(
        validate_contract(payload_for(approved_cases, case_id)),
        expected_codes,
    )


def test_missing_top_level_section(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "golden_001")
    del payload["audit"]

    result = validate_contract(payload)

    assert_blocked(result, (RC_CONTRACT_MISSING_FIELDS,))
    assert any(issue.instance_path == () and issue.validator == "required" for issue in result.issues)


def test_missing_required_metadata_field(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "golden_001")
    del payload["meta"]["schema_version"]

    result = validate_contract(payload)

    assert_blocked(result, (RC_CONTRACT_MISSING_FIELDS,))
    assert any(
        issue.instance_path == ("meta",) and issue.validator == "required"
        for issue in result.issues
    )


def test_unexpected_top_level_property(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "golden_001")
    payload["unexpected"] = True

    result = validate_contract(payload)

    assert_blocked(result, (RC_CONTRACT_SCHEMA_INVALID,))
    assert any(issue.validator == "additionalProperties" for issue in result.issues)


def test_unexpected_nested_property(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "golden_001")
    payload["meta"]["unexpected"] = True

    result = validate_contract(payload)

    assert_blocked(result, (RC_CONTRACT_SCHEMA_INVALID,))
    assert any(
        issue.instance_path == ("meta",)
        and issue.validator == "additionalProperties"
        for issue in result.issues
    )


def test_illegal_gating_enum(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "golden_001")
    payload["ad_gate"]["C1_onset_maximal_at_start"]["value"] = "MAYBE"

    result = validate_contract(payload)

    assert_blocked(result, (RC_CONTRACT_SCHEMA_INVALID,))
    assert any(issue.validator == "enum" for issue in result.issues)


def test_illegal_instability_enum(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "golden_001")
    payload["instability"]["syncope_or_collapse"]["value"] = "MAYBE"

    result = validate_contract(payload)

    assert_blocked(result, (RC_CONTRACT_SCHEMA_INVALID,))
    assert any(issue.validator == "enum" for issue in result.issues)


def test_non_unknown_gating_slot_without_evidence(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "pass_all_critical_no_001")
    payload["ad_gate"]["C1_onset_maximal_at_start"]["evidence"] = None

    result = validate_contract(payload)

    assert_blocked(result, (RC_CONTRACT_SCHEMA_INVALID,))
    assert any(issue.validator == "type" for issue in result.issues)


def test_non_unknown_instability_slot_without_evidence(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "pass_all_critical_no_001")
    payload["instability"]["syncope_or_collapse"]["evidence"] = None

    result = validate_contract(payload)

    assert_blocked(result, (RC_CONTRACT_SCHEMA_INVALID,))
    assert any(issue.validator == "type" for issue in result.issues)


def test_unknown_gating_slot_with_non_null_evidence(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "silence_001")
    payload["ad_gate"]["C1_onset_maximal_at_start"]["evidence"] = {
        "source_turn_id": 0,
        "quote_text": "Chest hurts.",
        "confidence": "high",
    }

    result = validate_contract(payload)

    assert_blocked(result, (RC_CONTRACT_SCHEMA_INVALID,))
    assert any(issue.validator == "type" for issue in result.issues)


def test_unknown_instability_slot_with_non_null_evidence(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "silence_001")
    payload["instability"]["syncope_or_collapse"]["evidence"] = {
        "source_turn_id": 0,
        "quote_text": "Chest hurts.",
        "confidence": "high",
    }

    result = validate_contract(payload)

    assert_blocked(result, (RC_CONTRACT_SCHEMA_INVALID,))
    assert any(issue.validator == "type" for issue in result.issues)


def test_empty_quote_text(approved_cases: dict[str, dict[str, Any]]) -> None:
    payload = payload_for(approved_cases, "pass_all_critical_no_001")
    payload["ad_gate"]["C1_onset_maximal_at_start"]["evidence"][
        "quote_text"
    ] = ""

    result = validate_contract(payload)

    assert_blocked(result, (RC_CONTRACT_SCHEMA_INVALID,))
    assert any(issue.validator == "minLength" for issue in result.issues)


def test_negative_source_turn_id(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "pass_all_critical_no_001")
    payload["ad_gate"]["C1_onset_maximal_at_start"]["evidence"][
        "source_turn_id"
    ] = -1

    result = validate_contract(payload)

    assert_blocked(result, (RC_CONTRACT_SCHEMA_INVALID,))
    assert any(issue.validator == "minimum" for issue in result.issues)


def test_malformed_evidence_object(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "pass_all_critical_no_001")
    payload["ad_gate"]["C1_onset_maximal_at_start"]["evidence"] = {
        "source_turn_id": 0
    }

    result = validate_contract(payload)

    assert result.is_valid is False
    assert result.failure_result is not None
    assert result.failure_result.decision is Decision.BLOCK
    assert any(issue.validator == "required" for issue in result.issues)


def test_non_object_root_input() -> None:
    result = validate_contract([])

    assert_blocked(result, (RC_CONTRACT_SCHEMA_INVALID,))
    assert result.issues[0].instance_path == ()
    assert result.issues[0].validator == "type"


def test_combined_missing_and_schema_invalid_failures(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "golden_001")
    del payload["audit"]
    payload["ad_gate"]["C1_onset_maximal_at_start"]["value"] = "MAYBE"

    result = validate_contract(payload)

    assert_blocked(
        result,
        (RC_CONTRACT_MISSING_FIELDS, RC_CONTRACT_SCHEMA_INVALID),
    )


def test_validation_issue_order_is_deterministic(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    first_payload = payload_for(approved_cases, "golden_001")
    first_payload["unexpected"] = True
    first_payload["meta"]["unexpected"] = True
    first_payload["ad_gate"]["C1_onset_maximal_at_start"]["value"] = "MAYBE"

    second_payload = payload_for(approved_cases, "golden_001")
    second_payload["ad_gate"]["C1_onset_maximal_at_start"]["value"] = "MAYBE"
    second_payload["meta"]["unexpected"] = True
    second_payload["unexpected"] = True

    first = validate_contract(first_payload)
    second = validate_contract(second_payload)

    assert first.issues == second.issues
    stable_fields = [
        (issue.instance_path, issue.validator, issue.schema_path)
        for issue in first.issues
    ]
    assert stable_fields == [
        (issue.instance_path, issue.validator, issue.schema_path)
        for issue in second.issues
    ]


def test_reason_code_order_is_deterministic(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "golden_001")
    payload["ad_gate"]["C1_onset_maximal_at_start"]["value"] = "MAYBE"
    del payload["audit"]

    result = validate_contract(payload)

    assert result.failure_result is not None
    assert result.failure_result.reason_codes == (
        RC_CONTRACT_MISSING_FIELDS,
        RC_CONTRACT_SCHEMA_INVALID,
    )


def test_validator_does_not_mutate_input(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "golden_001")
    before = copy.deepcopy(payload)

    validate_contract(payload)

    assert payload == before


def test_repeated_validation_gives_equivalent_results(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "contract_invalid_enum_001")

    assert validate_contract(payload) == validate_contract(payload)
