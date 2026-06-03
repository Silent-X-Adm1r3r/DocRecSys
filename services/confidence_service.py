"""
Confidence Service — Confidence scoring and interpretation.
"""
from __future__ import annotations


def score_confidence(confidence: float) -> dict:
    """
    Categorize confidence into levels with interpretation.
    High: >70%  Moderate: 40-70%  Low: <40%
    """
    if confidence > 0.70:
        return {
            "level": "high",
            "label": "High Confidence",
            "interpretation": "Likely condition",
            "color": "success",
        }
    elif confidence >= 0.40:
        return {
            "level": "moderate",
            "label": "Moderate Confidence",
            "interpretation": "Possible condition",
            "color": "warning",
        }
    else:
        return {
            "level": "low",
            "label": "Low Confidence",
            "interpretation": "Uncertain — please consult a doctor",
            "color": "danger",
        }


def get_overall_confidence(predictions: list[dict]) -> dict:
    """
    Get the overall confidence assessment for a set of predictions.
    """
    if not predictions:
        return {
            "level": "low",
            "label": "Insufficient Data",
            "message": "Unable to determine conditions with available information.",
        }

    top_confidence = predictions[0]["confidence"]
    info = score_confidence(top_confidence)

    if info["level"] == "low":
        info["message"] = (
            "⚠️ **Insufficient confidence.** The symptoms provided do not strongly match "
            "any specific condition in our database. Please consult a healthcare professional "
            "for proper evaluation."
        )
    elif info["level"] == "moderate":
        info["message"] = (
            "🔍 **Moderate confidence.** The predicted conditions are possible matches based on "
            "your symptoms. We recommend consulting a doctor for confirmation."
        )
    else:
        info["message"] = (
            "✅ **High confidence.** The predicted conditions strongly match your symptom pattern. "
            "However, please consult a healthcare professional for definitive diagnosis."
        )

    return info


def interpret_confidence(confidence: float) -> str:
    """Simple confidence interpretation string."""
    info = score_confidence(confidence)
    return info["interpretation"]
