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
