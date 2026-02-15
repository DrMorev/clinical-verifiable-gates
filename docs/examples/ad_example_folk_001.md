# AD Example — Folk 001 (slang/negations)

## Dialogue
- Turn 0: "It hit me out of nowhere, like BAM, max pain right away."
- Turn 1: "Nah, nothing in my back. Just chest."
- Turn 2: "No passing out."

## Expected Extractor JSON (v0.1)
```json
{
  "meta": {
    "dialogue_id": "folk_001",
    "last_turn_id": 2,
    "schema_version": "v0.1.0",
    "guideline_ref": "AHA_2014_ChestPain_v1",
    "taxonomy_version": "v0.1"
  },
  "instability": {
    "syncope_or_collapse": { "value": "ABSENT", "evidence": { "source_turn_id": 2, "quote_text": "No passing out.", "confidence": "high" } },
    "severe_respiratory_distress": { "value": "UNKNOWN", "evidence": null },
    "cyanosis_or_low_o2": { "value": "UNKNOWN", "evidence": null },
    "hypotension_or_shock_signs": { "value": "UNKNOWN", "evidence": null },
    "altered_mental_status": { "value": "UNKNOWN", "evidence": null },
    "acute_focal_neuro_deficit": { "value": "UNKNOWN", "evidence": null },
    "severe_pain_at_rest_with_diaphoresis_or_pallor": { "value": "UNKNOWN", "evidence": null }
  },
  "ad_gate": {
    "C1_onset_maximal_at_start": { "value": "YES", "evidence": { "source_turn_id": 0, "quote_text": "out of nowhere, like BAM, max pain right away", "confidence": "medium" } },
    "C2_back_interscapular_radiation": { "value": "NO", "evidence": { "source_turn_id": 1, "quote_text": "Nah, nothing in my back.", "confidence": "high" } },
    "C4_aortic_high_risk_history_any": { "value": "UNKNOWN", "evidence": null }
  },
  "audit": {
    "A1_focal_neuro_deficit": { "value": "UNKNOWN", "evidence": null }
  }
}
