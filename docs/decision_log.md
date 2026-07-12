# Decision Log — Clinical Verifiable Gates

Format:
- **D-0xx** — Decision
- **Why / trade-off**
- **Revisit trigger**

---

## D-001 — Repo name + tagline
**Decision:** repo = `clinical-verifiable-gates`  
Tagline: “Deterministic verifier kernel for medical RLVR: extractor contract, PASS/BLOCK/ABSTAIN, Silence gate.”  
**Why / trade-off:** Avoid affiliation optics; keep RLVR framing; make function explicit (“gates”, “deterministic”).  
**Revisit trigger:** If “clinical” creates expectation of clinical deployment.

## D-002 — Scope boundaries (v0.1)
**Decision:** Research/evaluation tooling only; no clinical deployment claims; PASS ≠ safe advice; no copyrighted guideline text in repo.  
**Why / trade-off:** Liability control + reviewer hygiene; keeps project defensible.  
**Revisit trigger:** If we add deployment artifacts or integrations.

## D-003 — Deterministic adjudication
**Decision:** Final verifier must be code (Python). ML allowed only for extraction.  
**Why / trade-off:** “Verifiable rewards” premise; auditable outputs.  
**Revisit trigger:** If we can prove LLM-verifier invariants (unlikely).

## D-004 — Tri-state adjudication
**Decision:** Outcomes: PASS / BLOCK / ABSTAIN (policy distinguishes ABSTAIN_ASK_ONCE vs ABSTAIN_ESCALATE).  
**Why / trade-off:** Bounded uncertainty beats guessing.  
**Revisit trigger:** If abstain rate becomes unusable.

## D-005 — Instability bypass policy
**Decision:** Any instability trigger present/possible => **ABSTAIN + escalate**, **no questions**.  
**Why / trade-off:** Clinically defensible; avoids “chatting through instability”.  
**Revisit trigger:** If we formalize “possible” thresholds differently.

## D-006 — Red-flag policy (AD v0.1)
**Decision:** Any critical gating slot = YES => **ABSTAIN + escalate**, no ASK-ONCE. ASK-ONCE only for UNKNOWN (no bypass, no YES).  
**Why / trade-off:** Safety-first v0.1; reduces unsafe reassurance risk.  
**Revisit trigger:** If evidence supports safe clarification even with YES (future).

## D-007 — Evidence source strategy
**Decision:** No offsets in prompts. Use quote + source_turn_id + confidence; offsets computed in Python if needed.  
**Why / trade-off:** Avoid off-by-one/index hallucinations; keep extractor simple.  
**Revisit trigger:** If we introduce structured input markers.

## D-008 — Evidence matching policy
**Decision:** normalize(casefold + whitespace + strip punctuation) -> exact substring -> strict fuzzy (rapidfuzz). Thresholds: critical 90, non-critical 85.  
**Why / trade-off:** Precision over recall; avoid “confirming a lie”.  
**Revisit trigger:** Negation-specific tuning (e.g., “no pain” vs “now pain”).

## D-009 — Silence gate
**Decision:** Include Silence set; hallucinated critical-slot fill is hard fail in eval.  
**Why / trade-off:** Measures “don’t fabricate” explicitly; differentiator.  
**Revisit trigger:** If label noise requires redefining “hallucinated”.

## D-010 — Versioning triad (no code hashes in v0.1)
**Decision:** `schema_version`, `guideline_ref`, `taxonomy_version` are required for reproducibility. Code hashes are target state (v1.0).  
**Why / trade-off:** Low overhead now; reproducible logs.  
**Revisit trigger:** When CI/CD automation lands.

## D-011 — Comparison table placement
**Decision:** Full comparison table lives in `/docs/compare_med_rlvr.md` with README link/summary.  
**Why / trade-off:** Keep memo focused; table helps outsiders quickly.  
**Revisit trigger:** If memo becomes the public landing page.

