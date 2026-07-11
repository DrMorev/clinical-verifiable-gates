# clinical-verifiable-gates

Clinical Verifiable Gates is an open-source reference implementation of deterministic runtime gates for safety-sensitive clinical AI outputs.

## Current implementation status

CVG is a deterministic runtime qualification layer and an open-source research and engineering artifact focused on explicit contracts, evidence, reason codes, and PASS / BLOCK / ABSTAIN decisions.

The repository currently contains:

- a contract schema;
- interface and policy scaffolding;
- design documentation;
- three non-executable Markdown examples.

It does not yet contain an executable deterministic verifier, executable PASS / BLOCK / ABSTAIN adjudication, implemented evidence matching, an executable Silence Gate or evaluation suite, tests, CI, or a canonical run command. Deterministic final adjudication remains an architectural requirement, not a claim about the current implementation.

## Boundaries (non-negotiable)

- Research and engineering tooling only. No clinical deployment claims.
- CVG is not a medical device or a replacement for clinical judgment.
- PASS means only that no rule violation was detected under the applicable verifier specification. It does not mean clinically safe, clinically correct, diagnostic clearance, or deployment readiness.
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
