import csv
import os
from datetime import datetime, timedelta

from passlib.context import CryptContext

from app.database import Base, SessionLocal, engine
from app.models import (
    Prenotazione,
    Terreno,
    TerrenoCategoria,
    Unita,
    User,
)

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def get_password_hash(password):
    return pwd_context.hash(password)


def reset_and_init_db(db=None):
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True

    try:
        print("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully.")

        seed_dir = os.path.join("data", "seed")

        # --- Units Population ---
        unita_file = os.path.join(seed_dir, "unita.csv")
        if not os.path.exists(unita_file):
            raise FileNotFoundError(f"Missing required seed file: {unita_file}")

        print(f"Reading units from {unita_file}...")
        with open(unita_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            required_cols = {"UnitName", "Tipo", "Sottocampo"}
            if not required_cols.issubset(set(reader.fieldnames or [])):
                raise ValueError(f"unita.csv is missing required columns. Found: {reader.fieldnames}")

            for row_idx, row in enumerate(reader, start=2):
                unit_name = row["UnitName"].strip()
                tipo = row["Tipo"].strip()
                sottocampo = row["Sottocampo"].strip()
                if not sottocampo:
                    sottocampo = None

                if not unit_name or not tipo:
                    raise ValueError(f"unita.csv row {row_idx}: UnitName and Tipo are required.")

                exists = db.query(Unita).filter(Unita.name == unit_name).first()
                if not exists:
                    new_unita = Unita(name=unit_name, tipo=tipo, sottocampo=sottocampo)
                    db.add(new_unita)
        db.commit()
        print("Units populated from CSV.")

        # --- Terreni Population ---
        terreni_file = os.path.join(seed_dir, "terreni.csv")
        if not os.path.exists(terreni_file):
            raise FileNotFoundError(f"Missing required seed file: {terreni_file}")

        print(f"Reading terreni from {terreni_file}...")
        with open(terreni_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            required_cols = {"Name", "Tags", "CenterLat", "CenterLon", "Polygon"}
            if not required_cols.issubset(set(reader.fieldnames or [])):
                raise ValueError(f"terreni.csv is missing required columns. Found: {reader.fieldnames}")

            for row_idx, row in enumerate(reader, start=2):
                t_name = row["Name"].strip()
                t_tags = row["Tags"].strip().upper()
                t_center_lat = row["CenterLat"].strip()
                t_center_lon = row["CenterLon"].strip()
                t_polygon = row["Polygon"].strip()
                t_description = row.get("Description", "").strip()
                t_image_urls = row.get("ImageUrls", "[]").strip()

                if not t_name or not t_center_lat or not t_center_lon or not t_polygon:
                    raise ValueError(f"terreni.csv row {row_idx}: Missing required fields.")

                is_valid, invalid_tags = TerrenoCategoria.validate_tags(t_tags)
                if not is_valid:
                    raise ValueError(f"terreni.csv row {row_idx}: Invalid tags: {invalid_tags}.")

                exists = db.query(Terreno).filter(Terreno.name == t_name).first()
                if not exists:
                    new_terreno = Terreno(
                        name=t_name,
                        tags=t_tags,
                        center_lat=t_center_lat,
                        center_lon=t_center_lon,
                        polygon=t_polygon,
                        description=t_description,
                        image_urls=t_image_urls,
                    )
                    db.add(new_terreno)
        db.commit()
        print("Terreni populated from CSV.")

        # --- Prenotazioni Population ---
        prenotazioni_file = os.path.join(seed_dir, "riservazioni_test.csv")
        if os.path.exists(prenotazioni_file):
            print(f"Reading reservations from {prenotazioni_file}...")
            with open(prenotazioni_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                required_cols = {"TerrenoName", "UnitName", "StartTime", "Duration", "Status"}
                if not required_cols.issubset(set(reader.fieldnames or [])):
                    raise ValueError("riservazioni_test.csv is missing required columns.")

                for row_idx, row in enumerate(reader, start=2):
                    t_name = row["TerrenoName"].strip()
                    u_name = row["UnitName"].strip()
                    start_time_str = row["StartTime"].strip()
                    duration_str = row["Duration"].strip()
                    status = row["Status"].strip()

                    try:
                        duration = int(duration_str)
                    except ValueError:
                        raise ValueError(
                            f"riservazioni_test.csv row {row_idx}: Invalid Duration '{duration_str}'"
                        ) from None

                    terreno = db.query(Terreno).filter(Terreno.name == t_name).first()
                    if not terreno:
                        raise ValueError(f"riservazioni_test.csv row {row_idx}: Terreno '{t_name}' not found.")
                    unita = db.query(Unita).filter(Unita.name == u_name).first()
                    if not unita:
                        raise ValueError(f"riservazioni_test.csv row {row_idx}: Unit '{u_name}' not found.")

                    try:
                        start_time = datetime.fromisoformat(start_time_str)
                    except ValueError:
                        raise ValueError(
                            f"riservazioni_test.csv row {row_idx}: Invalid StartTime '{start_time_str}'"
                        ) from None

                    end_time = start_time + timedelta(hours=duration)

                    new_prenotazione = Prenotazione(
                        terreno_id=terreno.id,
                        unita_id=unita.id,
                        start_time=start_time,
                        end_time=end_time,
                        duration=duration,
                        status=status,
                    )
                    db.add(new_prenotazione)
            db.commit()
            print("Reservations populated from CSV.")

        # --- Users Population ---
        if not db.query(User).filter(User.username == "admin").first():
            admin_user = User(username="admin", password_hash=get_password_hash("admin"), role="admin")
            db.add(admin_user)
            print("Admin user created.")

        if not db.query(User).filter(User.username == "prog").first():
            tech_user = User(username="prog", password_hash=get_password_hash("esplo"), role="tech")
            db.add(tech_user)
            print("Tech user created.")

        all_units = db.query(Unita).all()
        for unit in all_units:
            safe_username = "".join(c for c in unit.name if c.isalnum()).lower()
            if not db.query(User).filter(User.username == safe_username).first():
                unit_user = User(
                    username=safe_username, password_hash=get_password_hash("scout"), role="unit", unita_id=unit.id
                )
                db.add(unit_user)
        db.commit()

        # Export Admin DB UI to credentials.txt is no longer needed or we can do it silently

    finally:
        if own_session:
            db.close()


if __name__ == "__main__":
    reset_and_init_db()