## D-012 — Artifact hygiene: no chain-of-thought
**Decision:** No chain-of-thought fields are allowed in artifacts/logs (schemas, datasets, eval records).  
**Why / trade-off:** Prevents leaking internal reasoning; keeps artifacts clean and portable.  
**Revisit trigger:** None (permanent unless policy changes).

## D-013 — AD v0.1 contract shape (gating vs audit)
**Decision:** AD gating slots = C1/C2/C4. C3 is not gating; kept as audit slot A1 (focal neuro deficit). Syncope/near-syncope remains only in instability bypass.  
**Why / trade-off:** Removes duplication; aligns with clinical bypass logic.  
**Revisit trigger:** If we expand to additional gates or revise AD slot set.


## D-014 — Instability trigger encoding
**Decision:** Instability triggers use value enum: PRESENT / ABSENT / POSSIBLE / UNKNOWN.  
**Why / trade-off:** “possible present” must deterministically trigger bypass; don’t infer it from confidence.  
**Revisit trigger:** If we standardize probabilistic thresholds for POSSIBLE.

## D-015 — Contract schema location + naming
**Decision:** Canon schema file: `core/schemas/ad_extractor_contract_v0.1.schema.json`.  
**Why / trade-off:** Treat contract as core API; stable path for tooling and CI.  
**Revisit trigger:** If we split into multiple gate schemas or introduce a top-level registry.

## D-016 — Canonical CVG identity supersedes RLVR framing

**Decision:** Clinical Verifiable Gates is an open-source reference implementation of deterministic runtime gates for safety-sensitive clinical AI outputs. CVG is a deterministic runtime qualification layer, not an RLVR or RLHF implementation, reward model, or training-time project. Med-RLVR and medical verifiable-reward work remain adjacent prior art only. Deterministic final adjudication remains an active architectural requirement; this requirement does not imply that executable adjudication is present in the current repository. This decision supersedes the identity and tagline framing in D-001 without altering any clinical decision or reason-code semantics.

**Why / trade-off:** Separates CVG's runtime qualification identity from adjacent reward-training work and keeps public claims aligned with observed executable artifacts.

**Revisit trigger:** If the project identity or implementation boundary changes through an explicitly approved decision.

## D-017 — Instability UNKNOWN handling

**Decision:**

- PRESENT or POSSIBLE remains instability bypass: ABSTAIN, ESCALATE, `RC_INSTABILITY_BYPASS`.
- If no instability bypass applies and any instability slot is UNKNOWN, the contract cannot PASS.
- That state produces ABSTAIN, ASK_ONCE, `RC_INSTABILITY_SLOT_MISSING`.
- Critical AD YES retains escalation precedence over missing-information handling.
- If both instability and critical AD information are missing after escalation checks, ordered reason codes are:
  1. `RC_INSTABILITY_SLOT_MISSING`
  2. `RC_AD_CRITICAL_SLOT_MISSING`
- PASS requires every instability slot to be ABSENT and every critical AD slot C1/C2/C4 to be grounded NO.

**Why:**

- UNKNOWN must not be treated as ABSENT.
- The current schema explicitly permits instability UNKNOWN.
- Deterministic total adjudication requires an explicit non-PASS result for this state.

**Revisit trigger:** If the instability contract, clarification policy, or slot taxonomy changes.

## D-018 — Evidence grounding and Silence-oracle boundary

**Decision:**

- adjudicate_contract(payload) remains the structural-only primitive.
- Runtime evidence verification is exposed through verify_evidence(payload, dialogue) -> EvidenceVerificationResult.
- High-level runtime verification is exposed through verify_case(payload, dialogue) -> CaseVerificationResult.
- CaseVerificationResult contains an immutable verdict: VerifierResult and immutable evidence: EvidenceVerificationResult.
- The existing core/evidence_match.py placeholder is the canonical production module to be made executable; no parallel core/evidence.py module is introduced.
- Contract validation always runs first and preserves existing contract BLOCK results unchanged.
- Malformed dialogue input produces BLOCK, abstain_mode=None, RC_DIALOGUE_INVALID.
- Dialogue is malformed if:
  - the root is not a non-empty list;
  - a turn is not an object;
  - turn_id is missing, Boolean, or not an integer;
  - a turn_id is duplicated;
  - text is missing or not a string;
  - any dialogue turn exceeds meta.last_turn_id;
  - the maximum dialogue turn_id does not equal meta.last_turn_id.
