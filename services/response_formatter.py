"""
Response Formatter — Builds structured JSON for all response types.
"""
from __future__ import annotations

DISCLAIMER = (
    "⚕️ **Medical Disclaimer:** This system provides informational guidance only "
    "and is NOT a substitute for professional medical diagnosis, treatment, or "
    "emergency care. Always consult a qualified healthcare professional."
)

def format_response(
    symptoms: list[str],
    predictions: list[dict],
    interpretations: list[str],
    triage: str,
    doctor_info: dict | None,
    emergency: bool = False,
    emergency_data: dict | None = None,
    followup: dict | None = None,
) -> dict:
    # ── Emergency override
    if emergency and emergency_data:
        return {
            "type": "emergency",
            "level": emergency_data.get("level", "HIGH"),
            "score": emergency_data.get("score", 0),
            "message": emergency_data.get("message", ""),
            "numbers": emergency_data.get("numbers", {}),
            "disclaimer": DISCLAIMER,
        }

    # ── Follow-up needed
    if followup:
        return {
            "type": "followup",
            "message": followup["question"],
            "followup_type": followup["type"],
        }

    # ── No predictions
    if not predictions:
        return {
            "type": "no_match",
            "message": (
                "I wasn't able to identify a specific condition from those symptoms. "
                "Could you provide more details or describe additional symptoms?"
            ),
            "disclaimer": DISCLAIMER,
        }

    # ── Normal result
    conditions = []
    for pred, interp in zip(predictions, interpretations):
        conditions.append({
            "disease": pred["disease"],
            "confidence": pred["confidence"],
            "confidence_pct": pred.get("confidence_pct", f"{round(pred['confidence']*100)}%"),
            "interpretation": interp,
            "influencing_symptoms": pred.get("explanation_symptoms", []),
        })

    from services.symptom_extractor import get_display_name
    symptom_names = [get_display_name(s) for s in symptoms]
    explanation = "Prediction based on: " + ", ".join(f"**{s}**" for s in symptom_names) + "."

    result: dict = {
        "type": "result",
        "conditions": conditions,
        "explanation": explanation,
        "triage": triage,
        "disclaimer": DISCLAIMER,
    }
    if doctor_info:
        result["doctor_recommendation"] = doctor_info

    return result
