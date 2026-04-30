# DocRecSys — AI-Powered Medical Symptom Checker & Doctor Recommendation

A production-grade Flask web application that uses machine learning to analyze symptoms, predict diseases, and recommend specialist doctors across India.

## Features

- **ML-Powered Disease Prediction** — Calibrated ensemble model (Random Forest + Logistic Regression + Gradient Boosting) trained on 50 diseases, 141 symptoms, achieving 98% accuracy
- **Natural Language Symptom Extraction** — 200+ synonym mappings, fuzzy matching for typos, negation detection ("I don't have fever")
- **Emergency Triage System** — 40+ emergency patterns, dangerous symptom combination detection, severity scoring, India emergency helplines (112, 108, NIMHANS)
- **Doctor Recommendation** — 923 doctors across 35 Indian cities (all state/UT capitals), 18 specialties, ranked by rating and experience
- **Premium UI** — Dark theme with 3D glassmorphism, animated confidence bars, typing indicators, responsive design
- **Security** — Rate limiting, input validation, sanitization, security headers, safe error handling
- **SQLite Database** — Persistent storage for doctors, sessions, feedback, and emergency alerts

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.8+, Flask, Gunicorn |
| ML | scikit-learn (Ensemble: RF + LR + GBT), CalibratedClassifierCV |
| Database | SQLite (default), PostgreSQL (via DATABASE_URL) |
| Frontend | Vanilla HTML5, CSS3, JavaScript |
| Deployment | Render / Railway ready (Procfile included) |

## Quick Start

```bash
# Clone and setup
git clone https://github.com/Silent-X-Adm1r3r/DocRecSys.git
cd DocRecSys
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Generate data and train model
python generate_dataset.py
python generate_doctors.py
python train_model.py

# Run the application
python app.py
```

Open http://127.0.0.1:5000 in your browser.

## Project Structure

```
DocRecSys/
├── app.py                      # Flask app with security & rate limiting
├── config.py                   # Centralized configuration
├── train_model.py              # ML model training script
├── generate_dataset.py         # Disease-symptom dataset generator
├── generate_doctors.py         # Indian doctor database generator
├── Procfile                    # Deployment config (Gunicorn)
├── requirements.txt            # Python dependencies
├── data/
│   ├── doctors_india.json      # 923 doctors, 35 cities, 18 specialties
│   ├── symptom_disease_data.csv # Training data (50 diseases, 141 symptoms)
│   ├── symptom_synonyms.json   # 200+ symptom synonym mappings
│   └── docrecsys.db            # SQLite database (auto-created)
├── models/
│   ├── disease_predictor.pkl   # Trained ensemble model
│   ├── symptom_columns.pkl     # Feature column names
│   ├── label_encoder.pkl       # Disease label encoder
│   └── model_metadata.json     # Training metrics
├── services/
│   ├── ml_engine.py            # ML prediction engine
│   ├── symptom_extractor.py    # NLP symptom extraction
│   ├── predictor.py            # Disease prediction service
│   ├── triage.py               # Emergency triage & severity scoring
│   ├── doctor_recommender.py   # Doctor recommendation service
│   ├── database.py             # SQLite database layer
│   └── response_formatter.py   # JSON response builder
├── static/
│   ├── css/style.css           # Premium dark theme with 3D effects
│   └── js/chat.js              # Chat client with city selector
├── templates/
│   └── index.html              # Landing page & chatbot UI
└── tests/
    └── test_api.py             # 18 automated tests
```

## ML Model Details

| Metric | Value |
|--------|-------|
| Algorithm | Voting Ensemble (RF + LR + GBT) |
| Calibration | CalibratedClassifierCV (sigmoid) |
| Test Accuracy | 98.0% |
| 5-Fold CV | 96.1% |
| Diseases | 50 |
| Symptoms | 141 |
| Training Samples | 2,000 |

## Doctor Coverage

- **35 cities** covering all Indian state and UT capitals
- **18 specialties** including Cardiologist, Neurologist, Dermatologist, Pulmonologist, Psychiatrist, Gastroenterologist, Pediatrician, Orthopedic Surgeon, ENT, Gynecologist, Oncologist, Nephrologist, Endocrinologist, Urologist, Ophthalmologist, Rheumatologist, Infectious Disease Specialist, and General Physician
- **923 total doctors** with real Indian hospital names (Apollo, AIIMS, Fortis, Manipal, Narayana, etc.)

## Deployment

The app is ready for deployment on Render or Railway:

```bash
# Production with Gunicorn
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --preload
```

## Testing

```bash
python -m pytest tests/ -v
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Landing page |
| `/webhook` | POST | Chat endpoint (symptom analysis) |
| `/feedback` | POST | Feedback collection |
| `/reset` | POST | Session reset |
| `/health` | GET | Health check + model status |

## License

Open source for educational and research purposes.
