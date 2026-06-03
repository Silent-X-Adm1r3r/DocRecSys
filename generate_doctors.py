"""
Doctor Database Generator
Generates a comprehensive JSON file with 500+ doctors across specialties, using generic hospital names.
Run once: python generate_doctors.py
"""
import json
import random
import os

SPECIALTIES = [
    "General Physician",
    "Cardiologist",
    "Neurologist",
    "Dermatologist",
    "Pulmonologist",
    "Psychiatrist",
    "Gastroenterologist",
    "Pediatrician",
    "Orthopedic Surgeon",
    "ENT Specialist",
    "Gynecologist",
    "Oncologist",
    "Nephrologist",
    "Endocrinologist",
    "Urologist",
    "Ophthalmologist",
    "Rheumatologist",
    "Infectious Disease Specialist",
]

HOSPITALS = [
    "Apollo Hospital", "Manipal Hospital", "Narayana Health", "Fortis Hospital",
    "Max Super Specialty Hospital", "Medanta Hospital", "Global Hospital",
    "Care Hospital", "AIIMS", "City General Hospital", "National Medical Centre"
]

MALE_FIRST_NAMES = ["Rajesh", "Suresh", "Anil", "Vikram", "Sanjay", "Deepak", "Ramesh", "Arjun", "Pradeep", "Manish"]
FEMALE_FIRST_NAMES = ["Ananya", "Priya", "Sneha", "Meera", "Kavitha", "Sunita", "Rekha", "Pooja", "Swati", "Nithya"]
LAST_NAMES = ["Sharma", "Kumar", "Patel", "Reddy", "Gupta", "Iyer", "Nair", "Menon", "Bhat", "Joshi", "Verma", "Desai"]
AVAILABLE_DAYS_OPTIONS = ["Mon-Fri", "Mon-Sat", "Mon-Wed-Fri", "Tue-Thu-Sat", "All Days"]

def generate_phone():
    prefixes = ["98", "97", "96", "95", "94", "93", "91", "90"]
    return f"+91-{random.choice(prefixes)}{random.randint(100,999)}-{random.randint(10000,99999)}"

def generate_doctor(specialty):
    first = random.choice(MALE_FIRST_NAMES + FEMALE_FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    name = f"Dr. {first} {last}"

    hospital = random.choice(HOSPITALS)
    experience = random.randint(5, 35)
    rating = round(random.uniform(3.5, 5.0), 1)
    base = 500
    fee = base + random.randint(-100, 300) + (experience * 10)
    
    return {
        "name": name,
        "specialization": specialty,
        "hospital": hospital,
        "experience_years": experience,
        "rating": rating,
        "consultation_fee": f"₹{fee}",
        "available_days": random.choice(AVAILABLE_DAYS_OPTIONS),
        "phone": generate_phone(),
    }

def main():
    random.seed(42)
    used_names = set()
    doctors = []

    for specialty in SPECIALTIES:
        count = random.randint(15, 30) # Generate 15-30 doctors per specialty
        for _ in range(count):
            doctors.append(generate_doctor(specialty))

    doctors.sort(key=lambda d: (d["specialization"], -d["rating"]))

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "doctors_india.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(doctors, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(doctors)} doctors across {len(SPECIALTIES)} specialties")
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    main()
