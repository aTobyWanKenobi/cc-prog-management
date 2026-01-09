import csv
import random
from datetime import datetime, timedelta


def generate_reservations():
    # Read units
    units = []
    with open("units.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        units = [row["UnitName"] for row in reader]

    # Read terrains
    terrains = []
    with open("terreni.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        terrains = [row["Name"] for row in reader]

    # Reservation parameters
    start_date_base = datetime(2026, 7, 25)
    end_date_limit = datetime(2026, 8, 8)
    num_reservations = 30

    reservations = []
    for _ in range(num_reservations):
        terreno = random.choice(terrains)
        unit = random.choice(units)

        # Random day between start and end
        days_diff = (end_date_limit - start_date_base).days
        random_day = start_date_base + timedelta(days=random.randint(0, days_diff))

        # Random hour between 8 and 20
        random_hour = random.randint(8, 20)
        start_time = random_day.replace(hour=random_hour, minute=0, second=0)

        duration = random.randint(1, 4)

        reservations.append(
            {
                "TerrenoName": terreno,
                "UnitName": unit,
                "StartTime": start_time.isoformat(),
                "Duration": duration,
                "Status": "APPROVED",
            }
        )

    # Write to CSV
    with open("prenotazioni.csv", "w", newline="", encoding="utf-8") as f:
        fieldnames = ["TerrenoName", "UnitName", "StartTime", "Duration", "Status"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reservations)

    print(f"Generated {num_reservations} random reservations in prenotazioni.csv")


if __name__ == "__main__":
    generate_reservations()
