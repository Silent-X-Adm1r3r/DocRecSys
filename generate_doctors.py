"""
Doctor Database Generator
Generates a comprehensive JSON file with 500+ doctors across all Indian
state/UT capitals × 15+ specialties, using REAL hospital names.
Run once: python generate_doctors.py
"""
import json
import random
import os

# All 28 state capitals + 8 UT capitals
CITIES = {
    # State Capitals
    "Amaravati": "Andhra Pradesh",
    "Itanagar": "Arunachal Pradesh",
    "Dispur": "Assam",
    "Patna": "Bihar",
    "Raipur": "Chhattisgarh",
    "Panaji": "Goa",
    "Gandhinagar": "Gujarat",
    "Chandigarh": "Haryana",
    "Shimla": "Himachal Pradesh",
    "Ranchi": "Jharkhand",
    "Bengaluru": "Karnataka",
    "Thiruvananthapuram": "Kerala",
    "Bhopal": "Madhya Pradesh",
    "Mumbai": "Maharashtra",
    "Imphal": "Manipur",
    "Shillong": "Meghalaya",
    "Aizawl": "Mizoram",
    "Kohima": "Nagaland",
    "Bhubaneswar": "Odisha",
    "Chandigarh_PB": "Punjab",
    "Jaipur": "Rajasthan",
    "Gangtok": "Sikkim",
    "Chennai": "Tamil Nadu",
    "Hyderabad": "Telangana",
    "Agartala": "Tripura",
    "Lucknow": "Uttar Pradesh",
    "Dehradun": "Uttarakhand",
    "Kolkata": "West Bengal",
    # UT Capitals
    "Port Blair": "Andaman and Nicobar Islands",
    "New Delhi": "Delhi",
    "Kavaratti": "Lakshadweep",
    "Puducherry": "Puducherry",
    "Srinagar": "Jammu and Kashmir",
    "Leh": "Ladakh",
    "Daman": "Dadra Nagar Haveli and Daman Diu",
    "Silvassa": "Dadra Nagar Haveli and Daman Diu",
}

# Fix Chandigarh duplicate (shared by Haryana/Punjab)
# We'll handle this in the code

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

