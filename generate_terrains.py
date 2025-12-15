import csv
import random
import json
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Unita

# Campo Blenio approximate center
CENTER_LAT = 46.538
CENTER_LON = 8.955

TAGS = ["SPORT", "CERIMONIA", "BOSCO", "AC", "NOTTURNO"]

def generate_terrains():
    terrains = []
    for i in range(1, 11): # 10 terrains
        name = f"Terreno {i}"
        tags = random.sample(TAGS, k=random.randint(1, 2))
        
        # Random offset for center
        lat_offset = random.uniform(-0.005, 0.005)
        lon_offset = random.uniform(-0.005, 0.005)
        lat = CENTER_LAT + lat_offset
        lon = CENTER_LON + lon_offset
        
        # Simple square polygon around center
        poly_size = 0.001
        polygon = [
            [lat - poly_size, lon - poly_size],
            [lat + poly_size, lon - poly_size],
            [lat + poly_size, lon + poly_size],
            [lat - poly_size, lon + poly_size],
            [lat - poly_size, lon - poly_size] # Close loop
        ]
        
        terrains.append({
            "Name": name,
            "Tags": ",".join(tags),
            "CenterLat": str(lat),
            "CenterLon": str(lon),
            "Polygon": json.dumps(polygon)
        })
        
    with open("terreni.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Name", "Tags", "CenterLat", "CenterLon", "Polygon"])
        writer.writeheader()
        writer.writerows(terrains)
    print(f"Generated terreni.csv with {len(terrains)} entries.")
    return terrains

def generate_reservations(terrains):
    db = SessionLocal()
    units = db.query(Unita).all()
    
    if not units:
        print("No units found. Cannot generate reservations.")
        return

    reservations = []
    # Generate 30 random reservations
    for _ in range(30):
        t = random.choice(terrains)
        u = random.choice(units)
        
        # Random day in next 7 days
        days_ahead = random.randint(0, 7)
        # Random hour between 8 and 22 (minus max duration)
        hour = random.randint(8, 18) 
        duration = random.randint(1, 4)
        
        start_time = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
        
        status = random.choice(["PENDING", "APPROVED"])
        
        reservations.append({
            "TerrenoName": t["Name"],
            "UnitName": u.name,
            "StartTime": start_time.isoformat(),
            "Duration": duration,
            "Status": status
        })
        
    with open("prenotazioni.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["TerrenoName", "UnitName", "StartTime", "Duration", "Status"])
        writer.writeheader()
        writer.writerows(reservations)
    print(f"Generated prenotazioni.csv with {len(reservations)} entries.")
    db.close()

if __name__ == "__main__":
    terrains = generate_terrains()
    generate_reservations(terrains)
