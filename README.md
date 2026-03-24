# DocRecSys — AI-Powered Symptom Checker & Doctor Recommendation

DocRecSys is a Flask-based web application that acts as an AI health assistant. It allows users to describe their symptoms in plain language, predicts possible conditions (simulated BERT-based prediction), offers triage suggestions, and recommends specialists with mock doctor data.

## Features

- **Natural Language Parsing:** Automatically extracts symptoms, duration, and severity keywords using a custom NLP module.
- **Disease Prediction:** Rule-based simulated-BERT model that outputs the top 2 possible conditions based on confidence scores.
- **Triage & Emergency Alert:** Suggests actionable steps ("Monitor", "Consult Doctor", or "Emergency") and overrides normal flow if critical keywords (e.g., "chest pain") are detected.
- **Adaptive Follow-up:** Asks a clarifying question (duration or severity) if the initial input is vague or confidence is too low.
- **Doctor Recommendation:** Maps predicted conditions to medical specialties and provides a hardcoded list of relevant doctors with contact details.
- **Premium UI:** A modern, dark-themed, responsive glassmorphism chatbot interface with animations and interactive confidence bars.

## Tech Stack

- **Backend:** Python, Flask
- **Frontend:** Vanilla HTML5, CSS3, JavaScript

## Local Development Setup

To run this project locally, follow these steps:

### Prerequisites
- Python 3.8+ installed on your machine.
- `git` installed.

### 1. Clone the Repository
```bash
git clone https://github.com/Silent-X-Adm1r3r/DocRecSys.git
cd DocRecSys
```

### 2. Create a Virtual Environment
It is highly recommended to use a virtual environment to manage dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
# On Windows use: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Flask Server
```bash
python3 app.py
```
The application will start running on your local development server.

### 5. Access the Application
Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

## Project Structure

```
DocRecSys/
├── app.py                    # Main Flask application entry point
├── requirements.txt          # Python dependencies
├── .gitignore                # Git ignore constraints
├── services/                 # Backend functional modules
│   ├── __init__.py
│   ├── symptom_extractor.py  # NLP logic for formatting inputs
│   ├── predictor.py          # Simulated BERT prediction logic
│   ├── doctor_recommender.py # Disease-to-specialist mapping logic
│   ├── triage.py             # Emergency alerts and triage processing
│   └── response_formatter.py # JSON response structurer
├── static/
│   ├── css/
│   │   └── style.css         # Main stylesheet (Dark Theme / Glassmorphism)
│   └── js/
│       └── chat.js           # Client-side chat interaction logic
└── templates/
    └── index.html            # Main HTML landing page and chatbot UI
```

## Extending the Application
- **AI Model Swap:** You can easily swap out the mock implementation in `services/predictor.py` with a real `transformers` pipeline to hook into an actual HuggingFace BERT model.
- **Database Hookup:** Modify `services/doctor_recommender.py` and the `feedback` route in `app.py` to connect to a real database (e.g., PostgreSQL or MongoDB) instead of using hardcoded mock data.
