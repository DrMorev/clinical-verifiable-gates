# AD Verdict Fixture Matrix v0.1

Status: approved test vectors for deterministic verifier implementation.

| Fixture ID | Category | Relevant state | Expected decision | Abstain mode | Ordered reason codes | Deterministic rationale | Source basis | Approval status |
|---|---|---|---|---|---|---|---|---|
| `golden_001` | Golden | C1 and C2 are `YES`; C4 is `UNKNOWN` | `ABSTAIN` | `ESCALATE` | `RC_AD_RED_FLAG_PRESENT` | A critical `YES` triggers red-flag escalation before missing critical information is considered. | `docs/examples/ad_example_golden_001.md`; memo §6.3 and §8 | APPROVED — PI/PM |
| `folk_001` | Folk | C1 is `YES`; C2 is `NO`; C4 is `UNKNOWN` | `ABSTAIN` | `ESCALATE` | `RC_AD_RED_FLAG_PRESENT` | Colloquial wording does not change the structured C1 red-flag result. | `docs/examples/ad_example_folk_001.md`; memo §6.3 and §8 | APPROVED — PI/PM |
| `silence_001` | Silence | C1, C2, and C4 remain `UNKNOWN` | `ABSTAIN` | `ASK_ONCE` | `RC_AD_CRITICAL_SLOT_MISSING` | Missing critical information remains unknown and must not be treated as negative. | `docs/examples/ad_example_silence_001.md`; memo §6.3 and §8 | APPROVED — PI/PM |
| `pass_all_critical_no_001` | PASS invariants | All instability triggers are `ABSENT`; C1, C2, and C4 are grounded `NO` values | `PASS` | `null` | `[]` | All current PASS invariants are satisfied; the verdict is not clinical clearance or a safety claim. | Memo §6.3 and PASS rule; current JSON Schema | APPROVED — PI/PM |
| `instability_present_001` | Instability bypass | Exactly one instability trigger is `PRESENT`; remaining instability and critical slots are non-triggering | `ABSTAIN` | `ESCALATE` | `RC_INSTABILITY_BYPASS` | Instability bypass precedes ordinary gating logic. | Current JSON Schema instability definition; memo §6.1 and §8 | APPROVED — PI/PM |
| `contract_missing_fields_001` | Contract error | Required top-level `audit` field is omitted | `BLOCK` | `null` | `RC_CONTRACT_MISSING_FIELDS` | Required contract content is absent. | Current JSON Schema top-level required fields; memo §8 | APPROVED — PI/PM |
| `contract_invalid_enum_001` | Contract error | C1 uses invalid enum value `MAYBE`; remaining structure minimizes unrelated defects | `BLOCK` | `null` | `RC_CONTRACT_SCHEMA_INVALID` | The structured output violates the current JSON Schema. | Current JSON Schema `GatingSlot` enum; memo §8 | APPROVED — PI/PM |
| `hallucinated_critical_fill_001` | Silence Gate | C1 is filled with `YES`, but its quoted evidence is absent from the referenced turn and dialogue | `BLOCK` | `null` | `RC_HALLUCINATED_CRITICAL_FILL` | This synthetic Silence-set oracle contains no support for C1, yet the extractor assigns a non-`UNKNOWN` critical value; D-009 defines that known Silence violation as a hard failure without treating every exact-quote miss as proof of hallucination. | Decision log D-009; memo §7.3 and §8 | APPROVED — PI/PM |

## Boundaries

- These fixtures are approved test vectors, not evidence of implemented functionality.
- No production verifier exists yet.
- PASS means only that no rule violation was detected under the applicable verifier specification. It does not mean clinical safety, clinical correctness, diagnostic clearance, or deployment readiness.
- `pass_all_critical_no_001` is a synthetic verifier-control case, not a claim of realistic extractor or clinical-dialogue performance.
- Evidence not found outside an oracle-labelled Silence violation is not automatically classified as hallucination by this fixture set.
- The `schema_version: v0.1.0` values mirror the existing Markdown examples and do not resolve the deferred `v0.1` versus `v0.1.0` notation question.
- This fixture set does not resolve contradiction representation.
- This fixture set does not modify the JSON Schema, clinical policy, or existing examples.
- The contract-error fixtures are intentionally non-conforming in the single defect identified by each case; no JSON Schema validator is added in this phase.
