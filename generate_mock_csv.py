import csv
import random
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Pattuglia, Challenge

def generate_mock_csv():
    db = SessionLocal()
    pattuglie = db.query(Pattuglia).all()
    challenges = db.query(Challenge).all()
    
    if not pattuglie or not challenges:
        print("No pattuglie or challenges found. Cannot generate mock data.")
        return

    print(f"Found {len(pattuglie)} pattuglie and {len(challenges)} challenges.")

    completions = []
    # Generate 50 random completions
    for _ in range(50):
        p = random.choice(pattuglie)
        c = random.choice(challenges)
        # Random time in the last 7 days
        days_ago = random.randint(0, 7)
        seconds_ago = random.randint(0, 86400)
        timestamp = datetime.now() - timedelta(days=days_ago, seconds=seconds_ago)
        
        completions.append({
            "PattugliaName": p.name,
            "ChallengeName": c.name,
            "Timestamp": timestamp.isoformat()
        })

    with open("completions.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["PattugliaName", "ChallengeName", "Timestamp"])
        writer.writeheader()
        writer.writerows(completions)
    
    print(f"Generated completions.csv with {len(completions)} entries.")
    db.close()

if __name__ == "__main__":
    generate_mock_csv()
