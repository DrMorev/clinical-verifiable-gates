"""Deterministic dialogue validation and anchored evidence grounding."""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast

from rapidfuzz.fuzz import partial_ratio

from core.contract_validation import ValidationIssue, validate_contract
from core.verifier import CRITICAL_AD_SLOTS, INSTABILITY_SLOTS


class EvidenceVerificationState(str, Enum):
    CONTRACT_INVALID = "CONTRACT_INVALID"
    DIALOGUE_INVALID = "DIALOGUE_INVALID"
    COMPLETE = "COMPLETE"


class EvidenceSlotStatus(str, Enum):
    SKIPPED_UNKNOWN = "SKIPPED_UNKNOWN"
    GROUNDED_EXACT = "GROUNDED_EXACT"
    GROUNDED_FUZZY = "GROUNDED_FUZZY"
    NOT_FOUND = "NOT_FOUND"


DIALOGUE_ISSUE_CODES = (
    "DIALOGUE_ROOT_NOT_LIST",
    "DIALOGUE_EMPTY",
    "TURN_NOT_OBJECT",
    "TURN_ID_MISSING",
    "TURN_ID_INVALID",
    "TURN_ID_DUPLICATE",
    "TURN_TEXT_MISSING",
    "TURN_TEXT_INVALID",
    "TURN_AFTER_LAST",
    "LAST_TURN_MISMATCH",
)

AUDIT_SLOTS = ("A1_focal_neuro_deficit",)

SLOT_SPECS = (
    *(("instability", slot, 90) for slot in INSTABILITY_SLOTS),
    *(("ad_gate", slot, 90) for slot in CRITICAL_AD_SLOTS),
    *(("audit", slot, 85) for slot in AUDIT_SLOTS),
)


PathComponent = str | int


@dataclass(frozen=True, slots=True)
class DialogueValidationIssue:
    code: str
    path: tuple[PathComponent, ...]

    def __post_init__(self) -> None:
        if self.code not in DIALOGUE_ISSUE_CODES:
            raise ValueError("unsupported dialogue issue code")
        if type(self.path) is not tuple:
            raise TypeError("path must be a tuple")
        if any(type(component) not in (str, int) for component in self.path):
            raise TypeError("path components must be strings or integers")


def _is_numeric_score(value: object) -> bool:
    return (
        type(value) in (int, float)
        and math.isfinite(float(value))
        and 0.0 <= float(value) <= 100.0
    )


@dataclass(frozen=True, slots=True)
class EvidenceSlotResult:
    section: str
    slot: str
    value: str
    source_turn_id: int | None
    threshold: int
    status: EvidenceSlotStatus
    score: float | None

    def __post_init__(self) -> None:
        if self.section not in ("instability", "ad_gate", "audit"):
            raise ValueError("unsupported evidence section")
        if type(self.slot) is not str or not self.slot:
            raise ValueError("slot must be a non-empty string")
        if type(self.value) is not str or not self.value:
            raise ValueError("value must be a non-empty string")
        if self.threshold not in (85, 90) or type(self.threshold) is not int:
            raise ValueError("threshold must be 85 or 90")
        if not isinstance(self.status, EvidenceSlotStatus):
            raise TypeError("status must be an EvidenceSlotStatus")

        valid_turn = (
            type(self.source_turn_id) is int and self.source_turn_id >= 0
        )
        if self.status is EvidenceSlotStatus.SKIPPED_UNKNOWN:
            if self.source_turn_id is not None or self.score is not None:
                raise ValueError("SKIPPED_UNKNOWN cannot have source or score")
            return

        if not valid_turn:
            raise ValueError("matched and missing evidence require a source turn")

        if self.status is EvidenceSlotStatus.GROUNDED_EXACT:
            if self.score != 100.0:
                raise ValueError("GROUNDED_EXACT requires score 100.0")
            return

        if self.status is EvidenceSlotStatus.GROUNDED_FUZZY:
            if not _is_numeric_score(self.score) or float(self.score) < self.threshold:
                raise ValueError("GROUNDED_FUZZY requires score at or above threshold")
            return

        if self.status is EvidenceSlotStatus.NOT_FOUND:
            if self.score is not None and (
                not _is_numeric_score(self.score)
                or float(self.score) >= self.threshold
            ):
                raise ValueError("NOT_FOUND score must be below threshold")


