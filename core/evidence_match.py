"""Deterministic dialogue validation and anchored evidence grounding."""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast

from rapidfuzz.fuzz import partial_ratio_alignment

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


Pattern = tuple[str, ...]
PatternSet = tuple[Pattern, ...]


def _patterns(*phrases: str) -> PatternSet:
    return tuple(tuple(phrase.split()) for phrase in phrases)


_NEURO_POSITIVE = _patterns(
    "new weakness",
    "new numbness",
    "speech trouble",
    "slurred speech",
    "facial droop",
    "one sided weakness",
    "one sided numbness",
)
_NEURO_NEGATIVE = _patterns(
    "no new weakness numbness or speech trouble",
    "no new weakness or numbness",
    "no new weakness",
    "no new numbness",
    "no speech trouble",
    "no weakness",
    "no numbness",
    "speech is normal",
)

SLOT_POLARITY_PATTERNS: dict[
    tuple[str, str], tuple[PatternSet, PatternSet]
] = {
    ("instability", "syncope_or_collapse"): (
        _patterns(
            "fainted",
            "fainting",
            "passed out",
            "passing out",
            "collapsed",
            "collapse",
        ),
        _patterns(
            "no fainting",
            "no passing out",
            "no collapse",
            "not fainted",
            "did not faint",
            "didn t faint",
            "did not pass out",
            "didn t pass out",
            "not collapsed",
            "did not collapse",
            "didn t collapse",
            "not fainted or collapsed",
        ),
    ),
    ("instability", "severe_respiratory_distress"): (
        _patterns(
            "cannot breathe",
            "can t breathe",
            "could not breathe",
            "couldn t breathe",
            "gasping",
            "struggling to breathe",
            "severe shortness of breath",
        ),
        _patterns(
            "breathing is okay",
            "breathing okay",
            "breathe normally",
            "breathing normally",
            "speak in full sentences",
            "speaking in full sentences",
            "no shortness of breath",
            "not short of breath",
        ),
    ),
    ("instability", "cyanosis_or_low_o2"): (
        _patterns(
            "lips are blue",
            "blue lips",
            "oxygen is low",
            "oxygen reading is low",
            "low oxygen",
            "low o2",
            "abnormal oxygen",
        ),
        _patterns(
            "lips are not blue",
            "lips not blue",
            "oxygen is normal",
            "oxygen reading is normal",
            "normal oxygen",
            "normal o2",
        ),
    ),
    ("instability", "hypotension_or_shock_signs"): (
        _patterns(
            "blood pressure is low",
            "low blood pressure",
            "hypotensive",
            "cold and clammy",
            "cold or clammy",
            "in shock",
        ),
        _patterns(
            "blood pressure is normal",
            "normal blood pressure",
            "not cold or clammy",
            "not cold and clammy",
        ),
    ),
    ("instability", "altered_mental_status"): (
        _patterns(
            "confused",
            "disoriented",
            "not alert",
            "hard to wake",
            "unresponsive",
            "not thinking clearly",
        ),
        _patterns(
            "alert",
            "thinking clearly",
            "oriented",
            "not confused",
            "not disoriented",
        ),
    ),
    ("instability", "acute_focal_neuro_deficit"): (
        _NEURO_POSITIVE,
        _NEURO_NEGATIVE,
    ),
    ("instability", "severe_pain_at_rest_with_diaphoresis_or_pallor"): (
        _patterns(
            "severe pain at rest",
            "pain is severe at rest",
            "sweaty",
            "sweating",
            "diaphoretic",
            "pale",
            "pallor",
        ),
        _patterns(
            "pain is not severe at rest",
            "not severe at rest",
            "not sweaty",
            "not sweaty or pale",
            "not sweating",
            "not pale",
            "no sweating",
            "no pallor",
            "no chest pain",
        ),
    ),
    ("ad_gate", "C1_onset_maximal_at_start"): (
        _patterns(
            "maximal at the start",
            "maximal at start",
            "maximal immediately",
            "worst pain right away",
            "max pain right away",
            "instantly became the worst pain",
            "sudden onset",
            "started suddenly",
            "out of nowhere",
        ),
        _patterns(
            "built up gradually",
            "gradual onset",
            "not maximal at the start",
            "not maximal at start",
            "rather than being maximal at the start",
            "rather than maximal at the start",
            "denies sudden onset",
            "no sudden onset",
            "not sudden onset",
        ),
    ),
    ("ad_gate", "C2_back_interscapular_radiation"): (
        _patterns(
            "upper back between the shoulder blades",
            "between the shoulder blades",
            "interscapular",
            "spread to my back",
            "spreads to my back",
            "goes to my upper back",
            "radiates to my back",
        ),
        _patterns(
            "does not spread to my back or between my shoulder blades",
            "does not spread to the back or between the shoulder blades",
            "does not spread to my back",
            "doesn t spread to my back",
            "no pain in my back",
            "nothing in my back",
            "not in my back",
            "no back radiation",
        ),
    ),
    ("ad_gate", "C4_aortic_high_risk_history_any"): (
        _patterns(
            "aortic aneurysm",
            "known aortic disease",
            "marfan syndrome",
            "ehlers danlos",
            "bicuspid aortic valve",
            "family history of aortic dissection",
            "prior aortic surgery",
        ),
        _patterns(
            "none of the listed aortic high risk history",
            "no aortic high risk history",
            "no known aortic disease",
            "no marfan syndrome",
            "no family history of aortic dissection",
            "no prior aortic surgery",
        ),
    ),
    ("audit", "A1_focal_neuro_deficit"): (
        _NEURO_POSITIVE,
        _NEURO_NEGATIVE,
    ),
}

