# Med-RLVR vs Clinical Verifiable Gates (v0.1)

This repo is **not** a treatment model and does not claim clinical deployment. It is a **deterministic verifier kernel** for safety-sensitive clinical dialogue.

| Axis | Med-RLVR (Zhang et al., 2025, arXiv:2502.19655) | clinical-verifiable-gates (v0.1) |
|---|---|---|
| Primary task | Medical MCQA (closed-set) | Open-ended clinical dialogue gating (uncertainty-first) |
| Core mechanism | RLVR with verifiable labels | Extractor Contract + deterministic verifier (PASS/BLOCK/ABSTAIN) |
| What is “verifiable” | Answer correctness against labels | Rule invariants + evidence anchoring + reason codes |
| Failure focus | Reward hacking / reasoning shortcuts | Hallucinated slot filling (Silence Gate), unsafe reassurance blocking |
| Output | Model behavior improvement | Qualification/gating signal for downstream systems (or reward shaping) |
| Determinism | No (training/inference are stochastic) | Yes (final adjudication is code) |
| Portability | Tied to training setup/model | Vendor-agnostic: swap extractor backend, keep verifier |
| Evidence grounding | Not the central artifact | Required: `source_turn_id + quote_text + confidence` |
| Known limitations | Reward hacking, generalization gaps | Extractor quality dependency; conservative matching may increase abstain rate |

Notes:
- We intentionally avoid claiming a “standard” for medicine; we provide a reproducible **kernel**.
- “RLVR” mention is framing only; no affiliation with Med-RLVR authors.
