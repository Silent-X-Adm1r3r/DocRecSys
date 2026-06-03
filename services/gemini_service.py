"""
Gemini Service — AI-powered symptom extraction using Google Gemini.
CRITICAL: Gemini is used ONLY for NLP extraction, NEVER for diagnosis.
Falls back to local symptom_extractor if API unavailable.
"""
from __future__ import annotations
import json, logging, time

logger = logging.getLogger(__name__)

_model = None
_cache: dict[str, tuple[dict, float]] = {}  # key -> (result, timestamp)
_CACHE_TTL = 3600  # 1 hour
_CACHE_MAX = 200
_available = False


def init_gemini(api_key: str, model_name: str = "gemini-2.0-flash"):
    """Initialize Gemini client. Call once at app startup."""
    global _model, _available
    if not api_key:
        logger.warning("GEMINI_API_KEY not set. Using local extraction only.")
        return
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        _model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "temperature": 0.1,
                "top_p": 0.8,
                "max_output_tokens": 1024,
            },
            system_instruction=_SYSTEM_PROMPT,
        )
        _available = True
        logger.info("Gemini AI initialized: %s", model_name)
    except Exception as e:
        logger.error("Gemini init failed: %s", e)
        _available = False


def is_available() -> bool:
    return _available


_SYSTEM_PROMPT = """You are a medical symptom extraction assistant. Your ONLY job is to extract structured medical information from user text.

STRICT RULES:
1. You must NEVER diagnose diseases.
2. You must NEVER suggest treatments.
3. You must NEVER provide medical advice.
4. Extract ONLY what the user explicitly states.
5. Output ONLY valid JSON matching the schema below.

OUTPUT SCHEMA:
{
  "symptoms": ["list of extracted symptom terms in medical terminology"],
  "duration": "extracted duration or empty string",
  "severity": "mild|moderate|severe or empty string",
  "age": "extracted age or empty string",
  "gender": "extracted gender or empty string",
  "riskFactors": ["smoking", "diabetes", "hypertension", etc.],
  "emergencyIndicators": ["any emergency signs detected"]
}

SYMPTOM NORMALIZATION RULES:
- "tummy pain" → "abdominal pain"
- "feeling hot" → "fever"
- "throwing up" → "vomiting"
- "head spinning" → "dizziness"
- "can't breathe" → "breathlessness"
- "heart racing" → "fast heart rate"
- "running nose" → "runny nose"
- Use standard medical terms always.

Return ONLY the JSON object. No explanation, no markdown, no extra text."""


def extract_symptoms_gemini(user_text: str, context: dict | None = None) -> dict:
    """
    Extract structured medical information from user text using Gemini.
    Returns structured dict or empty dict on failure.
    """
    if not _available or not _model:
        return {}

    # Check cache
    cache_key = user_text.strip().lower()[:200]
    cached = _cache.get(cache_key)
    if cached and (time.time() - cached[1]) < _CACHE_TTL:
        logger.debug("Gemini cache hit")
        return cached[0]

    try:
        # Build prompt with context
        prompt = f"Extract medical information from this patient statement:\n\n\"{user_text}\""
        if context:
            existing = context.get("symptoms", [])
            if existing:
                prompt += f"\n\nPreviously identified symptoms: {', '.join(existing)}"

        response = _model.generate_content(prompt)
        text = response.text.strip()

        # Clean JSON from markdown code blocks
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            if text.startswith("json"):
                text = text[4:].strip()

        result = json.loads(text)

        # Validate structure
        validated = {
            "symptoms": result.get("symptoms", []),
            "duration": result.get("duration", ""),
            "severity": result.get("severity", ""),
            "age": result.get("age", ""),
            "gender": result.get("gender", ""),
            "riskFactors": result.get("riskFactors", []),
            "emergencyIndicators": result.get("emergencyIndicators", []),
        }

        # Evict oldest entries if cache is full
        if len(_cache) >= _CACHE_MAX:
            oldest_key = min(_cache, key=lambda k: _cache[k][1])
            del _cache[oldest_key]
        _cache[cache_key] = (validated, time.time())
        logger.info("Gemini extracted: %d symptoms, severity=%s", len(validated["symptoms"]), validated["severity"])
        return validated

    except json.JSONDecodeError as e:
        logger.warning("Gemini JSON parse error: %s", e)
        return {}
    except Exception as e:
        logger.error("Gemini extraction failed: %s", e)
        return {}


def get_status() -> dict:
    """Return Gemini service status."""
    return {
        "available": _available,
        "cache_size": len(_cache),
        "cache_max": _CACHE_MAX,
    }
