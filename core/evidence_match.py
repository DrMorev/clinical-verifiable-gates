"""
Evidence matching policy (v0.1) — placeholder.

Policy (deterministic, conservative):
1) normalize: casefold + whitespace collapse + strip punctuation
2) exact substring match
3) strict fuzzy match (rapidfuzz)

Thresholds (v0.1):
- Critical gating slots: 90
- Non-critical / audit slots: 85

Outcomes:
- EVIDENCE_STRONG
- EVIDENCE_WEAK (log; not hallucination by default)
- RC_EVIDENCE_NOT_FOUND -> ABSTAIN_ASK_ONCE
- RC_HALLUCINATED_CRITICAL_FILL -> BLOCK (hard fail in eval)

Note:
Negation sensitivity (“no pain” vs “now pain”) is a known risk; backlog item for future tuning.
"""