- Dialogue turn IDs need not be contiguous, and input list order does not affect verification.
- A valid evidence anchor whose source_turn_id does not exist in the bounded dialogue, including a value above meta.last_turn_id, is an ordinary evidence-grounding failure rather than a dialogue-structure failure.
- UNKNOWN slots are not quote-matched and retain evidence: null.
- All non-UNKNOWN instability slots, critical AD slots C1/C2/C4, and audit slot A1 are deterministically checked.
- Instability and C1/C2/C4 evidence use threshold 90.
- Audit A1 evidence uses threshold 85.
- Normalization applies Unicode-aware casefold, replaces Unicode punctuation-category characters with spaces, collapses whitespace, and strips leading/trailing whitespace.
- NFC and NFKC normalization are not added in v0.1.
- Matching uses normalized anchored-turn exact substring first, then rapidfuzz.fuzz.partial_ratio(..., processor=None).
- A fuzzy score matches when score >= threshold.
- Exact matching remains permitted for short quotes.
- Fuzzy matching is disabled unless the normalized quote contains at least 8 code points and at least 2 non-empty whitespace-delimited tokens.
- Empty normalized quotes are not grounded.
- Matching is restricted to the declared source_turn_id; text in another turn does not ground the evidence.
- Confidence remains metadata and does not alter matching or thresholds in v0.1.
- rapidfuzz>=3.14.5,<3.15 is the approved runtime dependency.
- No silent fallback scorer is permitted.
- Ordinary inability to ground evidence produces RC_EVIDENCE_NOT_FOUND; failure to match a quote does not by itself establish hallucination.
- Instability PRESENT/POSSIBLE and critical AD YES retain structural ESCALATE precedence even when their evidence is not grounded.
- In an escalation result, evidence failures remain visible in the evidence report but do not replace or supplement the structural verdict reason code.
- If no escalation applies, ASK_ONCE reason codes are ordered:
  1. RC_INSTABILITY_SLOT_MISSING
  2. RC_AD_CRITICAL_SLOT_MISSING
  3. one deduplicated RC_EVIDENCE_NOT_FOUND
- Detailed evidence issues remain individually represented in canonical slot order even when the verdict contains one deduplicated evidence reason code.
- Audit evidence failures are recorded but do not alter the runtime verdict in P4.
- Runtime PASS requires structural PASS plus grounded evidence for every non-UNKNOWN instability and C1/C2/C4 slot.
- RC_EVIDENCE_WEAK remains deferred in P4.
- Silence-oracle adjudication is evaluation-only and accepts explicit immutable trusted context containing unsupported critical AD slots.
- Silence-oracle code must not inspect fixture IDs, fixture categories, filenames, rationale text, expected results, or expected reason codes.
- A trusted oracle-labelled critical slot produces BLOCK / RC_HALLUCINATED_CRITICAL_FILL only when that slot is non-UNKNOWN in the extractor output.
- The trusted oracle label, not an exact or fuzzy mismatch, authorizes hallucinated-fill classification.
- Evaluation precedence is:
  1. contract failure;
  2. malformed dialogue;
  3. trusted Silence-oracle violation;
  4. ordinary runtime verification.
- For P4, trusted oracle context is supplied explicitly by evaluation tests; no new oracle-label artifact or fixture field is introduced.

**Why / trade-off:**

- Structural escalation must not be downgraded because an extractor supplied weak or fabricated evidence for a potentially dangerous state.
- Runtime grounding failure and trusted evaluation-only hallucination classification are different claims and must remain mechanically separated.
- Returning both the verdict and ordered evidence report preserves auditability without contaminating the minimal verdict taxonomy.
- A single dialogue-invalid reason code provides deterministic fail-closed handling without broad taxonomy expansion.
- Explicit normalization, scorer version, thresholds, and short-quote limits reduce hidden preprocessing and fuzzy-match drift.
- Audit grounding remains observable while preserving the approved P3 rule that audit slots do not control PASS.

