# scripts/generate_large_dataset.py
"""
Generate a large multi-modal routes CSV with ~100 cities.
Each ordered pair (A -> B) is a route (A != B).
Columns: source,destination,mode,cost,duration_hours,distance_km
"""

import os
import random
import pandas as pd

os.makedirs("data", exist_ok=True)

# 100 city list (mix of Indian cities and unique names)
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

# Ensure exactly 100 names
i = 1
while len(cities) < 100:
    cities.append(f"City_{i}")
    i += 1

rows = []
for src in cities:
    for dst in cities:
        if src == dst:
            continue
        # mode distribution: more trains than flights
        mode = random.choices(["flight", "train"], weights=[0.4, 0.6])[0]
        # distance in km
        distance_km = random.randint(80, 2500)
        if mode == "flight":
            speed = random.randint(450, 700)
            cost = int(distance_km * random.uniform(2.5, 5.0))
        else:
            speed = random.randint(45, 100)
            cost = int(distance_km * random.uniform(0.25, 1.6))
        duration_hours = round(distance_km / speed, 2)
        rows.append([src, dst, mode, cost, duration_hours, distance_km])

df = pd.DataFrame(rows, columns=["source", "destination", "mode", "cost", "duration_hours", "distance_km"])
out_path = "data/multi_modal_routes_100cities.csv"
df.to_csv(out_path, index=False)
print(f"Generated {len(df)} routes -> {out_path}")
