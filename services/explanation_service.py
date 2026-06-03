"""
Explanation Service — Generates human-readable explanations for predictions.
No internal calculations exposed. Patient-friendly language.
"""
from __future__ import annotations
from services.symptom_extractor import get_display_name


def generate_explanation(disease, matching_symptoms, confidence, all_symptoms):
    display_symptoms = [get_display_name(s) for s in matching_symptoms[:5]]
    if not display_symptoms:
        display_symptoms = [get_display_name(s) for s in all_symptoms[:5]]
    if len(display_symptoms) == 1:
        stxt = f"**{display_symptoms[0]}**"
    elif len(display_symptoms) == 2:
        stxt = f"**{display_symptoms[0]}** and **{display_symptoms[1]}**"
    else:
        last = display_symptoms[-1]
        rest = ", ".join(f"**{s}**" for s in display_symptoms[:-1])
        stxt = f"{rest}, and **{last}**"
    if confidence > 0.70:
        return f"We identified **{disease}** as a likely condition because {stxt} are commonly associated with {disease} patterns in our medical database."
    elif confidence >= 0.40:
        return f"**{disease}** is a possible match because {stxt} are sometimes seen in {disease} cases. Further evaluation is recommended."
    else:
        return f"**{disease}** has a weak association with your symptoms ({stxt}). This prediction has low confidence — please consult a healthcare professional."


def generate_summary_explanation(predictions, all_symptoms):
    display_symptoms = [get_display_name(s) for s in all_symptoms[:6]]
    stxt = ", ".join(f"**{s}**" for s in display_symptoms)
    if not predictions:
        return f"Analysis based on: {stxt}. No strong matches found."
    top = predictions[0]
    if top["confidence"] > 0.70:
        return f"Based on your symptoms ({stxt}), our analysis suggests **{top['disease']}** as the most likely condition."
    return f"Based on your symptoms ({stxt}), we've identified several possible conditions. Please review the results below."
