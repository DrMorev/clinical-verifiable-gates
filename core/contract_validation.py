"""Draft 7 structural validation for extractor contract payloads."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

from core.result import Decision, VerifierResult


RC_CONTRACT_MISSING_FIELDS = "RC_CONTRACT_MISSING_FIELDS"
RC_CONTRACT_SCHEMA_INVALID = "RC_CONTRACT_SCHEMA_INVALID"

_SCHEMA_PATH = (
    Path(__file__).resolve().parent
    / "schemas"
    / "ad_extractor_contract_v0.1.schema.json"
)

PathComponent = str | int


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    instance_path: tuple[PathComponent, ...]
    validator: str
    schema_path: tuple[PathComponent, ...]
    message: str


@dataclass(frozen=True, slots=True)
class ContractValidationResult:
    is_valid: bool
    issues: tuple[ValidationIssue, ...]
    failure_result: VerifierResult | None

    def __post_init__(self) -> None:
        if type(self.is_valid) is not bool:
            raise TypeError("is_valid must be a bool")
        if type(self.issues) is not tuple:
            raise TypeError("issues must be a tuple")
        if self.is_valid:
            if self.issues or self.failure_result is not None:
                raise ValueError("valid contracts cannot have issues or a failure result")
        else:
            if not self.issues:
                raise ValueError("invalid contracts require at least one issue")
            if (
                self.failure_result is None
                or self.failure_result.decision is not Decision.BLOCK
            ):
                raise ValueError("invalid contracts require a BLOCK failure result")


def _load_validator() -> Draft7Validator:
    with _SCHEMA_PATH.open(encoding="utf-8") as schema_file:
        schema = json.load(schema_file)
    Draft7Validator.check_schema(schema)
    return Draft7Validator(schema)


_VALIDATOR = _load_validator()


def _component_sort_key(component: PathComponent) -> tuple[int, int | str]:
    if isinstance(component, int) and not isinstance(component, bool):
        return (0, component)
    return (1, str(component))


def _issue_sort_key(issue: ValidationIssue) -> tuple[Any, ...]:
    return (
        tuple(_component_sort_key(part) for part in issue.instance_path),
        issue.validator,
        tuple(_component_sort_key(part) for part in issue.schema_path),
        issue.message,
    )


def validate_contract(payload: object) -> ContractValidationResult:
    issues = tuple(
        sorted(
            (
                ValidationIssue(
                    instance_path=tuple(error.absolute_path),
                    validator=str(error.validator),
                    schema_path=tuple(error.absolute_schema_path),
                    message=error.message,
                )
                for error in _VALIDATOR.iter_errors(payload)
            ),
            key=_issue_sort_key,
        )
    )

    if not issues:
        return ContractValidationResult(
            is_valid=True,
            issues=(),
            failure_result=None,
        )

    reason_codes: list[str] = []
    if any(issue.validator == "required" for issue in issues):
        reason_codes.append(RC_CONTRACT_MISSING_FIELDS)
    if any(issue.validator != "required" for issue in issues):
        reason_codes.append(RC_CONTRACT_SCHEMA_INVALID)

    return ContractValidationResult(
        is_valid=False,
        issues=issues,
        failure_result=VerifierResult(
            decision=Decision.BLOCK,
            reason_codes=tuple(reason_codes),
        ),
    )
