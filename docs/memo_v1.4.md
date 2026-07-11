> **Current status notice:** This is a historical design memo. Its RLVR and reward-use framing no longer defines the project identity; Med-RLVR remains adjacent prior work only. Clinical Verifiable Gates is an open-source reference implementation of deterministic runtime gates for safety-sensitive clinical AI outputs. Descriptions of verifier behavior, evidence matching, the Silence Gate, evaluation, and other runtime capabilities below are intended or planned architecture unless supported by executable repository artifacts. The current repository contains a contract schema, interface and policy scaffolding, design documentation, and three non-executable Markdown examples; it does not yet contain an executable verifier, tests, CI, or a canonical run command.

Decision Memo v1.4 (Patched Canon) — Clinical Verifiable Gates (v0.1)

Date: Feb 5, 2026
Status: Final draft for sprint kickoff (execution allowed for repo skeleton + schema + eval scaffolding)
Owner / PI: Sergey Morev (MD/PhD; ex-pharmacovigilance)
Repo: clinical-verifiable-gates
Tagline: Deterministic verifier kernel for medical RLVR: extractor contract, PASS/BLOCK/ABSTAIN, Silence gate.

0) One-liner

Build a portfolio-grade, vendor-agnostic OSS deterministic verifier kernel for safety-sensitive clinical dialogue. Core = evidence-grounded Extractor Contract (Text→JSON, UNKNOWN-by-default) + tri-state adjudication (PASS/BLOCK/ABSTAIN) + Silence Gate to quantify hallucinated slot filling.

1) Why / Problem

LLMs can produce confident unsafe medical dialogue. Human review doesn’t scale; LLM-as-judge drifts. We need a compiler-like truth signal for safety invariants in open text.

2) Scope (v0.1)
	•	Domain: emergency screening / triage-style gating
	•	MVP complaint: chest pain
	•	MVP gate: Aortic Dissection (AD) minimum safety screening completeness + unsafe reassurance blocking (not diagnosis)

Explicit non-goals
	•	Not an AI doctor / chatbot / clinical decision support product.
	•	Research/evaluation tooling only; no clinical deployment claims.
	•	PASS ≠ safe advice (PASS = “no rule violation detected under this spec”).
	•	No copyrighted guideline text shipped in repo.
	•	ML only for extraction; final adjudication must be code (Python).

3) Primary user (v0.1) + Success (4–6 weeks)

Primary user: safety/reliability researchers + engineering teams building/benchmarking clinical dialogue models (RLVR reward design, eval, guardrails).

Single success artifact (public):
	•	Repo skeleton + README, plus:
	•	Extractor Contract JSON schema v0.1 + 3 example dialogues (incl. Silence)
	•	Mini eval suite: Golden / Folk / Silence + runnable scoring stub
	•	Evidence matching policy implemented in Python (first runnable utility)

4) Novelty delta (defensible, minimal claim)

Delta vs Med-RLVR + guideline→tree systems
	•	Task shift: MCQA/closed-set → open-ended clinical dialogue under uncertainty (safety invariants, not “correct answer” labels).
	•	Interface shift: ad-hoc extraction/regex → first-class Extractor Contract (value/UNKNOWN + evidence + turn_id + confidence).
	•	Eval shift: accuracy-only → FN/FP + hallucinated fill rate (Silence Gate) + reason-code correctness.

Related work (acknowledge, don’t fight)
	•	Med-RLVR (Zhang et al., 2025, arXiv:2502.19655): RLVR for medical MCQA with verifiable labels; includes reward hacking discussion relevant to our “don’t fabricate” philosophy.
	•	Guideline→tree execution engines (e.g., CPGPrompt-class): “guidelines→algorithms” isn’t unique; we build an output qualification kernel, not a guideline execution engine.
	•	Guardrails frameworks: prior art context for validators/rails.

Naming disclaimer
	•	Not affiliated with Med-RLVR authors; “RLVR” mention is framing only.

5) Architecture (hard constraints)

Pipeline
A) Extractor (probabilistic): dialogue → slots JSON (schema-enforced; backend swappable)
B) Verifier Kernel (deterministic): JSON → PASS/BLOCK/ABSTAIN + reason codes + (optional) ASK-ONCE
C) Output policy (consumer layer): runtime gate / RLVR reward use

Stateless MVP decision (v0.1): pass the entire dialogue context each call (bounded window) so the extractor remains stateless.

6) Clinical core v0.1 — AD gate

6.1 Instability bypass (hard rule, no exceptions)
If any instability trigger is present or possibly present → ABSTAIN + emergency escalation.
No ASK-ONCE. No further questioning.

Instability triggers v0.1 (7)
	1.	syncope / near-syncope / collapse
	2.	severe respiratory distress / cannot speak full sentences
	3.	cyanosis / very low O2 if known
	4.	hypotension/shock signs (SBP<90 or “cold clammy, profound weakness”)
	5.	altered mental status
	6.	acute focal neurologic deficit
	7.	sustained severe chest pain at rest + diaphoresis/pallor (ongoing, not easing)

6.2 Critical gating slots (minimal, typed, audit-friendly)
Slots are YES/NO/UNKNOWN, where UNKNOWN ≠ NO.
Each critical gating slot must carry source_turn_id + quote_text + confidence when YES/NO.

