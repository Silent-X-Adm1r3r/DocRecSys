"""
Response Formatter — Builds structured JSON for all response types.
Enhanced with embedded map data, distance info, specialist badges.
"""
from __future__ import annotations
from services.confidence_service import score_confidence, get_overall_confidence

DISCLAIMER = (
    "\u2695\ufe0f **Medical Disclaimer:** This system provides informational guidance only "
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
    explanation: str = "",
    red_flags: list[dict] | None = None,
    confidence_info: dict | None = None,
    precautions: list[str] | None = None,
    location_error: str | None = None,
) -> dict:
    # Emergency override
    if emergency and emergency_data:
        result = {
            "type": "emergency",
            "level": emergency_data.get("level", "HIGH"),
            "score": emergency_data.get("score", 0),
            "message": emergency_data.get("message", ""),
            "numbers": emergency_data.get("numbers", {}),
            "disclaimer": DISCLAIMER,
        }
        if doctor_info and doctor_info.get("hospitals"):
            result["hospitals"] = doctor_info["hospitals"]
        if doctor_info and doctor_info.get("user_location"):
            result["user_location"] = doctor_info["user_location"]
        return result

    # Follow-up needed
    if followup:
        return {
            "type": "followup",
            "message": followup["question"],
            "followup_type": followup["type"],
        }

    # No predictions
    if not predictions:
        return {
            "type": "no_match",
            "message": (
                "I wasn't able to identify a specific condition from those symptoms. "
                "Could you provide more details or describe additional symptoms?"
            ),
            "disclaimer": DISCLAIMER,
        }

    # Normal result (Top 5)
    conditions = []
    for i, pred in enumerate(predictions):
        interp = interpretations[i] if i < len(interpretations) else ""
        conf_info = score_confidence(pred["confidence"])
        conditions.append({
            "disease": pred["disease"],
            "confidence": pred["confidence"],
            "confidence_pct": pred.get("confidence_pct", f"{round(pred['confidence'] * 100)}%"),
            "interpretation": interp,
            "confidence_level": conf_info["level"],
            "influencing_symptoms": pred.get("explanation_symptoms", pred.get("matching_symptoms", [])),
            "description": pred.get("description", ""),
            "precautions": pred.get("precautions", []),
        })

    from services.symptom_extractor import get_display_name
    symptom_names = [get_display_name(s) for s in symptoms]

    overall_confidence = confidence_info or get_overall_confidence(predictions)

    result = {
        "type": "result",
        "conditions": conditions,
        "confidenceLevel": overall_confidence.get("level", "moderate"),
        "confidenceMessage": overall_confidence.get("message", ""),
        "explanation": explanation or ("Prediction based on: " + ", ".join(f"**{s}**" for s in symptom_names) + "."),
        "triage": triage,
        "disclaimer": DISCLAIMER,
    }

    if doctor_info:
        dr_data = {
            "specialist": doctor_info.get("specialist", ""),
            "specialist_rarity": doctor_info.get("specialist_rarity", "general"),
            "doctors": doctor_info.get("doctors", []),
        }
        result["doctor_recommendation"] = dr_data

        if doctor_info.get("hospitals"):
            result["hospitals"] = doctor_info["hospitals"]

        # Embedded map data for frontend rendering
        if doctor_info.get("user_location"):
            result["user_location"] = doctor_info["user_location"]

        # Include location error if present
        if doctor_info.get("success") is False:
            result["location_error"] = doctor_info.get("error", "")

    if location_error:
        result["location_error"] = location_error

    if red_flags:
        result["redFlags"] = red_flags

    if precautions:
        result["precautions"] = precautions

    return result