# Real Indian hospital names by city/region
HOSPITALS_BY_CITY = {
    "Bengaluru": ["Manipal Hospital", "Narayana Health", "Apollo Hospital", "Fortis Hospital", "Columbia Asia", "Aster CMI", "BGS Gleneagles", "Sakra World Hospital", "MS Ramaiah Hospital"],
    "Chennai": ["Apollo Hospital", "MIOT International", "Fortis Malar Hospital", "Global Hospital", "Sri Ramachandra Medical Centre", "Kauvery Hospital", "Billroth Hospital", "Vijaya Hospital"],
    "Mumbai": ["Kokilaben Dhirubhai Ambani Hospital", "Lilavati Hospital", "Hinduja Hospital", "Breach Candy Hospital", "Nanavati Hospital", "Jaslok Hospital", "Tata Memorial Hospital", "Wockhardt Hospital"],
    "New Delhi": ["AIIMS Delhi", "Sir Ganga Ram Hospital", "Fortis Escorts Heart Institute", "Max Super Specialty Hospital", "Medanta Hospital", "BLK-Max Hospital", "Indraprastha Apollo Hospital", "Safdarjung Hospital"],
    "Hyderabad": ["Apollo Hospital", "KIMS Hospital", "Yashoda Hospital", "Care Hospital", "Continental Hospital", "AIG Hospital", "Sunshine Hospital", "Global Hospital"],
    "Kolkata": ["Apollo Gleneagles", "Fortis Hospital", "Medica Super Specialty", "AMRI Hospital", "Peerless Hospital", "Ruby General Hospital", "Woodlands Hospital", "Calcutta Medical Research Institute"],
    "Jaipur": ["Fortis Escorts Hospital", "Narayana Multispeciality Hospital", "SMS Hospital", "Manipal Hospital", "Eternal Hospital", "CK Birla Hospital", "Mahatma Gandhi Hospital"],
    "Lucknow": ["Medanta Hospital", "Sahara Hospital", "King George Medical University", "Charak Hospital", "Apollo Hospital", "Mayo Hospital", "Ram Manohar Lohia Hospital"],
    "Bhopal": ["AIIMS Bhopal", "Bansal Hospital", "Chirayu Medical College", "Noble Hospital", "People's Hospital", "Hamidia Hospital"],
    "Bhubaneswar": ["AIIMS Bhubaneswar", "KIMS Hospital", "Apollo Hospital", "Sum Hospital", "Sparsh Hospital", "Care Hospital"],
    "Patna": ["AIIMS Patna", "Indira Gandhi Institute of Medical Sciences", "Paras Hospital", "Ruban Memorial Hospital", "Mahavir Cancer Institute", "Patna Medical College"],
    "Chandigarh": ["PGIMER", "Fortis Hospital", "Alchemist Hospital", "Max Hospital", "Ivy Hospital", "Grecian Hospital"],
    "Raipur": ["AIIMS Raipur", "Ramkrishna Care Hospital", "Shri Balaji Hospital", "VY Hospital", "MMI Narayana Hospital"],
    "Thiruvananthapuram": ["KIMS Hospital", "Sree Chitra Tirunal Institute", "Ananthapuri Hospital", "SK Hospital", "SUT Hospital", "Cosmopolitan Hospital"],
    "Ranchi": ["Medanta Hospital", "Rajendra Institute of Medical Sciences", "Orchid Medical Centre", "Bhagwan Mahavir Medica", "TMH Hospital"],
    "Dehradun": ["Max Hospital", "Synergy Hospital", "Doon Hospital", "Shri Mahant Indiresh Hospital", "Himalayan Hospital"],
    "Shimla": ["IGMC Hospital", "Kamla Nehru Hospital", "Deen Dayal Upadhyay Hospital", "Max Hospital Shimla"],
    "Panaji": ["Goa Medical College", "Manipal Hospital Goa", "Healthway Hospital", "Victor Hospital"],
    "Gandhinagar": ["GMERS Medical College", "Apollo Hospital Ahmedabad", "Sterling Hospital", "Zydus Hospital", "HCG Hospital"],
    "Imphal": ["RIMS Imphal", "Shija Hospital", "Raj Medicity", "Babina Hospital"],
    "Shillong": ["NEIGRIHMS", "Nazareth Hospital", "Woodland Hospital", "Bethany Hospital"],
    "Aizawl": ["Civil Hospital Aizawl", "Adventist Hospital", "Trinity Hospital"],
    "Kohima": ["Naga Hospital", "Eden Medical Centre", "Bethel Medical Centre"],
    "Itanagar": ["TRIHMS", "Ramakrishna Mission Hospital", "Heema Hospital"],
    "Agartala": ["Agartala Government Medical College", "ILS Hospital", "GBP Hospital"],
    "Gangtok": ["STNM Hospital", "Central Referral Hospital", "Manipal Hospital Gangtok"],
    "Dispur": ["GMCH Guwahati", "Nemcare Hospital", "Excelcare Hospital", "Dispur Hospital", "Apollo Excelcare"],
    "Amaravati": ["Guntur Government Hospital", "NRI Medical College", "Apollo Hospital Guntur"],
    "Port Blair": ["GB Pant Hospital", "ANIMS Hospital"],
    "Puducherry": ["JIPMER", "Sri Lakshmi Narayana Medical College", "Aarupadai Veedu Medical College"],
    "Srinagar": ["SKIMS Hospital", "SMHS Hospital", "Bone and Joint Hospital", "Shri Maharaja Hari Singh Hospital"],
    "Leh": ["SNM Hospital Leh", "District Hospital Leh"],
    "Kavaratti": ["Indira Gandhi Hospital Kavaratti"],
    "Daman": ["Government Hospital Daman", "District Hospital Daman"],
    "Silvassa": ["Vinoba Bhave Hospital", "Shri Vinoba Bhave Civil Hospital"],
}

# Indian first names and last names for generating realistic doctor names
MALE_FIRST_NAMES = [
    "Rajesh", "Suresh", "Anil", "Vikram", "Sanjay", "Deepak", "Ramesh", "Arjun",
    "Pradeep", "Manish", "Alok", "Vivek", "Kiran", "Manoj", "Ashok", "Nitin",
    "Gaurav", "Amit", "Rahul", "Ajay", "Rohit", "Sachin", "Harish", "Mukesh",
    "Praveen", "Ravi", "Arun", "Dinesh", "Naveen", "Siddharth", "Abhishek",
    "Rakesh", "Vinod", "Yogesh", "Mahesh", "Sunil", "Tarun", "Pankaj",
    "Sandeep", "Hemant", "Akhil", "Varun", "Dev", "Rohan", "Kunal",
    "Vishal", "Anand", "Neeraj", "Kapil", "Mohit", "Jitendra", "Bharat",
]
FEMALE_FIRST_NAMES = [
    "Ananya", "Priya", "Sneha", "Meera", "Kavitha", "Sunita", "Rekha", "Pooja",
    "Swati", "Nithya", "Deepa", "Lakshmi", "Divya", "Shruti", "Gayathri",
    "Neha", "Aishwarya", "Ranjani", "Padma", "Shobha", "Jyoti", "Anjali",
    "Shalini", "Geeta", "Radha", "Savitri", "Usha", "Vandana", "Archana",
    "Smita", "Pallavi", "Seema", "Rani", "Bhavana", "Chitra", "Aarti",
    "Aparna", "Tanvi", "Ishita", "Ritika", "Megha", "Komal", "Renuka",
]
LAST_NAMES = [
    "Sharma", "Kumar", "Patel", "Reddy", "Gupta", "Iyer", "Nair", "Menon",
    "Bhat", "Joshi", "Verma", "Desai", "Pillai", "Rajan", "Das", "Rao",
    "Saxena", "Mehta", "Kapoor", "Agarwal", "Chauhan", "Srivastava",
    "Banerjee", "Mukherjee", "Chatterjee", "Singh", "Thakur", "Chandra",
    "Mishra", "Pandey", "Tiwari", "Dubey", "Yadav", "Jain", "Malhotra",
    "Sethi", "Khanna", "Basu", "Dutta", "Sengupta", "Choudhury", "Hegde",
    "Kulkarni", "Patil", "Bhatt", "Naidu", "Shetty", "Prasad", "Mohan",
    "Babu", "Subramaniam", "Krishnan", "Varma", "Nambiar", "Kaul",
]

