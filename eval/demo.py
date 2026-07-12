"""Canonical reviewer demo for approved CVG fixtures."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Sequence

from core.case_verifier import verify_case


DEFAULT_FIXTURE_ID = "golden_001"
FIXTURE_PATH = Path(__file__).resolve().parent / "data" / "ad_verdict_fixtures_v0.1.json"


class DemoError(Exception):
    """Expected operational failure for the reviewer demo."""


def _load_cases() -> dict[str, dict[str, object]]:
    try:
        fixture_set = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DemoError("fixture source could not be loaded") from exc

    if not isinstance(fixture_set, dict) or not isinstance(
        fixture_set.get("cases"), list
    ):
        raise DemoError("fixture source has an invalid structure")

    cases: dict[str, dict[str, object]] = {}
    for case in fixture_set["cases"]:
        if not isinstance(case, dict):
            raise DemoError("fixture source has an invalid structure")
        fixture_id = case.get("id")
        if not isinstance(fixture_id, str) or not fixture_id or fixture_id in cases:
            raise DemoError("fixture source has an invalid structure")
        cases[fixture_id] = case
    return cases


def _run(fixture_id: str) -> str:
    case = _load_cases().get(fixture_id)
    if case is None:
        raise DemoError("unknown fixture ID")
    if "extractor_output" not in case or "dialogue" not in case:
        raise DemoError("selected fixture is missing required data")

    try:
        result = verify_case(case["extractor_output"], case["dialogue"])
    except Exception as exc:
        raise DemoError("selected fixture could not be verified") from exc
    return result.verdict.to_json()


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) > 1:
        print("error: expected zero or one fixture ID", file=sys.stderr)
        return 2

    fixture_id = arguments[0] if arguments else DEFAULT_FIXTURE_ID
    try:
        output = _run(fixture_id)
    except DemoError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
