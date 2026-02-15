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