@dataclass(frozen=True, slots=True)
class EvidenceVerificationResult:
    state: EvidenceVerificationState
    contract_issues: tuple[ValidationIssue, ...]
    dialogue_issues: tuple[DialogueValidationIssue, ...]
    slot_results: tuple[EvidenceSlotResult, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.state, EvidenceVerificationState):
            raise TypeError("state must be an EvidenceVerificationState")
        if type(self.contract_issues) is not tuple:
            raise TypeError("contract_issues must be a tuple")
        if type(self.dialogue_issues) is not tuple:
            raise TypeError("dialogue_issues must be a tuple")
        if type(self.slot_results) is not tuple:
            raise TypeError("slot_results must be a tuple")
        if any(not isinstance(issue, ValidationIssue) for issue in self.contract_issues):
            raise TypeError("contract_issues must contain ValidationIssue values")
        if any(
            not isinstance(issue, DialogueValidationIssue)
            for issue in self.dialogue_issues
        ):
            raise TypeError("dialogue_issues must contain DialogueValidationIssue values")
        if any(
            not isinstance(result, EvidenceSlotResult)
            for result in self.slot_results
        ):
            raise TypeError("slot_results must contain EvidenceSlotResult values")

        if self.state is EvidenceVerificationState.CONTRACT_INVALID:
            if not self.contract_issues or self.dialogue_issues or self.slot_results:
                raise ValueError("invalid contract result has inconsistent fields")
            return

        if self.state is EvidenceVerificationState.DIALOGUE_INVALID:
            if self.contract_issues or not self.dialogue_issues or self.slot_results:
                raise ValueError("invalid dialogue result has inconsistent fields")
            return

        expected_order = tuple(
            (section, slot, threshold) for section, slot, threshold in SLOT_SPECS
        )
        observed_order = tuple(
            (result.section, result.slot, result.threshold)
            for result in self.slot_results
        )
        if self.contract_issues or self.dialogue_issues:
            raise ValueError("complete result cannot contain validation issues")
        if observed_order != expected_order:
            raise ValueError("complete result requires 11 slots in canonical order")

    @property
    def runtime_failures(self) -> tuple[EvidenceSlotResult, ...]:
        return tuple(
            result
            for result in self.slot_results
            if result.status is EvidenceSlotStatus.NOT_FOUND
            and result.section in ("instability", "ad_gate")
        )

    @property
    def audit_failures(self) -> tuple[EvidenceSlotResult, ...]:
        return tuple(
            result
            for result in self.slot_results
            if result.status is EvidenceSlotStatus.NOT_FOUND
            and result.section == "audit"
        )

    @property
    def has_runtime_failure(self) -> bool:
        return bool(self.runtime_failures)

    @property
    def has_audit_failure(self) -> bool:
        return bool(self.audit_failures)


def _component_sort_key(component: PathComponent) -> tuple[int, int | str]:
    if type(component) is int:
        return (0, component)
    return (1, component)


def _dialogue_issue_sort_key(
    issue: DialogueValidationIssue,
) -> tuple[tuple[tuple[int, int | str], ...], int]:
    return (
        tuple(_component_sort_key(component) for component in issue.path),
        DIALOGUE_ISSUE_CODES.index(issue.code),
    )


def _validate_dialogue(
    dialogue: object, last_turn_id: int
) -> tuple[tuple[DialogueValidationIssue, ...], dict[int, str]]:
    if not isinstance(dialogue, list):
        return (
            (DialogueValidationIssue("DIALOGUE_ROOT_NOT_LIST", ()),),
            {},
        )
    if not dialogue:
        return ((DialogueValidationIssue("DIALOGUE_EMPTY", ()),), {})

    issues: list[DialogueValidationIssue] = []
    turns: dict[int, str] = {}
    seen_turn_ids: set[int] = set()
    valid_turn_ids: list[int] = []

    for index, turn in enumerate(dialogue):
        if not isinstance(turn, dict):
            issues.append(DialogueValidationIssue("TURN_NOT_OBJECT", (index,)))
            continue

        if "turn_id" not in turn:
            issues.append(
                DialogueValidationIssue("TURN_ID_MISSING", (index, "turn_id"))
            )
            turn_id: object = None
        else:
            turn_id = turn["turn_id"]
            if type(turn_id) is not int:
                issues.append(
                    DialogueValidationIssue("TURN_ID_INVALID", (index, "turn_id"))
                )
            else:
                valid_turn_ids.append(turn_id)
                if turn_id in seen_turn_ids:
                    issues.append(
                        DialogueValidationIssue(
                            "TURN_ID_DUPLICATE", (index, "turn_id")
                        )
                    )
                else:
                    seen_turn_ids.add(turn_id)
                if turn_id > last_turn_id:
                    issues.append(
                        DialogueValidationIssue(
                            "TURN_AFTER_LAST", (index, "turn_id")
                        )
                    )

        if "text" not in turn:
            issues.append(
                DialogueValidationIssue("TURN_TEXT_MISSING", (index, "text"))
            )
            text: object = None
        else:
            text = turn["text"]
            if type(text) is not str:
                issues.append(
                    DialogueValidationIssue("TURN_TEXT_INVALID", (index, "text"))
                )

        if type(turn_id) is int and type(text) is str and turn_id not in turns:
            turns[turn_id] = text

    if valid_turn_ids and max(valid_turn_ids) != last_turn_id:
        issues.append(
            DialogueValidationIssue(
                "LAST_TURN_MISMATCH", ("meta", "last_turn_id")
            )
        )

    ordered_issues = tuple(sorted(issues, key=_dialogue_issue_sort_key))
    if ordered_issues:
        return ordered_issues, {}
    return (), turns


