from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from eval import demo


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPOSITORY_ROOT / "eval" / "data" / "ad_verdict_fixtures_v0.1.json"
GOLDEN_JSON = (
    '{"decision":"ABSTAIN","reason_codes":["RC_AD_RED_FLAG_PRESENT"],'
    '"abstain_mode":"ESCALATE","schema_ref":"core/schemas/'
    'ad_extractor_contract_v0.1.schema.json","taxonomy_version":"v0.1"}'
)
PASS_JSON = (
    '{"decision":"PASS","reason_codes":[],"abstain_mode":null,'
    '"schema_ref":"core/schemas/ad_extractor_contract_v0.1.schema.json",'
    '"taxonomy_version":"v0.1"}'
)
BLOCK_JSON = (
    '{"decision":"BLOCK","reason_codes":["RC_CONTRACT_MISSING_FIELDS"],'
    '"abstain_mode":null,"schema_ref":"core/schemas/'
    'ad_extractor_contract_v0.1.schema.json","taxonomy_version":"v0.1"}'
)


def run_demo(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "eval.demo", *arguments],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def assert_success(
    completed: subprocess.CompletedProcess[str], expected_json: str
) -> None:
    assert completed.returncode == 0
    assert completed.stdout == expected_json + "\n"
    assert completed.stderr == ""
    assert completed.stdout.count("\n") == 1
    assert json.loads(completed.stdout) == json.loads(expected_json)


def assert_failure(returncode: int, stdout: str, stderr: str) -> None:
    assert returncode != 0
    assert stdout == ""
    assert stderr.strip()
    assert len(stderr.splitlines()) == 1
    assert len(stderr) < 200
    assert "Traceback" not in stderr


def invoke_main(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fixture_path: Path,
    arguments: list[str],
) -> tuple[int, str, str]:
    monkeypatch.setattr(demo, "FIXTURE_PATH", fixture_path)
    returncode = demo.main(arguments)
    captured = capsys.readouterr()
    return returncode, captured.out, captured.err


def test_no_argument_selects_golden_fixture() -> None:
    assert_success(run_demo(), GOLDEN_JSON)


def test_explicit_golden_fixture_returns_exact_abstain_json() -> None:
    assert_success(run_demo("golden_001"), GOLDEN_JSON)


def test_pass_fixture_returns_exact_pass_json() -> None:
    assert_success(run_demo("pass_all_critical_no_001"), PASS_JSON)


def test_invalid_contract_fixture_returns_exact_block_json() -> None:
    assert_success(run_demo("contract_missing_fields_001"), BLOCK_JSON)


def test_repeated_successful_execution_is_byte_identical() -> None:
    first = run_demo("golden_001")
    second = run_demo("golden_001")

    assert first.returncode == second.returncode == 0
    assert first.stdout.encode() == second.stdout.encode()
    assert first.stderr.encode() == second.stderr.encode() == b""


@pytest.mark.parametrize(
    "arguments",
    (("unknown_fixture",), ("golden_001", "pass_all_critical_no_001")),
)
def test_invalid_cli_selection_fails_closed(arguments: tuple[str, ...]) -> None:
    completed = run_demo(*arguments)

    assert_failure(completed.returncode, completed.stdout, completed.stderr)


@pytest.mark.parametrize("source_kind", ("missing", "unreadable"))
def test_missing_or_unreadable_fixture_source_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    source_kind: str,
) -> None:
    fixture_path = tmp_path / "missing.json" if source_kind == "missing" else tmp_path

    result = invoke_main(monkeypatch, capsys, fixture_path, [])

    assert_failure(*result)


def test_invalid_json_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fixture_path = tmp_path / "fixtures.json"
    fixture_path.write_text("{invalid", encoding="utf-8")

    result = invoke_main(monkeypatch, capsys, fixture_path, [])

    assert_failure(*result)


@pytest.mark.parametrize(
    "fixture_set",
    ({}, {"cases": {}}, {"cases": [None]}),
)
def test_malformed_fixture_set_structure_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fixture_set: object,
) -> None:
    fixture_path = tmp_path / "fixtures.json"
    fixture_path.write_text(json.dumps(fixture_set), encoding="utf-8")

    result = invoke_main(monkeypatch, capsys, fixture_path, [])

    assert_failure(*result)


@pytest.mark.parametrize("missing_field", ("extractor_output", "dialogue"))
def test_selected_fixture_missing_required_data_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    missing_field: str,
) -> None:
    fixture_set: dict[str, Any] = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    selected = next(case for case in fixture_set["cases"] if case["id"] == "golden_001")
    del selected[missing_field]
    fixture_path = tmp_path / "fixtures.json"
    fixture_path.write_text(json.dumps(fixture_set), encoding="utf-8")

    result = invoke_main(monkeypatch, capsys, fixture_path, ["golden_001"])

    assert_failure(*result)
