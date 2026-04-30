"""
Disease-Symptom Dataset Generator
Creates a comprehensive CSV mapping diseases to symptoms for ML training.
Covers ~50 diseases with structured symptom columns.
"""
import csv, os, random

# 132 symptom columns from the standard Kaggle disease prediction format
SYMPTOM_COLUMNS = [
    "itching","skin_rash","nodal_skin_eruptions","continuous_sneezing","shivering",
    "chills","joint_pain","stomach_pain","acidity","ulcers_on_tongue",
    "muscle_wasting","vomiting","burning_micturition","spotting_urination","fatigue",
    "weight_gain","anxiety","cold_hands_and_feets","mood_swings","weight_loss",
    "restlessness","lethargy","patches_in_throat","irregular_sugar_level","cough",
    "high_fever","sunken_eyes","breathlessness","sweating","dehydration",
    "indigestion","headache","yellowish_skin","dark_urine","nausea",
    "loss_of_appetite","pain_behind_the_eyes","back_pain","constipation","abdominal_pain",
    "diarrhoea","mild_fever","yellow_urine","yellowing_of_eyes","acute_liver_failure",
    "fluid_overload","swelling_of_stomach","swelled_lymph_nodes","malaise","blurred_and_distorted_vision",
    "phlegm","throat_irritation","redness_of_eyes","sinus_pressure","runny_nose",
    "congestion","chest_pain","weakness_in_limbs","fast_heart_rate","excessive_hunger",
    "extra_marital_contacts","drying_and_tingling_lips","slurred_speech","knee_pain","hip_joint_pain",
    "muscle_weakness","stiff_neck","swelling_joints","movement_stiffness","spinning_movements",
    "loss_of_balance","unsteadiness","weakness_of_one_body_side","loss_of_smell","bladder_discomfort",
    "foul_smell_of_urine","continuous_feel_of_urine","passage_of_gases","internal_itching","toxic_look_typhos",
    "depression","irritability","muscle_pain","altered_sensorium","red_spots_over_body",
    "belly_pain","abnormal_menstruation","dischromic_patches","watering_from_eyes","increased_appetite",
    "polyuria","family_history","mucoid_sputum","rusty_sputum","lack_of_concentration",
    "visual_disturbances","receiving_blood_transfusion","receiving_unsterile_injections","coma","stomach_bleeding",
    "distention_of_abdomen","history_of_alcohol_consumption","blood_in_sputum","prominent_veins_on_calf",
    "palpitations","painful_walking","pus_filled_pimples","blackheads","scurring",
    "skin_peeling","silver_like_dusting","small_dents_in_nails","inflammatory_nails","blister",
    "red_sore_around_nose","yellow_crust_ooze","prognosis","swollen_legs","swollen_blood_vessels",
    "puffy_face_and_eyes","enlarged_thyroid","brittle_nails","swollen_extremeties","excessive_hunger_e",
    "drying_and_tingling_lips_e","obesity","sunken_eyes_e","ear_pain","neck_pain",
    "bruising","hair_loss","loss_of_consciousness","seizure","high_bp","low_bp",
    "body_ache","skin_darkening","numbness","tingling","insomnia","acne",
    "stiff_neck_e","bloody_stool"
]