**Revisit trigger:**

- If contradiction detection, semantic entailment, confidence-based thresholds, multilingual normalization, RC_EVIDENCE_WEAK, production oracle metadata, or a formal dialogue JSON Schema is introduced.

## D-019 — Polarity containment for evidence grounding

**Decision:**

### Public boundary

- P5 adds deterministic polarity-conflict containment to evidence grounding.
- It does not implement general negation parsing, semantic entailment, extraction correction, or clinical-language understanding.
- A match may be rejected when an approved deterministic guard establishes explicit polarity conflict or approved ambiguity.
- Absence of a recognised pattern does not establish polarity and does not by itself reject otherwise valid evidence.

### Value polarity

- PRESENT, POSSIBLE, and YES map to positive polarity.
- ABSENT and NO map to negative polarity.
- UNKNOWN remains skipped.

### Existing behavior preserved

- Existing normalization remains unchanged.
- Evidence remains restricted to its declared source_turn_id.
- Thresholds remain 90 for instability and C1/C2/C4, and 85 for A1.
- Confidence remains metadata only.
- No explicit negation cue is required for ABSENT or NO.
- Cue-free negative evidence such as breathe normally, alert and thinking clearly, and built up gradually remains eligible.
- Existing nine fixture verdicts remain unchanged.

### Pattern mechanics

- Patterns are matched against normalized whitespace-delimited tokens.
- Pattern matching uses whole-token contiguous sequences.
- Character-substring matching inside another token is forbidden.
- Each slot has approved positive-support and negative-support patterns.
- Collect positive and negative pattern spans.
- A shorter hit fully contained in a strictly longer opposite-polarity hit is suppressed.
  - Example: alert is suppressed inside not alert.
  - Example: maximal at the start is suppressed inside rather than being maximal at the start.
- After suppression:
  - positive hits only → positive;
  - negative hits only → negative;
  - both → ambiguous;
  - neither → neutral.
- Opposite polarity or ambiguous polarity is a conflict.
- Same polarity or neutral is not a conflict.

### Approved slot-pattern lexicon v0.1

#### instability.syncope_or_collapse

- positive:
  fainted; fainting; passed out; passing out; collapsed; collapse
- negative:
  no fainting; no passing out; no collapse; not fainted; did not faint; didn t faint; did not pass out; didn t pass out; not collapsed; did not collapse; didn t collapse; not fainted or collapsed

#### instability.severe_respiratory_distress

- positive:
  cannot breathe; can t breathe; could not breathe; couldn t breathe; gasping; struggling to breathe; severe shortness of breath
- negative:
  breathing is okay; breathing okay; breathe normally; breathing normally; speak in full sentences; speaking in full sentences; no shortness of breath; not short of breath

#### instability.cyanosis_or_low_o2

- positive:
  lips are blue; blue lips; oxygen is low; oxygen reading is low; low oxygen; low o2; abnormal oxygen
- negative:
  lips are not blue; lips not blue; oxygen is normal; oxygen reading is normal; normal oxygen; normal o2

#### instability.hypotension_or_shock_signs

- positive:
  blood pressure is low; low blood pressure; hypotensive; cold and clammy; cold or clammy; in shock
- negative:
  blood pressure is normal; normal blood pressure; not cold or clammy; not cold and clammy

#### instability.altered_mental_status

- positive:
  confused; disoriented; not alert; hard to wake; unresponsive; not thinking clearly
- negative:
  alert; thinking clearly; oriented; not confused; not disoriented

#### instability.acute_focal_neuro_deficit

- positive:
  new weakness; new numbness; speech trouble; slurred speech; facial droop; one sided weakness; one sided numbness
- negative:
  no new weakness numbness or speech trouble; no new weakness or numbness; no new weakness; no new numbness; no speech trouble; no weakness; no numbness; speech is normal

#### instability.severe_pain_at_rest_with_diaphoresis_or_pallor

