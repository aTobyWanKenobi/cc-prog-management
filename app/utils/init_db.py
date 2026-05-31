import csv
import os
from datetime import datetime, timedelta

from passlib.context import CryptContext

from app.database import Base, SessionLocal, engine
from app.models import (
    Challenge,
    Pattuglia,
    Prenotazione,
    Terreno,
    TerrenoCategoria,
    Unita,
    User,
)

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def get_password_hash(password):
    return pwd_context.hash(password)


def reset_and_init_db(
    db=None,
    seed_unita=True,
    seed_pattuglie=True,
    seed_sfide=True,
    seed_terreni=True,
    seed_prenotazioni=True,
    seed_users=True,
    reset_tables=True,
):
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True

    try:
        # If reset_tables is True, drop and recreate all tables
        if reset_tables:
            print("Dropping all tables...")
            Base.metadata.drop_all(bind=engine)
            print("Creating database tables...")
            Base.metadata.create_all(bind=engine)
            print("Tables created successfully.")

        seed_dir = os.getenv("SEED_DIR", os.path.join("data", "seed"))

        # --- Units Population ---
        if seed_unita:
            if not reset_tables:
                print("Clearing existing units and non-admin users...")
                db.query(User).filter(User.role == "unit").delete()
                db.query(Unita).delete()
                db.commit()

            unita_file = os.path.join(seed_dir, "unita.csv")
            if not os.path.exists(unita_file):
                raise FileNotFoundError(f"Missing required seed file: {unita_file}")

            print(f"Reading units from {unita_file}...")
            with open(unita_file, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                required_cols = {"UnitName", "Tipo", "Sottocampo", "Email"}
                if not required_cols.issubset(set(reader.fieldnames or [])):
                    raise ValueError(f"unita.csv is missing required columns. Found: {reader.fieldnames}")

                for row_idx, row in enumerate(reader, start=2):
                    unit_name = row["UnitName"].strip()
                    tipo = row["Tipo"].strip()
                    sottocampo = row["Sottocampo"].strip()
                    email = row.get("Email", "").strip()
                    short_name = row.get("ShortName", "").strip() or None

                    if not sottocampo:
                        sottocampo = None

                    if not unit_name or not tipo or not email:
                        raise ValueError(f"unita.csv row {row_idx}: UnitName, Tipo, and Email are required.")

                    exists = db.query(Unita).filter(Unita.name == unit_name).first()
                    if not exists:
                        new_unita = Unita(
                            name=unit_name, tipo=tipo, sottocampo=sottocampo, email=email, short_name=short_name
                        )
                        db.add(new_unita)
            db.commit()
            print("Units populated from CSV.")

        # --- Pattuglie Population ---
        if seed_pattuglie:
            if not reset_tables:
                print("Clearing existing pattuglie...")
                db.query(Pattuglia).delete()
                db.commit()

            pattuglie_file = os.path.join(seed_dir, "pattuglie.csv")
            if os.path.exists(pattuglie_file):
                print(f"Reading pattuglie from {pattuglie_file}...")
                with open(pattuglie_file, encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    required_cols = {"PattugliaName", "UnitName", "CapoPattuglia"}
                    if not required_cols.issubset(set(reader.fieldnames or [])):
                        raise ValueError(f"pattuglie.csv is missing required columns. Found: {reader.fieldnames}")

                    for _row_idx, row in enumerate(reader, start=2):
                        p_name = row["PattugliaName"].strip()
                        u_name = row["UnitName"].strip()
                        capo = row["CapoPattuglia"].strip()

                        unita = db.query(Unita).filter(Unita.name == u_name).first()
                        if not unita:
                            print(f"Warning: Unit '{u_name}' not found for pattuglia '{p_name}'. Skipping.")
                            continue

                        exists = db.query(Pattuglia).filter(Pattuglia.name == p_name).first()
                        if not exists:
                            new_patt = Pattuglia(name=p_name, capo_pattuglia=capo, unita_id=unita.id)
                            db.add(new_patt)
                db.commit()
                print("Pattuglie populated from CSV.")

        # --- Sfide Population ---
        if seed_sfide:
            if not reset_tables:
                print("Clearing existing sfide...")
                db.query(Challenge).delete()
                db.commit()

            sfide_file = os.path.join(seed_dir, "sfide.csv")
            if os.path.exists(sfide_file):
                print(f"Reading sfide from {sfide_file}...")
                with open(sfide_file, encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    required_cols = {"Name", "Description", "Points", "IsFungo", "RewardTokens"}
                    if not required_cols.issubset(set(reader.fieldnames or [])):
                        raise ValueError(f"sfide.csv is missing required columns. Found: {reader.fieldnames}")

                    for _row_idx, row in enumerate(reader, start=2):
                        c_name = row["Name"].strip()
                        c_desc = row["Description"].strip()
                        c_points = int(row["Points"].strip())
                        c_isfungo = row["IsFungo"].strip().lower() == "true"
                        c_tokens = int(row["RewardTokens"].strip() or "0")

                        exists = db.query(Challenge).filter(Challenge.name == c_name).first()
                        if not exists:
                            new_challenge = Challenge(
                                name=c_name,
                                description=c_desc,
                                points=c_points,
                                is_fungo=c_isfungo,
                                reward_tokens=c_tokens,
                            )
                            db.add(new_challenge)
                db.commit()
                print("Sfide populated from CSV.")

        # --- Terreni Population ---
        if seed_terreni:
            if not reset_tables:
                print("Clearing existing terreni...")
                db.query(Terreno).delete()
                db.commit()

            terreni_file = os.path.join(seed_dir, "terreni.csv")
            if not os.path.exists(terreni_file):
                raise FileNotFoundError(f"Missing required seed file: {terreni_file}")

            print(f"Reading terreni from {terreni_file}...")
            with open(terreni_file, encoding="utf-8-sig") as f:
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
                    t_tipo_accesso = row.get("TipoAccesso", "entrambi").strip()

                    if not t_name or not t_center_lat or not t_center_lon or not t_polygon:
                        raise ValueError(f"terreni.csv row {row_idx}: Missing required fields.")

                    if t_tags:
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
                            tipo_accesso=t_tipo_accesso.lower(),
                        )
                        db.add(new_terreno)
            db.commit()
            print("Terreni populated from CSV.")

        # --- Prenotazioni Population ---
        if seed_prenotazioni:
            if not reset_tables:
                print("Clearing existing reservations...")
                db.query(Prenotazione).delete()
                db.commit()

            prenotazioni_file = os.path.join(seed_dir, "riservazioni_test.csv")
            if os.path.exists(prenotazioni_file):
                print(f"Reading reservations from {prenotazioni_file}...")
                with open(prenotazioni_file, encoding="utf-8-sig") as f:
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
        if seed_users:
            if not db.query(User).filter(User.username == "prog").first():
                prog_user = User(
                    username="prog",
                    email="programma@bestiale2026.ch",
                    password_hash=get_password_hash("esplo"),
                    role="admin",
                )
                db.add(prog_user)
                print("Admin user 'prog' created.")

            all_units = db.query(Unita).all()
            for unit in all_units:
                safe_username = "".join(c for c in unit.name if c.isalnum()).lower()
                if not db.query(User).filter(User.username == safe_username).first():
                    unit_user = User(
                        username=safe_username,
                        email=unit.email,
                        password_hash=get_password_hash("bestiale"),
                        role="unit",
                        unita_id=unit.id,
                    )
                    db.add(unit_user)
            db.commit()
            print("Users populated.")

    finally:
        if own_session:
            db.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed database from CSV files selectively or entirely.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # Define flags for selective seeding
    parser.add_argument("--unita", action="store_true", help="Seed units table from unita.csv")
    parser.add_argument("--pattuglie", action="store_true", help="Seed patrols table from pattuglie.csv")
    parser.add_argument("--sfide", action="store_true", help="Seed challenges table from sfide.csv")
    parser.add_argument("--terreni", action="store_true", help="Seed terrains table from terreni.csv")
    parser.add_argument(
        "--prenotazioni",
        action="store_true",
        help="Seed reservations table from riservazioni_test.csv",
    )
    parser.add_argument("--users", action="store_true", help="Seed users table")
    parser.add_argument("--reset-tables", action="store_true", help="Drop and recreate all database tables")
    parser.add_argument("--all", action="store_true", help="Seed all tables and perform a full database reset")

    args = parser.parse_args()

    # If --all is passed, or if no selective flags are passed, we reset everything
    selective_flags = [args.unita, args.pattuglie, args.sfide, args.terreni, args.prenotazioni, args.users]
    any_selective = any(selective_flags)

    if args.all or not any_selective:
        # Full reset & seed
        print("=== Database Reset and Full Initialisation ===")
        reset_and_init_db(
            seed_unita=True,
            seed_pattuglie=True,
            seed_sfide=True,
            seed_terreni=True,
            seed_prenotazioni=True,
            seed_users=True,
            reset_tables=True,
        )
    else:
        # Selective seed
        print("=== Selective Database Seeding ===")
        # If they did not pass --reset-tables explicitly, keep tables intact by default
        reset_val = args.reset_tables
        if reset_val:
            print("WARNING: --reset-tables is set. This will drop all tables first!")

        reset_and_init_db(
            seed_unita=args.unita,
            seed_pattuglie=args.pattuglie,
            seed_sfide=args.sfide,
            seed_terreni=args.terreni,
            seed_prenotazioni=args.prenotazioni,
            seed_users=args.users,
            reset_tables=reset_val,
        )
    print("Database initialisation complete.")


if __name__ == "__main__":
    main()