# Disease -> list of symptom names that are positive
DISEASE_SYMPTOMS = {
    "Fungal infection": ["itching","skin_rash","nodal_skin_eruptions","dischromic_patches"],
    "Allergy": ["continuous_sneezing","shivering","chills","watering_from_eyes","runny_nose","congestion"],
    "GERD": ["stomach_pain","acidity","ulcers_on_tongue","vomiting","cough","chest_pain","indigestion","nausea"],
    "Chronic Cholestasis": ["itching","vomiting","yellowish_skin","nausea","loss_of_appetite","abdominal_pain","yellowing_of_eyes","dark_urine"],
    "Drug Reaction": ["itching","skin_rash","stomach_pain","burning_micturition","spotting_urination","fatigue"],
    "Peptic Ulcer Disease": ["vomiting","indigestion","loss_of_appetite","abdominal_pain","passage_of_gases","internal_itching","stomach_pain","acidity"],
    "AIDS": ["muscle_wasting","patches_in_throat","high_fever","extra_marital_contacts","fatigue","weight_loss"],
    "Diabetes": ["fatigue","weight_loss","restlessness","lethargy","irregular_sugar_level","blurred_and_distorted_vision","obesity","excessive_hunger","polyuria","increased_appetite"],
    "Gastroenteritis": ["vomiting","sunken_eyes","dehydration","diarrhoea","nausea","abdominal_pain","stomach_pain","fatigue","loss_of_appetite"],
    "Bronchial Asthma": ["fatigue","cough","high_fever","breathlessness","family_history","mucoid_sputum","phlegm","chest_pain"],
    "Hypertension": ["headache","chest_pain","dizziness","loss_of_balance","high_bp","breathlessness","fatigue","blurred_and_distorted_vision"],
    "Migraine": ["acidity","indigestion","headache","blurred_and_distorted_vision","excessive_hunger","stiff_neck","depression","irritability","visual_disturbances","nausea"],
    "Cervical Spondylosis": ["back_pain","weakness_in_limbs","neck_pain","dizziness","loss_of_balance","stiff_neck"],
    "Paralysis (Brain Hemorrhage)": ["vomiting","headache","weakness_of_one_body_side","altered_sensorium","loss_of_balance","slurred_speech","loss_of_consciousness"],
    "Jaundice": ["itching","vomiting","fatigue","weight_loss","high_fever","yellowish_skin","dark_urine","abdominal_pain","yellowing_of_eyes","loss_of_appetite","nausea"],
    "Malaria": ["chills","vomiting","high_fever","sweating","headache","nausea","muscle_pain","body_ache","fatigue","loss_of_appetite","diarrhoea"],
    "Chicken Pox": ["itching","skin_rash","fatigue","lethargy","high_fever","headache","loss_of_appetite","mild_fever","swelled_lymph_nodes","malaise","red_spots_over_body"],
    "Dengue": ["skin_rash","chills","joint_pain","vomiting","fatigue","high_fever","headache","nausea","loss_of_appetite","pain_behind_the_eyes","back_pain","muscle_pain","red_spots_over_body","body_ache"],
    "Typhoid": ["chills","vomiting","fatigue","high_fever","headache","nausea","constipation","abdominal_pain","diarrhoea","loss_of_appetite","belly_pain","sweating","toxic_look_typhos"],
    "Hepatitis A": ["joint_pain","vomiting","yellowish_skin","dark_urine","nausea","loss_of_appetite","abdominal_pain","diarrhoea","mild_fever","yellowing_of_eyes","muscle_pain","fatigue"],
    "Hepatitis B": ["itching","fatigue","lethargy","yellowish_skin","dark_urine","loss_of_appetite","abdominal_pain","yellow_urine","yellowing_of_eyes","malaise","receiving_blood_transfusion","receiving_unsterile_injections"],
    "Hepatitis C": ["fatigue","yellowish_skin","nausea","loss_of_appetite","yellowing_of_eyes","family_history","receiving_blood_transfusion","receiving_unsterile_injections"],
    "Hepatitis D": ["joint_pain","vomiting","fatigue","yellowish_skin","dark_urine","nausea","loss_of_appetite","abdominal_pain","yellowing_of_eyes"],
    "Hepatitis E": ["joint_pain","vomiting","fatigue","high_fever","yellowish_skin","dark_urine","nausea","loss_of_appetite","abdominal_pain","yellowing_of_eyes","coma","stomach_bleeding","acute_liver_failure"],
    "Alcoholic Hepatitis": ["vomiting","yellowish_skin","abdominal_pain","swelling_of_stomach","distention_of_abdomen","history_of_alcohol_consumption","fluid_overload","loss_of_appetite"],
    "Tuberculosis": ["chills","vomiting","fatigue","weight_loss","cough","high_fever","breathlessness","sweating","loss_of_appetite","mild_fever","yellowing_of_eyes","swelled_lymph_nodes","malaise","phlegm","chest_pain","blood_in_sputum"],
    "Common Cold": ["continuous_sneezing","chills","fatigue","cough","high_fever","headache","swelled_lymph_nodes","malaise","phlegm","throat_irritation","redness_of_eyes","sinus_pressure","runny_nose","congestion","chest_pain","loss_of_smell","muscle_pain"],
    "Pneumonia": ["chills","fatigue","cough","high_fever","breathlessness","sweating","malaise","phlegm","chest_pain","fast_heart_rate","rusty_sputum","loss_of_appetite","body_ache"],
    "Dimorphic Hemorrhoids (Piles)": ["constipation","pain_during_bowel_movements","pain_in_anal_region","bloody_stool","irritation_in_anus"],
    "Heart Attack": ["vomiting","breathlessness","sweating","chest_pain","fatigue","anxiety","fast_heart_rate","loss_of_consciousness","body_ache","nausea"],
    "Varicose Veins": ["fatigue","cramps","bruising","obesity","swollen_legs","swollen_blood_vessels","prominent_veins_on_calf","painful_walking"],
    "Hypothyroidism": ["fatigue","weight_gain","cold_hands_and_feets","mood_swings","lethargy","dizziness","puffy_face_and_eyes","enlarged_thyroid","brittle_nails","swollen_extremeties","depression","irritability","abnormal_menstruation","hair_loss","obesity"],
    "Hyperthyroidism": ["fatigue","mood_swings","weight_loss","restlessness","sweating","diarrhoea","fast_heart_rate","excessive_hunger","muscle_weakness","irritability","abnormal_menstruation","insomnia","anxiety"],
    "Hypoglycemia": ["vomiting","fatigue","anxiety","sweating","headache","nausea","blurred_and_distorted_vision","excessive_hunger","drying_and_tingling_lips","slurred_speech","irritability","palpitations","shivering","altered_sensorium"],
    "Osteoarthritis": ["joint_pain","knee_pain","hip_joint_pain","muscle_weakness","stiff_neck","swelling_joints","movement_stiffness","painful_walking","neck_pain","back_pain"],
    "Arthritis": ["muscle_weakness","stiff_neck","swelling_joints","movement_stiffness","loss_of_appetite","fatigue","joint_pain","painful_walking","neck_pain"],
    "Vertigo": ["vomiting","headache","nausea","spinning_movements","loss_of_balance","unsteadiness","dizziness"],
    "Acne": ["skin_rash","pus_filled_pimples","blackheads","scurring","acne","itching"],
    "Urinary Tract Infection": ["burning_micturition","spotting_urination","dark_urine","bladder_discomfort","foul_smell_of_urine","continuous_feel_of_urine","abdominal_pain","back_pain","high_fever","fatigue","nausea"],
    "Psoriasis": ["skin_rash","joint_pain","skin_peeling","silver_like_dusting","small_dents_in_nails","inflammatory_nails","itching","red_spots_over_body"],
    "Impetigo": ["skin_rash","high_fever","blister","red_sore_around_nose","yellow_crust_ooze","itching"],
    "COVID-19": ["cough","high_fever","fatigue","breathlessness","headache","loss_of_smell","body_ache","throat_irritation","chills","diarrhoea","chest_pain","nausea","loss_of_appetite","muscle_pain"],
    "Influenza": ["high_fever","cough","fatigue","body_ache","headache","chills","sweating","muscle_pain","throat_irritation","runny_nose","loss_of_appetite","shivering","joint_pain","mild_fever"],
    "Anxiety Disorder": ["anxiety","restlessness","fatigue","palpitations","sweating","insomnia","breathlessness","chest_pain","irritability","lack_of_concentration","mood_swings","nausea","numbness","tingling","dizziness","headache","muscle_pain"],
    "Depression": ["depression","fatigue","insomnia","loss_of_appetite","weight_loss","lack_of_concentration","mood_swings","irritability","restlessness","lethargy","headache","anxiety","body_ache"],
    "Kidney Stones": ["abdominal_pain","back_pain","burning_micturition","nausea","vomiting","dark_urine","bloody_stool","fatigue","high_fever","bladder_discomfort"],
    "Chronic Kidney Disease": ["fatigue","weight_loss","loss_of_appetite","nausea","swollen_legs","puffy_face_and_eyes","dark_urine","high_bp","breathlessness","numbness","itching","muscle_pain"],
    "Irritable Bowel Syndrome": ["abdominal_pain","constipation","diarrhoea","passage_of_gases","stomach_pain","bloating","nausea","fatigue","anxiety","mood_swings","loss_of_appetite"],
    "Anemia": ["fatigue","weakness_in_limbs","dizziness","headache","breathlessness","fast_heart_rate","cold_hands_and_feets","loss_of_appetite","brittle_nails","hair_loss","numbness"],
    "Epilepsy": ["seizure","loss_of_consciousness","altered_sensorium","headache","fatigue","muscle_pain","anxiety","dizziness","nausea","mood_swings"],
}