def _normalize(text: str) -> str:
    casefolded = text.casefold()
    without_punctuation = "".join(
        " " if unicodedata.category(character).startswith("P") else character
        for character in casefolded
    )
    return " ".join(without_punctuation.split())


def _verify_slot(
    section: str,
    slot_name: str,
    threshold: int,
    slot: dict[str, Any],
    turns: dict[int, str],
) -> EvidenceSlotResult:
    value = cast(str, slot["value"])
    if value == "UNKNOWN":
        return EvidenceSlotResult(
            section=section,
            slot=slot_name,
            value=value,
            source_turn_id=None,
            threshold=threshold,
            status=EvidenceSlotStatus.SKIPPED_UNKNOWN,
            score=None,
        )

    evidence = cast(dict[str, Any], slot["evidence"])
    source_turn_id = cast(int, evidence["source_turn_id"])
    quote = _normalize(cast(str, evidence["quote_text"]))
    anchored_text = turns.get(source_turn_id)

    if not quote or anchored_text is None:
        return EvidenceSlotResult(
            section=section,
            slot=slot_name,
            value=value,
            source_turn_id=source_turn_id,
            threshold=threshold,
            status=EvidenceSlotStatus.NOT_FOUND,
            score=None,
        )

    normalized_turn = _normalize(anchored_text)
    if quote in normalized_turn:
        return EvidenceSlotResult(
            section=section,
            slot=slot_name,
            value=value,
            source_turn_id=source_turn_id,
            threshold=threshold,
            status=EvidenceSlotStatus.GROUNDED_EXACT,
            score=100.0,
        )

    if len(quote) < 8 or len(quote.split()) < 2:
        return EvidenceSlotResult(
            section=section,
            slot=slot_name,
            value=value,
            source_turn_id=source_turn_id,
            threshold=threshold,
            status=EvidenceSlotStatus.NOT_FOUND,
            score=None,
        )

    score = float(partial_ratio(quote, normalized_turn, processor=None))
    status = (
        EvidenceSlotStatus.GROUNDED_FUZZY
        if score >= threshold
        else EvidenceSlotStatus.NOT_FOUND
    )
    return EvidenceSlotResult(
        section=section,
        slot=slot_name,
        value=value,
        source_turn_id=source_turn_id,
        threshold=threshold,
        status=status,
        score=score,
    )


def verify_evidence(payload: object, dialogue: object) -> EvidenceVerificationResult:
    validation = validate_contract(payload)
    if not validation.is_valid:
        return EvidenceVerificationResult(
            state=EvidenceVerificationState.CONTRACT_INVALID,
            contract_issues=validation.issues,
            dialogue_issues=(),
            slot_results=(),
        )

    contract = cast(dict[str, Any], payload)
    last_turn_id = cast(int, contract["meta"]["last_turn_id"])
    dialogue_issues, turns = _validate_dialogue(dialogue, last_turn_id)
    if dialogue_issues:
        return EvidenceVerificationResult(
            state=EvidenceVerificationState.DIALOGUE_INVALID,
            contract_issues=(),
            dialogue_issues=dialogue_issues,
            slot_results=(),
        )

    slot_results = tuple(
        _verify_slot(
            section,
            slot_name,
            threshold,
            cast(dict[str, Any], contract[section][slot_name]),
            turns,
        )
        for section, slot_name, threshold in SLOT_SPECS
    )
    return EvidenceVerificationResult(
        state=EvidenceVerificationState.COMPLETE,
        contract_issues=(),
        dialogue_issues=(),
        slot_results=slot_results,
    )