- positive:
  severe pain at rest; pain is severe at rest; sweaty; sweating; diaphoretic; pale; pallor
- negative:
  pain is not severe at rest; not severe at rest; not sweaty; not sweaty or pale; not sweating; not pale; no sweating; no pallor; no chest pain

#### ad_gate.C1_onset_maximal_at_start

- positive:
  maximal at the start; maximal at start; maximal immediately; worst pain right away; max pain right away; instantly became the worst pain; sudden onset; started suddenly; out of nowhere
- negative:
  built up gradually; gradual onset; not maximal at the start; not maximal at start; rather than being maximal at the start; rather than maximal at the start; denies sudden onset; no sudden onset; not sudden onset

#### ad_gate.C2_back_interscapular_radiation

- positive:
  upper back between the shoulder blades; between the shoulder blades; interscapular; spread to my back; spreads to my back; goes to my upper back; radiates to my back
- negative:
  does not spread to my back or between my shoulder blades; does not spread to the back or between the shoulder blades; does not spread to my back; doesn t spread to my back; no pain in my back; nothing in my back; not in my back; no back radiation

#### ad_gate.C4_aortic_high_risk_history_any

- positive:
  aortic aneurysm; known aortic disease; marfan syndrome; ehlers danlos; bicuspid aortic valve; family history of aortic dissection; prior aortic surgery
- negative:
  none of the listed aortic high risk history; no aortic high risk history; no known aortic disease; no marfan syndrome; no family history of aortic dissection; no prior aortic surgery

#### audit.A1_focal_neuro_deficit

- reuses exactly the positive and negative pattern sets of:
  instability.acute_focal_neuro_deficit

No unlisted synonym or phrase is inferred.

### Global negation signature

After existing normalization, these are approved negation cues:

Single-token cues:

no; not; never; none; nothing; neither; nor; without; nah; deny; denies; denied; cannot

Multi-token cues:

can t; could not; couldn t; do not; don t; does not; doesn t; did not; didn t; is not; isn t; are not; aren t; was not; wasn t; were not; weren t; has not; hasn t; have not; haven t; had not; hadn t; will not; won t; would not; wouldn t; should not; shouldn t

The negation signature is binary: cue present or cue absent.

- Negation-signature equality is computed only between:
  - the normalized quote; and
  - the matched destination span.
- The expanded five-token local context is not used for negation-signature equality.
- The expanded context is used only for current-slot pattern classification and the bounded ambiguity guard.

### Approved ambiguous phrases

An approved ambiguous phrase fails closed when:

- it occurs in the quote;
- it overlaps the matched destination span; or
- it overlaps a surviving current-slot pattern span in the expanded context.

An unrelated ambiguous phrase elsewhere in the five-token expansion is ignored.

Approved ambiguous phrases:

not only; not uncommon; not impossible; not unlikely; not without; cannot rule out; can t rule out; could not rule out; couldn t rule out; no absence of; not no; denies no; denied no

Multiple ordinary negative statements are not automatically treated as double negation.

### Exact-match path

- Locate the normalized quote as a contiguous whole-token sequence in the normalized anchored turn.
- For each occurrence, select:
  - the occurrence tokens;
  - up to five tokens before;
  - up to five tokens after.
- The matched destination span is the exact whole-token quote occurrence.
- Binary negation signatures are compared between the quote and that occurrence only.
- Current-slot positive and negative patterns are evaluated in the expanded context.
- Opposite or ambiguous current-slot polarity still fails closed.
- If occurrences produce mixed compatible and conflicting contexts, fail closed.
- For a quote shorter than 8 code points or containing fewer than 2 tokens, exact grounding additionally requires an approved same-polarity slot pattern in the quote or at least one candidate context.
- Otherwise a conflict-free exact occurrence produces GROUNDED_EXACT, score 100.0.

### Fuzzy-match path

- Fuzzy remains disabled for quotes shorter than 8 code points or containing fewer than 2 tokens.
- Use:
  rapidfuzz.fuzz.partial_ratio_alignment(..., processor=None)