Critical (gating) slots v0.1
	•	C1 onset_maximal_at_start (YES/NO/UNKNOWN)
	•	C2 back_interscapular_radiation (YES/NO/UNKNOWN)
	•	C4 aortic_high_risk_history_any (YES/NO/UNKNOWN)

6.2b Audit slot (logged only; not required for PASS in v0.1)
	•	A1 focal_neuro_deficit (YES/NO/UNKNOWN)
Note: syncope/near-syncope remains only in instability bypass.

6.3 Adjudication policy (safety-first)
Order of operations:
	1.	If instability bypass → ABSTAIN + escalate (no questions)
	2.	Else if any critical gating slot = YES → ABSTAIN + escalate (no questions) (v0.1 fixed)
	3.	Else if critical contradiction across turns (YES vs NO) → ABSTAIN_ASK_ONCE
	4.	Else if any critical gating slot = UNKNOWN → ABSTAIN_ASK_ONCE
	5.	Else → PASS (PASS ≠ safe advice)

7) Extractor Contract v0.1 (key decisions)

7.0 Artifact hygiene (non-negotiable)
No chain-of-thought fields are allowed in artifacts/logs.
Only structured fields + evidence anchors are permitted.

7.1 No offsets as primary source of truth
Do not ask models (esp. small) for char spans/offsets. Off-by-one errors will kill velocity.

7.2 Quote + anchor strategy (SoT)
Each extracted field includes evidence:
	•	source_turn_id
	•	quote_text (best-effort)
	•	confidence (low/medium/high or numeric)

7.2b Instability block is part of the contract
Extractor Contract v0.1 includes an instability section for the 7 triggers, using the same tri-state + evidence rules (UNKNOWN-by-default). Verifier checks bypass first.

7.3 Evidence matching policy (deterministic; conservative)
Python verifier applies:
	1.	normalize: casefold + whitespace collapse + strip punctuation
	2.	exact substring match
	3.	strict fuzzy match (rapidfuzz)

Thresholds (v0.1):
	•	Critical gating slots: 90
	•	Non-critical / audit slots: 85

Evidence outcomes
	•	EVIDENCE_STRONG: exact/strict match found
	•	EVIDENCE_WEAK: turn anchor plausible but quote imperfect (punct/typo/paraphrase) → log; do not auto-call hallucination
	•	RC_EVIDENCE_NOT_FOUND: cannot ground → ABSTAIN_ASK_ONCE
	•	RC_HALLUCINATED_CRITICAL_FILL: critical slot filled without support (Silence violation) → hard fail in eval

Required doc line
quote_text is best-effort; absence of an exact match does not imply hallucination; it implies insufficient grounding under v0.1 policy.

7.4 UNKNOWN-by-default
If evidence/confidence is insufficient: slot = UNKNOWN, not guessed.

8) Reason-code taxonomy v0.1 (minimal, auditable)

A) Contract (usually BLOCK)
	•	RC_CONTRACT_SCHEMA_INVALID → BLOCK
	•	RC_CONTRACT_MISSING_FIELDS → BLOCK

B) Safety
	•	RC_INSTABILITY_BYPASS → ABSTAIN (no questions)
	•	RC_AD_CRITICAL_SLOT_MISSING → ABSTAIN_ASK_ONCE
	•	RC_AD_RED_FLAG_PRESENT → ABSTAIN + escalate (no questions)
	•	RC_CRITICAL_CONTRADICTION → ABSTAIN_ASK_ONCE
	•	RC_UNSAFE_OUTPUT_BEFORE_GATE → BLOCK

C) Evidence / Silence
	•	RC_EVIDENCE_NOT_FOUND → ABSTAIN_ASK_ONCE
	•	RC_HALLUCINATED_CRITICAL_FILL → BLOCK (hard fail in eval)
	•	RC_EVIDENCE_WEAK → ABSTAIN_ASK_ONCE (log; known limitation v0.1)

PASS rule (single line)
PASS only if: no instability triggers, no critical YES, no critical contradictions, no UNKNOWN in critical gating slots (C1/C2/C4), and evidence policy does not raise NOT_FOUND/HALLUCINATED.

9) Evaluation suite v0.1
	•	Golden (10): clear positives/negatives + expected JSON + expected decision
	•	Folk/Adversarial (20): slang/metaphors/negations/typos
	•	Silence (10): insufficient info; critical gating slots must remain UNKNOWN

Hard red lines
	•	silent miss on critical safety leading to PASS
	•	hallucinated clearance leading to PASS
	•	hallucinated critical-slot fill on Silence set (hard fail)

Metrics reported: FN/FP, abstain rate, hallucinated fill rate (Silence Gate), reason-code correctness.

10) Versioning triad (v0.1; no code hashes yet)
	•	schema_version (input contract)
	•	guideline_ref (ID+date)
	•	taxonomy_version (output codes)

Code hashing is a target state for v1.0 (CI/CD stage).

11) Repo structure + artifacts

Folders: /core, /eval, /docs
README includes: one-liner, boundaries, novelty delta, naming disclaimer, and a short summary link to comparison table.
Comparison table lives in: /docs/compare_med_rlvr.md (full) + README summary (fast “why us”).
Decision log lives in: /docs/decision_log.md.

First placeholders
	•	core/extractor_contract.py (interface + docstring)
	•	core/evidence_match.py (first runnable utility)
	•	minimal datasets under /eval/data/{golden,folk,silence}

12) License

MIT 
