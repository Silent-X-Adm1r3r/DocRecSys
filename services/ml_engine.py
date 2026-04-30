"""
ML Engine — Disease Prediction using trained scikit-learn ensemble.
Loads pre-trained model artifacts and provides prediction API.
Falls back to rule-based matching if model files are missing.
"""
from __future__ import annotations
import os, json, logging
import numpy as np

logger = logging.getLogger(__name__)

class MLEngine:
    """Handles model loading and disease prediction."""

    def __init__(self, model_dir: str):
        self.model_dir = model_dir
        self.model = None
        self.vectorizer_columns = None
        self.label_encoder = None
        self.metadata = None
        self._loaded = False
        self._load_model()

    def _load_model(self):
        """Load trained model artifacts from disk."""
        try:
            import joblib
            model_path = os.path.join(self.model_dir, "disease_predictor.pkl")
            columns_path = os.path.join(self.model_dir, "symptom_columns.pkl")
            encoder_path = os.path.join(self.model_dir, "label_encoder.pkl")
            meta_path = os.path.join(self.model_dir, "model_metadata.json")

            if not all(os.path.exists(p) for p in [model_path, columns_path, encoder_path]):
                logger.warning("Model files not found in %s — using fallback.", self.model_dir)
                return

            self.model = joblib.load(model_path)
            self.vectorizer_columns = joblib.load(columns_path)
            self.label_encoder = joblib.load(encoder_path)

            if os.path.exists(meta_path):
                with open(meta_path, "r") as f:
                    self.metadata = json.load(f)

            self._loaded = True
            accuracy = self.metadata.get("accuracy", "N/A") if self.metadata else "N/A"
            logger.info("ML model loaded successfully. Accuracy: %s", accuracy)
        except Exception as e:
            logger.error("Failed to load ML model: %s", e)
            self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def predict(self, symptoms: list[str], top_n: int = 3) -> list[dict]:
        """
        Predict diseases from a list of canonical symptom names.
        Returns list of {disease, confidence, matching_symptoms}.
        """
        if not self._loaded or not symptoms:
            return []

        try:
            # Build feature vector from symptom list
            feature_vector = np.zeros(len(self.vectorizer_columns))
            matched = []
            for i, col in enumerate(self.vectorizer_columns):
                if col in symptoms:
                    feature_vector[i] = 1
                    matched.append(col)

            if not matched:
                return []

            import pandas as pd
            X = pd.DataFrame([feature_vector], columns=self.vectorizer_columns)

            # Get probability predictions
            probas = self.model.predict_proba(X)[0]
            classes = self.label_encoder.classes_

            # Get top-N predictions
            top_indices = np.argsort(probas)[::-1][:top_n]

            results = []
            for idx in top_indices:
                conf = float(probas[idx])
                if conf < 0.02:  # Skip negligible probabilities
                    continue
                results.append({
                    "disease": classes[idx],
                    "confidence": round(conf, 3),
                    "matching_symptoms": matched,
                })

            return results
        except Exception as e:
            logger.error("Prediction failed: %s", e)
            return []

    def get_model_info(self) -> dict:
        """Return metadata about the loaded model."""
        if not self.metadata:
            return {"status": "no model loaded"}
        return {
            "status": "loaded",
            "accuracy": self.metadata.get("accuracy"),
            "diseases_count": self.metadata.get("num_diseases"),
            "symptoms_count": self.metadata.get("num_symptoms"),
            "trained_at": self.metadata.get("trained_at"),
        }