AVAILABLE_DAYS_OPTIONS = [
    "Mon-Fri", "Mon-Sat", "Mon-Wed-Fri", "Tue-Thu-Sat",
    "Mon-Fri", "All Days", "Mon-Sat", "Mon-Fri",
]

def generate_phone():
    """Generate a realistic Indian mobile number."""
    prefixes = ["98", "97", "96", "95", "94", "93", "91", "90", "89", "88", "87", "86", "85", "84", "83", "82", "81", "80", "79", "78", "77", "76", "75", "74", "73", "72", "71", "70"]
    prefix = random.choice(prefixes)
    return f"+91-{prefix}{random.randint(100,999)}-{random.randint(10000,99999)}"

def generate_doctor(city, state, specialty, used_names):
    """Generate a single doctor entry."""
    while True:
        gender = random.choice(["M", "F"])
        if gender == "M":
            first = random.choice(MALE_FIRST_NAMES)
        else:
            first = random.choice(FEMALE_FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"Dr. {first} {last}"
        if name not in used_names:
            used_names.add(name)
            break

    # Get hospitals for city, fall back to generic
    hospitals = HOSPITALS_BY_CITY.get(city, [f"{city} General Hospital", f"{city} Medical College", f"District Hospital {city}"])
    hospital = random.choice(hospitals)

    experience = random.randint(5, 35)
    rating = round(random.uniform(3.5, 5.0), 1)
    fee_base = {"General Physician": 300, "Cardiologist": 800, "Neurologist": 800,
                "Dermatologist": 600, "Pulmonologist": 700, "Psychiatrist": 700,
                "Gastroenterologist": 700, "Pediatrician": 500, "Orthopedic Surgeon": 800,
                "ENT Specialist": 600, "Gynecologist": 700, "Oncologist": 1000,
                "Nephrologist": 800, "Endocrinologist": 700, "Urologist": 700,
                "Ophthalmologist": 600, "Rheumatologist": 700,
                "Infectious Disease Specialist": 600}
    base = fee_base.get(specialty, 500)
    fee = base + random.randint(-100, 300) + (experience * 10)
    available_days = random.choice(AVAILABLE_DAYS_OPTIONS)

    return {
        "name": name,
        "specialization": specialty,
        "hospital": hospital,
        "city": city.replace("_PB", ""),  # Handle Chandigarh_PB
        "state": state,
        "experience_years": experience,
        "rating": rating,
        "consultation_fee": f"₹{fee}",
        "available_days": available_days,
        "phone": generate_phone(),
    }


def main():
    random.seed(42)  # Reproducible
    used_names = set()
    doctors = []

    for city, state in CITIES.items():
        actual_city = city.replace("_PB", "")
        for specialty in SPECIALTIES:
            # Ensure at least 1 doctor per specialty per city
            # Major cities get more doctors
            major_cities = ["Bengaluru", "Chennai", "Mumbai", "New Delhi", "Hyderabad",
                          "Kolkata", "Jaipur", "Lucknow", "Bhopal", "Bhubaneswar",
                          "Patna", "Chandigarh", "Thiruvananthapuram", "Ranchi", "Dehradun"]
            if city in major_cities:
                count = random.randint(1, 3)
            else:
                count = 1

            for _ in range(count):
                doc = generate_doctor(city, state, specialty, used_names)
                doctors.append(doc)

    # Sort by city then specialty
    doctors.sort(key=lambda d: (d["city"], d["specialization"], -d["rating"]))

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "doctors_india.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(doctors, f, indent=2, ensure_ascii=False)

    # Stats
    cities_set = set(d["city"] for d in doctors)
    specs_set = set(d["specialization"] for d in doctors)
    print(f"Generated {len(doctors)} doctors across {len(cities_set)} cities and {len(specs_set)} specialties")
    print(f"Saved to {output_path}")

    # Verify coverage
    for city in set(c.replace("_PB", "") for c in CITIES.keys()):
        city_docs = [d for d in doctors if d["city"] == city]
        city_specs = set(d["specialization"] for d in city_docs)
        missing = set(SPECIALTIES) - city_specs
        if missing:
            print(f"  WARNING: {city} missing: {missing}")


if __name__ == "__main__":
    main()