NEGATION_CUES = _patterns(
    "no",
    "not",
    "never",
    "none",
    "nothing",
    "neither",
    "nor",
    "without",
    "nah",
    "deny",
    "denies",
    "denied",
    "cannot",
    "can t",
    "could not",
    "couldn t",
    "do not",
    "don t",
    "does not",
    "doesn t",
    "did not",
    "didn t",
    "is not",
    "isn t",
    "are not",
    "aren t",
    "was not",
    "wasn t",
    "were not",
    "weren t",
    "has not",
    "hasn t",
    "have not",
    "haven t",
    "had not",
    "hadn t",
    "will not",
    "won t",
    "would not",
    "wouldn t",
    "should not",
    "shouldn t",
)

AMBIGUOUS_PHRASES = _patterns(
    "not only",
    "not uncommon",
    "not impossible",
    "not unlikely",
    "not without",
    "cannot rule out",
    "can t rule out",
    "could not rule out",
    "couldn t rule out",
    "no absence of",
    "not no",
    "denies no",
    "denied no",
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


class _Polarity(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    AMBIGUOUS = "AMBIGUOUS"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True, slots=True)
class _PatternHit:
    start: int
    end: int
    polarity: _Polarity


def _find_spans(
    tokens: tuple[str, ...],
    patterns: PatternSet,
    start: int = 0,
    end: int | None = None,
) -> tuple[tuple[int, int], ...]:
    limit = len(tokens) if end is None else end
    spans: list[tuple[int, int]] = []
    for pattern in patterns:
        pattern_length = len(pattern)
        for index in range(start, limit - pattern_length + 1):
            if tokens[index : index + pattern_length] == pattern:
                spans.append((index, index + pattern_length))
    return tuple(spans)


def _spans_overlap(first: tuple[int, int], second: tuple[int, int]) -> bool:
    return first[0] < second[1] and second[0] < first[1]


def _classify_slot_patterns(
    tokens: tuple[str, ...],
    section: str,
    slot_name: str,
    start: int,
    end: int,
) -> tuple[_Polarity, tuple[_PatternHit, ...]]:
    positive_patterns, negative_patterns = SLOT_POLARITY_PATTERNS[
        (section, slot_name)
    ]
    positive_hits = tuple(
        _PatternHit(hit_start, hit_end, _Polarity.POSITIVE)
        for hit_start, hit_end in _find_spans(
            tokens, positive_patterns, start, end
        )
    )
    negative_hits = tuple(
        _PatternHit(hit_start, hit_end, _Polarity.NEGATIVE)
        for hit_start, hit_end in _find_spans(
            tokens, negative_patterns, start, end
        )
    )

    def is_suppressed(
        hit: _PatternHit, opposite_hits: tuple[_PatternHit, ...]
    ) -> bool:
        hit_length = hit.end - hit.start
        return any(
            opposite.start <= hit.start
            and hit.end <= opposite.end
            and opposite.end - opposite.start > hit_length
            for opposite in opposite_hits
        )

    surviving_positive = tuple(
        hit for hit in positive_hits if not is_suppressed(hit, negative_hits)
    )
    surviving_negative = tuple(
        hit for hit in negative_hits if not is_suppressed(hit, positive_hits)
    )
    surviving = surviving_positive + surviving_negative

    if surviving_positive and surviving_negative:
        return _Polarity.AMBIGUOUS, surviving
    if surviving_positive:
        return _Polarity.POSITIVE, surviving
    if surviving_negative:
        return _Polarity.NEGATIVE, surviving
    return _Polarity.NEUTRAL, ()


def _expected_polarity(value: str) -> _Polarity:
    if value in ("PRESENT", "POSSIBLE", "YES"):
        return _Polarity.POSITIVE
    if value in ("ABSENT", "NO"):
        return _Polarity.NEGATIVE
    raise ValueError("UNKNOWN has no expected polarity")


def _has_negation(tokens: tuple[str, ...]) -> bool:
    return bool(_find_spans(tokens, NEGATION_CUES))


def _candidate_has_ambiguity(
    quote_tokens: tuple[str, ...],
    turn_tokens: tuple[str, ...],
    destination: tuple[int, int],
    context: tuple[int, int],
    surviving_hits: tuple[_PatternHit, ...],
) -> bool:
    if _find_spans(quote_tokens, AMBIGUOUS_PHRASES):
        return True

    destination_ambiguity = _find_spans(turn_tokens, AMBIGUOUS_PHRASES)
    if any(
        _spans_overlap(span, destination) for span in destination_ambiguity
    ):
        return True

    context_ambiguity = _find_spans(
        turn_tokens, AMBIGUOUS_PHRASES, context[0], context[1]
    )
    return any(
        _spans_overlap(ambiguous_span, (hit.start, hit.end))
        for ambiguous_span in context_ambiguity
        for hit in surviving_hits
    )


def _evaluate_candidate(
    section: str,
    slot_name: str,
    value: str,
    quote_tokens: tuple[str, ...],
    turn_tokens: tuple[str, ...],
    destination: tuple[int, int],
) -> tuple[bool, bool]:
    context = (
        max(0, destination[0] - 5),
        min(len(turn_tokens), destination[1] + 5),
    )
    polarity, surviving_hits = _classify_slot_patterns(
        turn_tokens, section, slot_name, context[0], context[1]
    )
    destination_tokens = turn_tokens[destination[0] : destination[1]]
    if _has_negation(quote_tokens) != _has_negation(destination_tokens):
        return True, False
    if _candidate_has_ambiguity(
        quote_tokens,
        turn_tokens,
        destination,
        context,
        surviving_hits,
    ):
        return True, False

    expected = _expected_polarity(value)
    if polarity is _Polarity.AMBIGUOUS:
        return True, False
    if polarity not in (_Polarity.NEUTRAL, expected):
        return True, False
    return False, polarity is expected


def _token_character_spans(
    tokens: tuple[str, ...],
) -> tuple[tuple[int, int], ...]:
    spans: list[tuple[int, int]] = []
    offset = 0
    for token in tokens:
        spans.append((offset, offset + len(token)))
        offset += len(token) + 1
    return tuple(spans)


def _destination_token_span(
    tokens: tuple[str, ...], destination_start: int, destination_end: int
) -> tuple[int, int] | None:
    overlapping = tuple(
        index
        for index, token_span in enumerate(_token_character_spans(tokens))
        if token_span[0] < destination_end and destination_start < token_span[1]
    )
    if not overlapping:
        return None
    return overlapping[0], overlapping[-1] + 1


def _not_found(
    section: str,
    slot_name: str,
    value: str,
    source_turn_id: int,
    threshold: int,
    score: float | None = None,
) -> EvidenceSlotResult:
    return EvidenceSlotResult(
        section=section,
        slot=slot_name,
        value=value,
        source_turn_id=source_turn_id,
        threshold=threshold,
        status=EvidenceSlotStatus.NOT_FOUND,
        score=score,
    )


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
        return _not_found(
            section, slot_name, value, source_turn_id, threshold
        )

    normalized_turn = _normalize(anchored_text)
    quote_tokens = tuple(quote.split())
    turn_tokens = tuple(normalized_turn.split())
    exact_occurrences = _find_spans(turn_tokens, (quote_tokens,))
    if exact_occurrences:
        candidate_results = tuple(
            _evaluate_candidate(
                section,
                slot_name,
                value,
                quote_tokens,
                turn_tokens,
                occurrence,
            )
            for occurrence in exact_occurrences
        )
        if any(conflict for conflict, _ in candidate_results):
            return _not_found(
                section, slot_name, value, source_turn_id, threshold
            )
        if (
            len(quote) < 8 or len(quote_tokens) < 2
        ) and not any(same_polarity for _, same_polarity in candidate_results):
            return _not_found(
                section, slot_name, value, source_turn_id, threshold
            )
        return EvidenceSlotResult(
            section=section,
            slot=slot_name,
            value=value,
            source_turn_id=source_turn_id,
            threshold=threshold,
            status=EvidenceSlotStatus.GROUNDED_EXACT,
            score=100.0,
        )

    if len(quote) < 8 or len(quote_tokens) < 2:
        return _not_found(
            section, slot_name, value, source_turn_id, threshold
        )

    alignment = partial_ratio_alignment(
        quote, normalized_turn, processor=None
    )
    if alignment is None:
        return _not_found(
            section, slot_name, value, source_turn_id, threshold
        )
    destination = _destination_token_span(
        turn_tokens, alignment.dest_start, alignment.dest_end
    )
    if destination is None:
        return _not_found(
            section, slot_name, value, source_turn_id, threshold
        )

    candidate_conflict, _ = _evaluate_candidate(
        section,
        slot_name,
        value,
        quote_tokens,
        turn_tokens,
        destination,
    )
    full_turn_polarity, _ = _classify_slot_patterns(
        turn_tokens, section, slot_name, 0, len(turn_tokens)
    )
    if candidate_conflict or full_turn_polarity is _Polarity.AMBIGUOUS:
        return _not_found(
            section, slot_name, value, source_turn_id, threshold
        )

    score = float(alignment.score)
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
