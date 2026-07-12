from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable

import pytest

from core.evidence_match import (
    SLOT_SPECS,
    DialogueValidationIssue,
    EvidenceSlotResult,
    EvidenceSlotStatus,
    EvidenceVerificationResult,
    EvidenceVerificationState,
    verify_evidence,
)
from core.verifier import CRITICAL_AD_SLOTS, INSTABILITY_SLOTS


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


def find_slot(
    result: EvidenceVerificationResult, section: str, slot: str
) -> EvidenceSlotResult:
    return next(
        item
        for item in result.slot_results
        if item.section == section and item.slot == slot
    )


def issue_codes(result: EvidenceVerificationResult) -> tuple[str, ...]:
    return tuple(issue.code for issue in result.dialogue_issues)


def reverse_mapping_order(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: reverse_mapping_order(value[key])
            for key in reversed(tuple(value))
        }
    if isinstance(value, list):
        return [reverse_mapping_order(item) for item in value]
    return value


def test_invalid_contract_prevents_dialogue_inspection(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    del payload["audit"]

    result = verify_evidence(payload, object())

    assert result.state is EvidenceVerificationState.CONTRACT_INVALID
    assert result.contract_issues
    assert result.dialogue_issues == ()
    assert result.slot_results == ()


@pytest.mark.parametrize(
    ("dialogue", "expected_code"),
    (
        (None, "DIALOGUE_ROOT_NOT_LIST"),
        ([], "DIALOGUE_EMPTY"),
        (["turn"], "TURN_NOT_OBJECT"),
        ([{"text": "missing id"}], "TURN_ID_MISSING"),
        ([{"turn_id": True, "text": "boolean"}], "TURN_ID_INVALID"),
        ([{"turn_id": "0", "text": "string"}], "TURN_ID_INVALID"),
        ([{"turn_id": 0}], "TURN_TEXT_MISSING"),
        ([{"turn_id": 0, "text": 7}], "TURN_TEXT_INVALID"),
    ),
)
def test_dialogue_shape_failures(
    approved_cases: dict[str, dict[str, Any]],
    dialogue: object,
    expected_code: str,
) -> None:
    result = verify_evidence(payload_for(approved_cases), dialogue)

    assert result.state is EvidenceVerificationState.DIALOGUE_INVALID
    assert expected_code in issue_codes(result)
    assert result.slot_results == ()


def test_duplicate_turn_id_is_rejected(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    dialogue = dialogue_for(approved_cases)
    dialogue[1]["turn_id"] = dialogue[0]["turn_id"]

    result = verify_evidence(payload_for(approved_cases), dialogue)

    assert "TURN_ID_DUPLICATE" in issue_codes(result)


def test_duplicate_turn_id_is_rejected_even_when_first_text_is_invalid(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    dialogue = [
        {"turn_id": 1, "text": None},
        {"turn_id": 1, "text": "duplicate"},
    ]

    result = verify_evidence(payload_for(approved_cases), dialogue)

    assert "TURN_TEXT_INVALID" in issue_codes(result)
    assert "TURN_ID_DUPLICATE" in issue_codes(result)


def test_actual_turn_after_last_is_rejected(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    dialogue = dialogue_for(approved_cases)
    dialogue.append({"turn_id": 2, "text": "late turn"})

    result = verify_evidence(payload_for(approved_cases), dialogue)

    assert "TURN_AFTER_LAST" in issue_codes(result)
    assert "LAST_TURN_MISMATCH" in issue_codes(result)


def test_maximum_turn_id_must_equal_last_turn_id(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    dialogue = dialogue_for(approved_cases)[:1]

    result = verify_evidence(payload_for(approved_cases), dialogue)

    assert issue_codes(result) == ("LAST_TURN_MISMATCH",)


def test_non_contiguous_turn_ids_are_accepted(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "silence_001")
    dialogue = dialogue_for(approved_cases, "silence_001")
    dialogue.pop(1)

    result = verify_evidence(payload, dialogue)

    assert result.state is EvidenceVerificationState.COMPLETE


def test_dialogue_list_order_does_not_affect_valid_result(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    dialogue = dialogue_for(approved_cases)

    assert verify_evidence(payload, dialogue) == verify_evidence(
        payload, list(reversed(dialogue))
    )


@pytest.mark.parametrize(
    ("quote", "expected_status"),
    (
        ("built up gradually", EvidenceSlotStatus.GROUNDED_EXACT),
        ("BUILT UP GRADUALLY", EvidenceSlotStatus.GROUNDED_EXACT),
        ("built\tup\n gradually", EvidenceSlotStatus.GROUNDED_EXACT),
        ("pain—built", EvidenceSlotStatus.GROUNDED_EXACT),
    ),
)
def test_exact_normalization_rules(
    approved_cases: dict[str, dict[str, Any]],
    quote: str,
    expected_status: EvidenceSlotStatus,
) -> None:
    payload = payload_for(approved_cases)
    slot = CRITICAL_AD_SLOTS[0]
    payload["ad_gate"][slot]["evidence"]["quote_text"] = quote

    result = verify_evidence(payload, dialogue_for(approved_cases))

    assert find_slot(result, "ad_gate", slot).status is expected_status


def test_unicode_punctuation_is_replaced_with_space(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    slot = CRITICAL_AD_SLOTS[0]
    payload["ad_gate"][slot]["evidence"]["quote_text"] = "pain。built"

    result = verify_evidence(payload, dialogue_for(approved_cases))

    assert find_slot(result, "ad_gate", slot).status is EvidenceSlotStatus.GROUNDED_EXACT


def test_no_nfc_or_nfkc_normalization_is_applied(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    dialogue = dialogue_for(approved_cases)
    slot = CRITICAL_AD_SLOTS[0]
    payload["ad_gate"][slot]["evidence"]["quote_text"] = "café"
    dialogue[1]["text"] = "cafe\u0301"

    result = verify_evidence(payload, dialogue)

    matched = find_slot(result, "ad_gate", slot)
    assert matched.status is EvidenceSlotStatus.NOT_FOUND
    assert matched.score is None


def test_quote_found_only_in_another_turn_fails(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    dialogue = dialogue_for(approved_cases)
    slot = CRITICAL_AD_SLOTS[0]
    dialogue[0]["text"] += " anchorword"
    payload["ad_gate"][slot]["evidence"]["quote_text"] = "anchorword"
    payload["ad_gate"][slot]["evidence"]["source_turn_id"] = 1

    result = verify_evidence(payload, dialogue)

    assert find_slot(result, "ad_gate", slot).status is EvidenceSlotStatus.NOT_FOUND


@pytest.mark.parametrize("source_turn_id", (7, 99))
def test_nonexistent_anchored_turn_is_evidence_failure(
    approved_cases: dict[str, dict[str, Any]], source_turn_id: int
) -> None:
    payload = payload_for(approved_cases)
    slot = CRITICAL_AD_SLOTS[0]
    payload["ad_gate"][slot]["evidence"]["source_turn_id"] = source_turn_id

    result = verify_evidence(payload, dialogue_for(approved_cases))

    assert result.state is EvidenceVerificationState.COMPLETE
    matched = find_slot(result, "ad_gate", slot)
    assert matched.status is EvidenceSlotStatus.NOT_FOUND
    assert matched.source_turn_id == source_turn_id
    assert matched.score is None


def test_empty_normalized_quote_is_not_grounded(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    slot = CRITICAL_AD_SLOTS[0]
    payload["ad_gate"][slot]["evidence"]["quote_text"] = "...—!?"

    result = verify_evidence(payload, dialogue_for(approved_cases))

    matched = find_slot(result, "ad_gate", slot)
    assert matched.status is EvidenceSlotStatus.NOT_FOUND
    assert matched.score is None


def test_short_exact_quote_is_permitted(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    slot = INSTABILITY_SLOTS[0]
    payload["instability"][slot]["evidence"]["quote_text"] = "no"

    result = verify_evidence(payload, dialogue_for(approved_cases))

    assert find_slot(result, "instability", slot).status is EvidenceSlotStatus.GROUNDED_EXACT


@pytest.mark.parametrize("quote", ("pain no", "abcdefgh"))
def test_short_or_one_token_fuzzy_quote_is_disabled(
    approved_cases: dict[str, dict[str, Any]], quote: str
) -> None:
    payload = payload_for(approved_cases)
    dialogue = dialogue_for(approved_cases)
    slot = CRITICAL_AD_SLOTS[0]
    payload["ad_gate"][slot]["evidence"]["quote_text"] = quote
    dialogue[1]["text"] = "pain nx abcdefgi"

    result = verify_evidence(payload, dialogue)

    matched = find_slot(result, "ad_gate", slot)
    assert matched.status is EvidenceSlotStatus.NOT_FOUND
    assert matched.score is None


@pytest.mark.parametrize(
    ("section", "slot", "score", "expected_status"),
    (
        ("ad_gate", CRITICAL_AD_SLOTS[0], 90.1, EvidenceSlotStatus.GROUNDED_FUZZY),
        ("ad_gate", CRITICAL_AD_SLOTS[0], 89.9, EvidenceSlotStatus.NOT_FOUND),
        ("ad_gate", CRITICAL_AD_SLOTS[0], 90.0, EvidenceSlotStatus.GROUNDED_FUZZY),
        ("audit", "A1_focal_neuro_deficit", 85.0, EvidenceSlotStatus.GROUNDED_FUZZY),
    ),
)
def test_fuzzy_threshold_boundaries(
    approved_cases: dict[str, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
    section: str,
    slot: str,
    score: float,
    expected_status: EvidenceSlotStatus,
) -> None:
    payload = payload_for(approved_cases)
    dialogue = dialogue_for(approved_cases)
    source_turn_id = payload[section][slot]["evidence"]["source_turn_id"]
    payload[section][slot]["evidence"]["quote_text"] = "alpha bravo"
    next(turn for turn in dialogue if turn["turn_id"] == source_turn_id)[
        "text"
    ] = "charlie delta"

    def fixed_score(*args: object, **kwargs: object) -> float:
        assert kwargs == {"processor": None}
        return score

    monkeypatch.setattr("core.evidence_match.partial_ratio", fixed_score)
    result = verify_evidence(payload, dialogue)

    matched = find_slot(result, section, slot)
    assert matched.status is expected_status
    assert matched.score == score


def test_real_rapidfuzz_integration(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    slot = CRITICAL_AD_SLOTS[0]
    payload["ad_gate"][slot]["evidence"][
        "quote_text"
    ] = "The pain built up gradualy rather than being maximal at the start."

    result = verify_evidence(payload, dialogue_for(approved_cases))

    matched = find_slot(result, "ad_gate", slot)
    assert matched.status is EvidenceSlotStatus.GROUNDED_FUZZY
    assert matched.score is not None and matched.score >= 90


def test_confidence_does_not_change_result(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    high = payload_for(approved_cases)
    low = payload_for(approved_cases)
    slot = CRITICAL_AD_SLOTS[0]
    high["ad_gate"][slot]["evidence"]["confidence"] = "high"
    low["ad_gate"][slot]["evidence"]["confidence"] = "low"
    dialogue = dialogue_for(approved_cases)

    assert verify_evidence(high, dialogue) == verify_evidence(low, dialogue)


def test_every_unknown_slot_is_skipped(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    result = verify_evidence(
        payload_for(approved_cases, "silence_001"),
        dialogue_for(approved_cases, "silence_001"),
    )

    assert len(result.slot_results) == 11
    assert all(
        item.status is EvidenceSlotStatus.SKIPPED_UNKNOWN
        and item.source_turn_id is None
        and item.score is None
        for item in result.slot_results
    )


def test_all_slots_use_exact_canonical_order_and_thresholds(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    result = verify_evidence(
        payload_for(approved_cases), dialogue_for(approved_cases)
    )

    observed = tuple(
        (item.section, item.slot, item.threshold) for item in result.slot_results
    )
    assert observed == SLOT_SPECS
    assert all(item.threshold == 90 for item in result.slot_results[:10])
    assert result.slot_results[-1].threshold == 85


def test_runtime_and_audit_failure_properties(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    runtime_slot = CRITICAL_AD_SLOTS[0]
    audit_slot = "A1_focal_neuro_deficit"
    payload["ad_gate"][runtime_slot]["evidence"]["quote_text"] = "unsupported runtime"
    payload["audit"][audit_slot]["evidence"]["quote_text"] = "unsupported audit"

    result = verify_evidence(payload, dialogue_for(approved_cases))

    assert tuple(item.slot for item in result.runtime_failures) == (runtime_slot,)
    assert tuple(item.slot for item in result.audit_failures) == (audit_slot,)
    assert result.has_runtime_failure is True
    assert result.has_audit_failure is True


def test_inputs_are_not_mutated(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    dialogue = dialogue_for(approved_cases)
    before_payload = copy.deepcopy(payload)
    before_dialogue = copy.deepcopy(dialogue)

    verify_evidence(payload, dialogue)

    assert payload == before_payload
    assert dialogue == before_dialogue


def test_repeated_calls_and_dictionary_order_are_deterministic(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    dialogue = dialogue_for(approved_cases)
    first = verify_evidence(payload, dialogue)

    assert first == verify_evidence(payload, dialogue)
    assert first == verify_evidence(reverse_mapping_order(payload), dialogue)


def test_result_models_reject_inconsistent_values() -> None:
    with pytest.raises(ValueError):
        DialogueValidationIssue("UNKNOWN_CODE", ())
    with pytest.raises(TypeError):
        DialogueValidationIssue("DIALOGUE_EMPTY", [])  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        EvidenceSlotResult(
            section="ad_gate",
            slot="C1",
            value="YES",
            source_turn_id=0,
            threshold=90,
            status=EvidenceSlotStatus.GROUNDED_FUZZY,
            score=89.0,
        )
    with pytest.raises(ValueError):
        EvidenceVerificationResult(
            EvidenceVerificationState.COMPLETE,
            (),
            (),
            (),
        )
