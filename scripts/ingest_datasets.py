"""
Dataset Ingestion — Populates MongoDB with disease data from JSON files.
Run: python -m scripts.ingest_datasets
"""
import json, os, sys, logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)


def run():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE, ".env"))
    from config import MONGODB_URI, MONGODB_DB_NAME
    from services.mongodb import init_mongodb, get_collection, is_available

    init_mongodb(MONGODB_URI, MONGODB_DB_NAME)
    if not is_available():
        logger.warning("MongoDB not available. Skipping ingestion.")
        return

    _ingest_diseases()
    _ingest_specialist_mappings()
    logger.info("Dataset ingestion complete!")


def _ingest_diseases():
    col = __import__("services.mongodb", fromlist=["get_collection"]).get_collection("diseases")
    if col is None:
        return

    # Load data files
    desc_path = os.path.join(BASE, "data", "disease_descriptions.json")
    weights_path = os.path.join(BASE, "data", "symptom_weights.json")

    with open(desc_path, "r") as f:
        descriptions = json.load(f)
    with open(weights_path, "r") as f:
        weights = json.load(f)
        weights.pop("_comment", None)

    count = 0
    for disease, info in descriptions.items():
        disease_symptoms = list(weights.get(disease, {}).keys())
        doc = {
            "name": disease,
            "description": info.get("description", ""),
            "symptoms": disease_symptoms,
            "symptom_weights": weights.get(disease, {}),
            "precautions": info.get("precautions", []),
            "severityLevel": info.get("severity", "moderate"),
        }
        col.update_one({"name": disease}, {"$set": doc}, upsert=True)
        count += 1

    logger.info("Ingested %d diseases into MongoDB", count)


def _ingest_specialist_mappings():
    from services.specialist_mapping_service import DISEASE_TO_SPECIALIST
    col = __import__("services.mongodb", fromlist=["get_collection"]).get_collection("disease_mappings")
    if col is None:
        return

    count = 0
    for disease, specialist in DISEASE_TO_SPECIALIST.items():
        col.update_one(
            {"disease": disease},
            {"$set": {"disease": disease, "specialist": specialist}},
            upsert=True,
        )
        count += 1
    logger.info("Ingested %d specialist mappings into MongoDB", count)


if __name__ == "__main__":
    run()