- Use its score as the existing partial-ratio score and its destination span only to identify the local anchored-turn context.
- Convert the destination character span deterministically to every overlapping normalized turn token.
- Expand that span by up to five tokens before and five tokens after.
- Binary negation signatures are compared between:
  - the normalized quote; and
  - the destination span returned by partial_ratio_alignment.
- Do not compute destination signature from the expanded context.
- Current-slot patterns and bounded ambiguity checks may use the expanded context as specified.
- If the full anchored turn contains both surviving positive and negative patterns for the current slot, fuzzy matching fails closed.
- If the guard passes, preserve the existing threshold rule:
  score >= threshold.
- No alternative alignment search or fallback scorer is introduced.

### Regression invariant

- Unrelated negation in a neighboring clause must not alter the signature of the matched destination span.
- Subject to absence of a current-slot conflict, the following approved evidence remains eligible:
  - Breathing is okay
  - breathe normally
  - alert and thinking clearly
  - built up gradually
- Every currently grounded non-UNKNOWN slot in the nine approved fixtures must remain grounded.
- All nine fixture verdicts must remain unchanged.
- In particular, pass_all_critical_no_001 must remain runtime PASS.

### Failure behavior

- Explicit conflict, ambiguity, or negation-signature mismatch produces:
  - EvidenceSlotStatus.NOT_FOUND;
  - score=None.
- Use existing RC_EVIDENCE_NOT_FOUND.
- Do not add a new evidence status.
- Do not add a new verifier reason code.
- A rejected match does not establish hallucination.

### Precedence

- Contract validation remains first.
- Dialogue validation remains second.
- Structural ESCALATE remains unchanged when polarity grounding fails.
- Non-escalation runtime failures retain existing ASK_ONCE behavior and reason-code ordering.
- Audit-only polarity failures remain report-only.
- Trusted Silence-oracle BLOCK retains its existing evaluation precedence.
- Polarity conflict alone never emits RC_HALLUCINATED_CRITICAL_FILL.

### Explicit exclusions

- General negation parsing.
- Semantic entailment.
- Extractor correction.
- Clause or dependency parsing.
- Coreference.
- Historical or hypothetical interpretation.
- Unlisted synonym expansion.
- Multilingual cues.
- Models, embeddings, classifiers, or external NLP dependencies.
- Schema, fixture, taxonomy, or verdict changes.

## D-020 — Canonical reviewer demo and CI interface

**Decision:**

- The canonical reviewer demo entrypoint is `python -m eval.demo [fixture_id]`.
- The optional `fixture_id` is resolved only against `eval/data/ad_verdict_fixtures_v0.1.json`.
- Omitting `fixture_id` selects `golden_001`.
- The demo calls the existing public `verify_case(payload, dialogue)`.
- The demo prints exactly `result.verdict.to_json()` followed by one newline.
- Successful execution emits no additional stdout text.
- PASS, BLOCK, and ABSTAIN all use process exit code 0; the clinical/verifier decision is represented only in JSON.
- An unknown fixture ID, invalid argument count, unreadable fixture source, or malformed fixture-set structure fails with non-zero exit status, emits no result JSON to stdout, and reports a concise error to stderr.
- Error-message wording is not a stable public contract.
- Output contains no timestamps, environment metadata, randomness, network-derived values, or mutable runtime state.
- The demo does not serialize EvidenceVerificationResult and does not create a new verifier result schema.
- The demo adds no clinical logic, verdict semantics, reason codes, schema behavior, extraction, or evidence policy.
- The canonical development installation command is `python -m pip install -r requirements-dev.txt`.
- The canonical test command is `python -m pytest -q`.
- Minimal CI runs the canonical development installation and test commands on Python 3.11 for push and pull_request.
- README may describe existing executable capabilities only as supported by the repository at the current canonical state.
- Research-only and non-deployment boundaries remain unchanged.

**Revisit trigger:**

- If the CLI arguments, fixture source, stdout schema, exit-code policy, Python support policy, or canonical CI command changes.
