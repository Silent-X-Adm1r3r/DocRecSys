"""
Train the disease prediction ML model.
Usage: python train_model.py
"""
import os, json, datetime
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score
from sklearn.calibration import CalibratedClassifierCV
import joblib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_DIR = os.path.join(BASE_DIR, "models")

def train():
    csv_path = os.path.join(DATA_DIR, "symptom_disease_data.csv")
    if not os.path.exists(csv_path):
        print("ERROR: Dataset not found. Run generate_dataset.py first.")
        return

    print("Loading dataset...")
    df = pd.read_csv(csv_path)
    print(f"  {df.shape[0]} samples, {df.shape[1]-1} features, {df['prognosis'].nunique()} diseases")

    # Features and labels
    X = df.drop("prognosis", axis=1)
    symptom_columns = list(X.columns)
    y_raw = df["prognosis"]

    le = LabelEncoder()
    y = le.fit_transform(y_raw)

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    print("\nTraining ensemble model...")
    # Build ensemble: RF + LR + GBT
    rf = RandomForestClassifier(n_estimators=200, max_depth=20, random_state=42, n_jobs=-1)
    lr = LogisticRegression(max_iter=1000, random_state=42, C=1.0)
    gb = GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42, learning_rate=0.1)

    ensemble = VotingClassifier(
        estimators=[("rf", rf), ("lr", lr), ("gb", gb)],
        voting="soft",
        weights=[2, 1, 2],
    )

    # Calibrate for better probability estimates
    calibrated = CalibratedClassifierCV(ensemble, cv=3, method="sigmoid")
    calibrated.fit(X_train, y_train)

    # Evaluate
    y_pred = calibrated.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nTest Accuracy: {acc:.4f}")
    print("\nClassification Report (top-level):")
    print(classification_report(y_test, y_pred, target_names=le.classes_, zero_division=0, output_dict=False))

    # Cross-validation on full data
    cv_scores = cross_val_score(ensemble, X, y, cv=5, scoring="accuracy")
    print(f"5-Fold CV Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

    # Retrain on full data for production
    print("\nRetraining on full dataset for production...")
    final_model = CalibratedClassifierCV(
        VotingClassifier(
            estimators=[("rf", rf), ("lr", lr), ("gb", gb)],
            voting="soft", weights=[2, 1, 2],
        ),
        cv=3, method="sigmoid"
    )
    final_model.fit(X, y)

    # Save artifacts
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(final_model, os.path.join(MODEL_DIR, "disease_predictor.pkl"))
    joblib.dump(symptom_columns, os.path.join(MODEL_DIR, "symptom_columns.pkl"))
    joblib.dump(le, os.path.join(MODEL_DIR, "label_encoder.pkl"))

    metadata = {
        "accuracy": round(float(acc), 4),
        "cv_accuracy": round(float(cv_scores.mean()), 4),
        "num_diseases": int(len(le.classes_)),
        "num_symptoms": len(symptom_columns),
        "num_samples": int(len(df)),
        "diseases": list(le.classes_),
        "trained_at": datetime.datetime.now().isoformat(),
    }
    with open(os.path.join(MODEL_DIR, "model_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nModel saved to {MODEL_DIR}/")
    print(f"  Diseases: {metadata['num_diseases']}")
    print(f"  Symptoms: {metadata['num_symptoms']}")
    print(f"  Accuracy: {metadata['accuracy']}")
    print("Done!")

if __name__ == "__main__":
    train()
