"""
Structured Logger — JSON-formatted observability for DocRecSys.
Provides structured log entries for debugging, monitoring, and analytics.
"""
from __future__ import annotations
import json, logging, sys
from datetime import datetime, timezone


class StructuredFormatter(logging.Formatter):
    """JSON log formatter for structured observability."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Attach extra structured fields if present
        for key in ("event", "session_id", "symptoms", "disease", "confidence",
                     "specialist", "latitude", "longitude", "search_radius",
                     "maps_query", "fallback_query", "result_count",
                     "redis_hit", "redis_miss", "prediction_cache_hit",
                     "maps_cache_hit", "duration_ms"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val

        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logging(level: str = "INFO"):
    """Configure structured JSON logging for the entire application."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    # JSON handler for stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    root.addHandler(handler)


def log_symptom_check(logger: logging.Logger, **kwargs):
    """Log a symptom check event with structured fields."""
    logger.info(
        "Symptom check processed",
        extra={"event": "symptom_check", **kwargs},
    )


def log_prediction(logger: logging.Logger, **kwargs):
    """Log a disease prediction event."""
    logger.info(
        "Disease prediction completed",
        extra={"event": "prediction", **kwargs},
    )


def log_doctor_search(logger: logging.Logger, **kwargs):
    """Log a doctor search event."""
    logger.info(
        "Doctor search completed",
        extra={"event": "doctor_search", **kwargs},
    )


def log_cache_event(logger: logging.Logger, cache_type: str, hit: bool, **kwargs):
    """Log a cache hit/miss event."""
    status = "HIT" if hit else "MISS"
    logger.info(
        f"Cache {status}: {cache_type}",
        extra={
            "event": f"cache_{status.lower()}",
            f"{cache_type}_cache_hit" if hit else f"{cache_type}_miss": True,
            **kwargs,
        },
    )
