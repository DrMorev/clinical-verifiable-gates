from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from core.case_verifier import RC_DIALOGUE_INVALID, verify_case
from core.contract_validation import RC_CONTRACT_MISSING_FIELDS
from core.evidence_match import EvidenceVerificationState, verify_evidence
from core.result import AbstainMode, Decision
from core.verifier import CRITICAL_AD_SLOTS, RC_AD_RED_FLAG_PRESENT
from eval.silence_oracle import (
    RC_HALLUCINATED_CRITICAL_FILL,
    SilenceOracleContext,
    evaluate_silence_case,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPOSITORY_ROOT / "eval" / "data" / "ad_verdict_fixtures_v0.1.json"


@pytest.fixture(scope="module")
def approved_cases() -> dict[str, dict[str, Any]]:
    fixture_set = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {case["id"]: case for case in fixture_set["cases"]}


def payload_for(
    approved_cases: dict[str, dict[str, Any]],
    case_id: str = "hallucinated_critical_fill_001",
) -> dict[str, Any]:
    return copy.deepcopy(approved_cases[case_id]["extractor_output"])


def dialogue_for(
    approved_cases: dict[str, dict[str, Any]],
    case_id: str = "hallucinated_critical_fill_001",
) -> list[dict[str, Any]]:
    return copy.deepcopy(approved_cases[case_id]["dialogue"])


def c1_oracle() -> SilenceOracleContext:
    return SilenceOracleContext((CRITICAL_AD_SLOTS[0],))


def test_context_rejects_non_tuple() -> None:
    with pytest.raises(TypeError):
        SilenceOracleContext([CRITICAL_AD_SLOTS[0]])  # type: ignore[arg-type]


def test_context_rejects_unknown_slot() -> None:
    with pytest.raises(ValueError):
        SilenceOracleContext(("unknown_slot",))


def test_context_rejects_duplicate_slot() -> None:
    with pytest.raises(ValueError):
        SilenceOracleContext((CRITICAL_AD_SLOTS[0], CRITICAL_AD_SLOTS[0]))


def test_context_rejects_noncanonical_order() -> None:
    with pytest.raises(ValueError):
        SilenceOracleContext((CRITICAL_AD_SLOTS[1], CRITICAL_AD_SLOTS[0]))


def test_empty_context_is_permitted() -> None:
    assert SilenceOracleContext(()).unsupported_critical_slots == ()


def test_contract_failure_precedes_oracle(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    del payload["audit"]

    result = evaluate_silence_case(payload, None, c1_oracle())

    assert result.verdict.decision is Decision.BLOCK
    assert result.verdict.reason_codes == (RC_CONTRACT_MISSING_FIELDS,)
    assert result.evidence.state is EvidenceVerificationState.CONTRACT_INVALID


def test_dialogue_failure_precedes_oracle(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    result = evaluate_silence_case(payload_for(approved_cases), [], c1_oracle())

    assert result.verdict.decision is Decision.BLOCK
    assert result.verdict.reason_codes == (RC_DIALOGUE_INVALID,)
    assert result.evidence.state is EvidenceVerificationState.DIALOGUE_INVALID


def test_ordinary_runtime_mismatch_never_creates_hallucination_block(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    result = verify_case(payload_for(approved_cases), dialogue_for(approved_cases))

    assert result.verdict.decision is Decision.ABSTAIN
    assert result.verdict.abstain_mode is AbstainMode.ESCALATE
    assert result.verdict.reason_codes == (RC_AD_RED_FLAG_PRESENT,)
    assert result.evidence.has_runtime_failure is True


def test_trusted_nonunknown_critical_fill_creates_exact_block(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    result = evaluate_silence_case(
        payload_for(approved_cases), dialogue_for(approved_cases), c1_oracle()
    )

    assert result.verdict.decision is Decision.BLOCK
    assert result.verdict.abstain_mode is None
    assert result.verdict.reason_codes == (RC_HALLUCINATED_CRITICAL_FILL,)


def test_trusted_unknown_slot_does_not_block(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases, "silence_001")
    dialogue = dialogue_for(approved_cases, "silence_001")

    result = evaluate_silence_case(payload, dialogue, c1_oracle())

    assert result.verdict.decision is Decision.ABSTAIN
    assert result.verdict.abstain_mode is AbstainMode.ASK_ONCE
    assert RC_HALLUCINATED_CRITICAL_FILL not in result.verdict.reason_codes


@pytest.mark.parametrize("quote_matches", (False, True))
def test_oracle_block_does_not_depend_on_quote_mismatch(
    approved_cases: dict[str, dict[str, Any]], quote_matches: bool
) -> None:
    payload = payload_for(approved_cases)
    dialogue = dialogue_for(approved_cases)
    if quote_matches:
        dialogue[0]["text"] = payload["ad_gate"][CRITICAL_AD_SLOTS[0]][
            "evidence"
        ]["quote_text"]

    result = evaluate_silence_case(payload, dialogue, c1_oracle())

    assert result.verdict.reason_codes == (RC_HALLUCINATED_CRITICAL_FILL,)


def test_changing_only_dialogue_id_does_not_change_oracle_result(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    first_payload = payload_for(approved_cases)
    second_payload = payload_for(approved_cases)
    second_payload["meta"]["dialogue_id"] = "unrelated-id"
    dialogue = dialogue_for(approved_cases)

    first = evaluate_silence_case(first_payload, dialogue, c1_oracle())
    second = evaluate_silence_case(second_payload, dialogue, c1_oracle())

    assert first == second


def test_context_accepts_no_fixture_or_expected_result_fields() -> None:
    with pytest.raises(TypeError):
        SilenceOracleContext(  # type: ignore[call-arg]
            unsupported_critical_slots=(CRITICAL_AD_SLOTS[0],),
            fixture_id="case",
        )


def test_evaluation_result_preserves_precomputed_evidence_report(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    dialogue = dialogue_for(approved_cases)
    evidence = verify_evidence(payload, dialogue)

    result = evaluate_silence_case(payload, dialogue, c1_oracle())

    assert result.evidence == evidence
    assert result.evidence.has_runtime_failure is True


def test_empty_oracle_returns_ordinary_runtime_result(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    dialogue = dialogue_for(approved_cases)

    assert evaluate_silence_case(
        payload, dialogue, SilenceOracleContext(())
    ) == verify_case(payload, dialogue)


def test_repeated_calls_are_deterministic_and_inputs_are_not_mutated(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    payload = payload_for(approved_cases)
    dialogue = dialogue_for(approved_cases)
    before_payload = copy.deepcopy(payload)
    before_dialogue = copy.deepcopy(dialogue)

    first = evaluate_silence_case(payload, dialogue, c1_oracle())
    second = evaluate_silence_case(payload, dialogue, c1_oracle())

    assert first == second
    assert payload == before_payload
    assert dialogue == before_dialogue


def test_oracle_argument_type_is_checked(
    approved_cases: dict[str, dict[str, Any]],
) -> None:
    with pytest.raises(TypeError):
        evaluate_silence_case(
            payload_for(approved_cases),
            dialogue_for(approved_cases),
            object(),  # type: ignore[arg-type]
        )
