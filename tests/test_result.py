import pytest

from core.result import (
    DEFAULT_SCHEMA_REF,
    DEFAULT_TAXONOMY_VERSION,
    AbstainMode,
    Decision,
    VerifierResult,
)


def test_valid_pass_construction() -> None:
    result = VerifierResult(decision=Decision.PASS, reason_codes=())

    assert result.decision is Decision.PASS
    assert result.reason_codes == ()
    assert result.abstain_mode is None


def test_valid_block_construction() -> None:
    result = VerifierResult(
        decision=Decision.BLOCK,
        reason_codes=("RC_CONTRACT_SCHEMA_INVALID",),
    )

    assert result.decision is Decision.BLOCK


def test_valid_abstain_ask_once() -> None:
    result = VerifierResult(
        decision=Decision.ABSTAIN,
        reason_codes=("RC_AD_CRITICAL_SLOT_MISSING",),
        abstain_mode=AbstainMode.ASK_ONCE,
    )

    assert result.abstain_mode is AbstainMode.ASK_ONCE


def test_valid_abstain_escalate() -> None:
    result = VerifierResult(
        decision=Decision.ABSTAIN,
        reason_codes=("RC_INSTABILITY_BYPASS",),
        abstain_mode=AbstainMode.ESCALATE,
    )

    assert result.abstain_mode is AbstainMode.ESCALATE


def test_abstain_without_mode_is_rejected() -> None:
    with pytest.raises(ValueError):
        VerifierResult(
            decision=Decision.ABSTAIN,
            reason_codes=("RC_AD_CRITICAL_SLOT_MISSING",),
        )


def test_pass_with_mode_is_rejected() -> None:
    with pytest.raises(ValueError):
        VerifierResult(
            decision=Decision.PASS,
            reason_codes=(),
            abstain_mode=AbstainMode.ASK_ONCE,
        )


def test_block_with_mode_is_rejected() -> None:
    with pytest.raises(ValueError):
        VerifierResult(
            decision=Decision.BLOCK,
            reason_codes=("RC_CONTRACT_SCHEMA_INVALID",),
            abstain_mode=AbstainMode.ESCALATE,
        )


def test_block_without_reason_code_is_rejected() -> None:
    with pytest.raises(ValueError):
        VerifierResult(decision=Decision.BLOCK, reason_codes=())


def test_abstain_without_reason_code_is_rejected() -> None:
    with pytest.raises(ValueError):
        VerifierResult(
            decision=Decision.ABSTAIN,
            reason_codes=(),
            abstain_mode=AbstainMode.ASK_ONCE,
        )


def test_reason_code_order_and_duplicates_are_preserved() -> None:
    codes = (
        "RC_CONTRACT_MISSING_FIELDS",
        "RC_CONTRACT_SCHEMA_INVALID",
        "RC_CONTRACT_SCHEMA_INVALID",
    )
    result = VerifierResult(decision=Decision.BLOCK, reason_codes=codes)

    assert result.reason_codes == codes
    assert result.to_dict()["reason_codes"] == list(codes)


def test_invalid_values_are_not_silently_coerced() -> None:
    with pytest.raises(TypeError):
        VerifierResult(decision="PASS", reason_codes=())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        VerifierResult(  # type: ignore[arg-type]
            decision=Decision.PASS,
            reason_codes=[],
        )
    with pytest.raises(TypeError):
        VerifierResult(
            decision=Decision.ABSTAIN,
            reason_codes=("RC_AD_CRITICAL_SLOT_MISSING",),
            abstain_mode="ASK_ONCE",  # type: ignore[arg-type]
        )


def test_to_dict_is_deterministic() -> None:
    result = VerifierResult(
        decision=Decision.BLOCK,
        reason_codes=("RC_CONTRACT_MISSING_FIELDS", "RC_CONTRACT_SCHEMA_INVALID"),
    )

    expected = {
        "decision": "BLOCK",
        "reason_codes": [
            "RC_CONTRACT_MISSING_FIELDS",
            "RC_CONTRACT_SCHEMA_INVALID",
        ],
        "abstain_mode": None,
        "schema_ref": DEFAULT_SCHEMA_REF,
        "taxonomy_version": DEFAULT_TAXONOMY_VERSION,
    }
    assert result.to_dict() == expected
    assert list(result.to_dict()) == [
        "decision",
        "reason_codes",
        "abstain_mode",
        "schema_ref",
        "taxonomy_version",
    ]


def test_to_json_is_byte_for_byte_deterministic() -> None:
    first = VerifierResult(
        decision=Decision.ABSTAIN,
        reason_codes=("RC_AD_CRITICAL_SLOT_MISSING",),
        abstain_mode=AbstainMode.ASK_ONCE,
    )
    second = VerifierResult(
        decision=Decision.ABSTAIN,
        reason_codes=("RC_AD_CRITICAL_SLOT_MISSING",),
        abstain_mode=AbstainMode.ASK_ONCE,
    )

    assert first.to_json().encode("utf-8") == second.to_json().encode("utf-8")
    assert first.to_json() == (
        '{"decision":"ABSTAIN","reason_codes":["RC_AD_CRITICAL_SLOT_MISSING"],'
        '"abstain_mode":"ASK_ONCE",'
        '"schema_ref":"core/schemas/ad_extractor_contract_v0.1.schema.json",'
        '"taxonomy_version":"v0.1"}'
    )
