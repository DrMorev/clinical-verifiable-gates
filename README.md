# clinical-verifiable-gates

Clinical Verifiable Gates is an open-source reference implementation of deterministic runtime gates for safety-sensitive clinical AI outputs.

## Current implementation status

CVG is a deterministic runtime qualification layer and an open-source research and engineering artifact focused on explicit contracts, evidence, reason codes, and PASS / BLOCK / ABSTAIN decisions.

The repository currently contains:

- executable structural contract adjudication;
- deterministic evidence grounding and polarity-conflict containment;
- high-level `verify_case` composition;
- PASS / BLOCK / ABSTAIN verdicts with ordered reason codes;
- evaluation-only Silence-oracle functionality;
- nine approved machine-readable JSON fixtures;
- an automated pytest suite;
- a canonical reviewer demo;
- GitHub Actions CI.

## Reviewer path

Supported Python version: 3.11.

Install development dependencies:

```text
python -m pip install -r requirements-dev.txt
```

Run the test suite:

```text
python -m pytest -q
```

Run the default reviewer demo (`golden_001`):

```text
python -m eval.demo
```

Explicit fixture examples:

```text
python -m eval.demo golden_001
```

```json
{"decision":"ABSTAIN","reason_codes":["RC_AD_RED_FLAG_PRESENT"],"abstain_mode":"ESCALATE","schema_ref":"core/schemas/ad_extractor_contract_v0.1.schema.json","taxonomy_version":"v0.1"}
```

```text
python -m eval.demo pass_all_critical_no_001
```

```json
{"decision":"PASS","reason_codes":[],"abstain_mode":null,"schema_ref":"core/schemas/ad_extractor_contract_v0.1.schema.json","taxonomy_version":"v0.1"}
```

```text
python -m eval.demo contract_missing_fields_001
```

```json
{"decision":"BLOCK","reason_codes":["RC_CONTRACT_MISSING_FIELDS"],"abstain_mode":null,"schema_ref":"core/schemas/ad_extractor_contract_v0.1.schema.json","taxonomy_version":"v0.1"}
```

## Boundaries (non-negotiable)

- Research and engineering tooling only. No clinical deployment claims.
- CVG is not a medical device or a replacement for clinical judgment.
- PASS means only that no rule violation was detected under the applicable verifier specification. It does not mean clinically safe, clinically correct, diagnostically cleared, validated, or deployment-ready.
- The Silence oracle is evaluation-only.
- CVG makes no claim of clinical validation, diagnostic accuracy, comprehensive disease coverage, autonomous clinical use, deployment readiness, or regulatory status.
- CVG does not implement model extraction.
- No copyrighted guideline text shipped in this repo.

## Related Work

- Med-RLVR and medical verifiable-reward work are adjacent prior art only.
- CVG is not a Med-RLVR project, an RLVR or RLHF implementation, a reward model, or a training-time safety layer.
- CVG is not affiliated with the Med-RLVR authors.
- Historical design memo: docs/memo_v1.4.md
- Comparison: docs/compare_med_rlvr.md

## Docs

- Historical design memo: docs/memo_v1.4.md
- Decision log: docs/decision_log.md
