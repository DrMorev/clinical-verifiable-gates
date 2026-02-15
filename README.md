# clinical-verifiable-gates

Deterministic verifier kernel for medical RLVR: extractor contract, PASS/BLOCK/ABSTAIN, Silence gate.

## What this is (v0.1)
A portfolio-grade, vendor-agnostic OSS verification kernel for safety-sensitive clinical dialogue:
- Evidence-grounded Extractor Contract (Text → JSON, UNKNOWN-by-default)
- Deterministic Verifier (Python) returning PASS/BLOCK/ABSTAIN + reason codes
- Silence Gate to quantify hallucinated slot filling

## Boundaries (non-negotiable)
- Research/evaluation tooling only. No clinical deployment claims.
- PASS ≠ safe advice (PASS = “no rule violation detected under this spec”).
- No copyrighted guideline text shipped in this repo.
- ML may be used for extraction only; final adjudication is deterministic code.

## Related work + naming
- Not affiliated with Med-RLVR authors; “RLVR” mention is framing only.
- Canon memo: docs/memo_v1.4.md
- Comparison: docs/compare_med_rlvr.md

## Docs
- Canon memo: docs/memo_v1.4.md
- Decision log: docs/decision_log.md
