# AD Example — Silence 001

## Dialogue
- Turn 0: "Chest hurts."
- Turn 1: "Not sure. Hard to explain."
- Turn 2: (no additional info)

## Expected Extractor JSON (v0.1)
```json
{
  "meta": {
    "dialogue_id": "silence_001",
    "last_turn_id": 2,
    "schema_version": "v0.1.0",
    "guideline_ref": "AHA_2014_ChestPain_v1",
    "taxonomy_version": "v0.1"
  },
  "instability": {
    "syncope_or_collapse": { "value": "UNKNOWN", "evidence": null },
    "severe_respiratory_distress": { "value": "UNKNOWN", "evidence": null },
    "cyanosis_or_low_o2": { "value": "UNKNOWN", "evidence": null },
    "hypotension_or_shock_signs": { "value": "UNKNOWN", "evidence": null },
    "altered_mental_status": { "value": "UNKNOWN", "evidence": null },
    "acute_focal_neuro_deficit": { "value": "UNKNOWN", "evidence": null },
    "severe_pain_at_rest_with_diaphoresis_or_pallor": { "value": "UNKNOWN", "evidence": null }
  },
  "ad_gate": {
    "C1_onset_maximal_at_start": { "value": "UNKNOWN", "evidence": null },
    "C2_back_interscapular_radiation": { "value": "UNKNOWN", "evidence": null },
    "C4_aortic_high_risk_history_any": { "value": "UNKNOWN", "evidence": null }
  },
  "audit": {
    "A1_focal_neuro_deficit": { "value": "UNKNOWN", "evidence": null }
  }
}
