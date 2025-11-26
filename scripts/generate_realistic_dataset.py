# scripts/generate_realistic_dataset.py
"""
Generate a more realistic multi-modal dataset with ~100 cities,
distance-based costs, route availability rules, and minor randomness.
Output: data/multi_modal_routes_realistic.csv
"""

import os, math, random
import pandas as pd

os.makedirs("data", exist_ok=True)

# 100 city list
cities = [
    "Mumbai","Delhi","Bengaluru","Kolkata","Chennai","Hyderabad","Pune","Ahmedabad","Jaipur","Surat",
    "Lucknow","Kanpur","Nagpur","Indore","Thane","Bhopal","Visakhapatnam","Pimpri-Chinchwad","Patna","Vadodara",
    "Ghaziabad","Ludhiana","Agra","Nashik","Faridabad","Meerut","Rajkot","Kalyan","Vasai-Virar","Varanasi",
    "Srinagar","Dhanbad","Jodhpur","Amritsar","Nanded","Gwalior","Kolhapur","Bhubaneswar","Solapur","Mangalore",
    "Tiruchirappalli","BiharSharif","Aligarh","Tirunelveli","Bhiwandi","Saharanpur","Gorakhpur","Jalandhar","Jamshedpur","Salem",
    "Warangal","Mira-Bhayandar","Thiruvananthapuram","Bhilai","Ujjain","Durgapur","Asansol","Rourkela","Nellore","Dehradun",
    "Davanagere","Kozhikode","Akola","Kurnool","Nizamabad","Guntur","Amravati","Kakinada","Tirupati","Puri",
    "Shimoga","Ongole","Bathinda","Darbhanga","Satara","Proddatur","Kollam","Ambala","Siliguri","Rohtak",
    "Etawah","Orai","Haldwani","Muzaffarpur","Ramagundam","Baripada","Tezpur","Korba","Nagapattinam","Mahbubnagar",
    "Buxar","Sagar","Chittoor","Arrah","Bharuch","Balasore","Jalgaon","Palakkad","Unnao","Bilaspur"
]

# Haversine formula
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    import math
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    return R * 2 * math.asin(
        math.sqrt(
            math.sin((phi2 - phi1)/2)**2 +
            math.cos(phi1)*math.cos(phi2)*math.sin(math.radians(lon2 - lon1)/2)**2
        )
    )

# Import coordinates
from scripts.city_coords import city_coords

rows = []

for src in cities:
    for dst in cities:
        if src == dst:
            continue
        if src not in city_coords or dst not in city_coords:
            continue

        s_lat, s_lng = city_coords[src]
        d_lat, d_lng = city_coords[dst]

        distance_km = round(haversine(s_lat, s_lng, d_lat, d_lng), 1)

        # Train probability
        if distance_km <= 400: p_train = 0.95
        elif distance_km <= 800: p_train = 0.75
        elif distance_km <= 1200: p_train = 0.35
        else: p_train = 0.05

        # Flight probability
        if distance_km <= 200: p_flight = 0.05
        elif distance_km <= 800: p_flight = 0.35
        else: p_flight = 0.8

        # Choose which routes exist
        train_exists = random.random() < p_train
        flight_exists = random.random() < p_flight

        # Ensure at least one mode
        if not train_exists and not flight_exists:
            if distance_km <= 1200:
                train_exists = True
            else:
                flight_exists = True

        # Cost formulas
        train_cost = round((50 + distance_km * 0.5) * random.uniform(0.9, 1.1))
        flight_cost = round((800 + distance_km * 3.0) * random.uniform(0.9, 1.15))

        # Duration
        train_dur = round(distance_km / random.uniform(45, 90), 2)
        flight_dur = round(distance_km / random.uniform(450, 800), 2)

        if train_exists:
            rows.append([src, dst, "train", train_cost, train_dur, distance_km])
        if flight_exists:
            rows.append([src, dst, "flight", flight_cost, flight_dur, distance_km])

df = pd.DataFrame(rows, columns=["source","destination","mode","cost","duration_hours","distance_km"])

out = "data/multi_modal_routes_realistic.csv"
df.to_csv(out, index=False)
print("Generated realistic dataset:", len(df), "rows ->", out)
