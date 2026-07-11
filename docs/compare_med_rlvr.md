# Med-RLVR vs Clinical Verifiable Gates (v0.1)

## Related Work

Clinical Verifiable Gates is an open-source reference implementation of deterministic runtime gates for safety-sensitive clinical AI outputs. CVG is not a Med-RLVR project, an RLVR or RLHF implementation, a reward model, or a training-time safety layer. Med-RLVR is discussed here only as adjacent prior work.

The CVG column below describes intended architecture unless it explicitly refers to an artifact present in the repository. The current repository contains a contract schema, interface and policy scaffolding, design documentation, and three non-executable Markdown examples; it does not yet contain an executable verifier, adjudication, evidence matcher, Silence Gate, evaluation suite, tests, CI, or canonical run command. CVG is not a treatment model, medical device, replacement for clinical judgment, or clinical deployment claim.

| Axis | Med-RLVR (Zhang et al., 2025, arXiv:2502.19655) | CVG intended architecture (v0.1) |
|---|---|---|
| Primary task | Medical MCQA (closed-set) | Open-ended clinical dialogue gating (uncertainty-first) |
| Core mechanism | RLVR with verifiable labels | Intended: Extractor Contract + deterministic runtime gates producing PASS/BLOCK/ABSTAIN |
| What is “verifiable” | Answer correctness against labels | Intended: rule invariants + evidence anchoring + reason codes |
| Failure focus | Reward hacking / reasoning shortcuts | Intended: hallucinated slot filling (Silence Gate) and unsafe reassurance blocking |
| Output | Model behavior improvement | Intended: runtime qualification/gating signal for downstream systems |
| Determinism | No (training/inference are stochastic) | Architectural requirement: final adjudication is deterministic code; not yet implemented |
| Portability | Tied to training setup/model | Intended: swap the extractor backend while retaining deterministic gates |
| Evidence grounding | Not the central artifact | Contract schema represents `source_turn_id + quote_text + confidence`; executable validation is not implemented |
| Known limitations | Reward hacking, generalization gaps | Current: no executable verifier or evaluation suite; intended matching may depend on extractor quality |

Notes:
- CVG does not claim to be a standard for medicine.
- Med-RLVR and RLVR are referenced as adjacent prior work only; CVG is not affiliated with the Med-RLVR authors.
