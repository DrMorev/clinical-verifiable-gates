# AD Example — Golden 001

## Dialogue
- Turn 0: "Chest pain started suddenly and instantly became the worst pain. It also goes to my upper back between the shoulder blades."
- Turn 1: "No fainting. Breathing is okay."

## Expected Extractor JSON (v0.1)
```json
{
  "meta": {
    "dialogue_id": "golden_001",
    "last_turn_id": 1,
    "schema_version": "v0.1.0",
    "guideline_ref": "AHA_2014_ChestPain_v1",
    "taxonomy_version": "v0.1"
  },
  "instability": {
    "syncope_or_collapse": { "value": "ABSENT", "evidence": { "source_turn_id": 1, "quote_text": "No fainting.", "confidence": "high" } },
    "severe_respiratory_distress": { "value": "ABSENT", "evidence": { "source_turn_id": 1, "quote_text": "Breathing is okay.", "confidence": "high" } },
    "cyanosis_or_low_o2": { "value": "UNKNOWN", "evidence": null },
    "hypotension_or_shock_signs": { "value": "UNKNOWN", "evidence": null },
    "altered_mental_status": { "value": "UNKNOWN", "evidence": null },
    "acute_focal_neuro_deficit": { "value": "UNKNOWN", "evidence": null },
    "severe_pain_at_rest_with_diaphoresis_or_pallor": { "value": "UNKNOWN", "evidence": null }
  },
  "ad_gate": {
    "C1_onset_maximal_at_start": { "value": "YES", "evidence": { "source_turn_id": 0, "quote_text": "started suddenly and instantly became the worst pain", "confidence": "high" } },
    "C2_back_interscapular_radiation": { "value": "YES", "evidence": { "source_turn_id": 0, "quote_text": "goes to my upper back between the shoulder blades", "confidence": "high" } },
    "C4_aortic_high_risk_history_any": { "value": "UNKNOWN", "evidence": null }
  },
  "audit": {
    "A1_focal_neuro_deficit": { "value": "UNKNOWN", "evidence": null }
  }
}