def generate_dataset():
    """Generate training CSV with symptom binary columns."""
    # Use all unique symptoms from the disease mappings
    all_symptoms = set()
    for symptoms in DISEASE_SYMPTOMS.values():
        all_symptoms.update(symptoms)
    all_symptoms = sorted(all_symptoms)

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "symptom_disease_data.csv")

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Header: all symptoms + prognosis (disease)
        header = all_symptoms + ["prognosis"]
        writer.writerow(header)

        random.seed(42)
        for disease, symptoms in DISEASE_SYMPTOMS.items():
            # Generate multiple training samples per disease with slight variations
            for _ in range(40):
                row = []
                for s in all_symptoms:
                    if s in symptoms:
                        # 85% chance symptom is present (simulates real-world variation)
                        row.append(1 if random.random() < 0.85 else 0)
                    else:
                        # 3% chance of noise (false positive)
                        row.append(1 if random.random() < 0.03 else 0)
                row.append(disease)
                writer.writerow(row)

    print(f"Generated dataset with {len(DISEASE_SYMPTOMS)} diseases, {len(all_symptoms)} symptoms")
    print(f"Total samples: {len(DISEASE_SYMPTOMS) * 40}")
    print(f"Saved to {output_path}")
    return output_path

if __name__ == "__main__":
    generate_dataset()
