"""
Response Formatter Service
Builds the structured JSON response returned by the /webhook endpoint.
"""

from __future__ import annotations


DISCLAIMER = (
    "⚕️ **Disclaimer:** This is a preliminary AI-based assessment and "
    "does NOT replace professional medical advice. Please consult a "
    "qualified healthcare professional for diagnosis and treatment."
)


def format_response(
    symptoms: list[str],
    predictions: list[dict],
    interpretations: list[str],
    triage: str,
    doctor_info: dict | None,
    emergency: bool = False,
    emergency_msg: str = "",
    followup: dict | None = None,
) -> dict:
    """
    Build the final structured response dict.

    Parameters
    ----------
    symptoms : matched symptom list
    predictions : [{ "disease": str, "confidence": float }, ...]
    interpretations : ["Likely condition", ...] parallel to predictions
    triage : triage suggestion string
    doctor_info : { "specialist": str, "doctors": [...] } or None
    emergency : whether emergency was triggered
    emergency_msg : the emergency alert text
    followup : optional follow-up question dict
    """

    # ── Emergency override ──────────────────────────────────────────
    if emergency:
        return {
            "type": "emergency",
            "message": emergency_msg,
            "disclaimer": DISCLAIMER,
        }

    # ── Follow-up needed ────────────────────────────────────────────
    if followup:
        return {
            "type": "followup",
            "message": followup["question"],
            "followup_type": followup["type"],
        }

    # ── No predictions ──────────────────────────────────────────────
    if not predictions:
        return {
            "type": "no_match",
            "message": (
                "I wasn't able to narrow down a condition from those symptoms. "
                "Could you provide more details or list additional symptoms?"
            ),
            "disclaimer": DISCLAIMER,
        }

    # ── Normal structured response ──────────────────────────────────
    conditions = []
    for pred, interp in zip(predictions, interpretations):
        conditions.append({
            "disease": pred["disease"],
            "confidence": pred["confidence"],
            "confidence_pct": f"{round(pred['confidence'] * 100)}%",
            "interpretation": interp,
        })

    explanation = (
        "This prediction is based on the symptoms: "
        + ", ".join(f"**{s}**" for s in symptoms)
        + "."
    )

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
