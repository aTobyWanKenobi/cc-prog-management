from app.database import engine, Base, SessionLocal
from app.models import Unita, Pattuglia, Challenge, Completion, User
from passlib.context import CryptContext
from datetime import datetime

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

    db = SessionLocal()
    
    # --- Units Population from CSV ---
    import csv
    import os

    if os.path.exists("units.csv"):
        print("Reading units from units.csv...")
        with open("units.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                unit_name = row["UnitName"]
                sottocampo = row["Sottocampo"]
                
                exists = db.query(Unita).filter(Unita.name == unit_name).first()
                if not exists:
                    new_unita = Unita(name=unit_name, sottocampo=sottocampo)
                    db.add(new_unita)
        db.commit()
        print("Units populated from CSV.")
    else:
        print("units.csv not found, skipping unit population.")

    # --- Pattuglie Population from CSV ---
    if os.path.exists("pattuglie.csv"):
        print("Reading pattuglie from pattuglie.csv...")
        with open("pattuglie.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                p_name = row["Name"]
                p_capo = row["CapoPattuglia"]
                unit_name = row["UnitName"]
                
                # Find unit
                unit = db.query(Unita).filter(Unita.name == unit_name).first()
                if unit:
                    exists = db.query(Pattuglia).filter(Pattuglia.name == p_name).first()
                    if not exists:
                        new_pattuglia = Pattuglia(
                            name=p_name, 
                            capo_pattuglia=p_capo, 
                            unita_id=unit.id,
                            current_score=0
                        )
                        db.add(new_pattuglia)
                else:
                    print(f"Warning: Unit '{unit_name}' not found for pattuglia '{p_name}'")
        db.commit()
        print("Pattuglie populated from CSV.")
    else:
        print("pattuglie.csv not found, skipping pattuglie population.")

    # --- Challenges Population from CSV ---
    if os.path.exists("challenges.csv"):
        print("Reading challenges from challenges.csv...")
        with open("challenges.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                c_name = row["Name"]
                c_desc = row["Description"]
                c_points = int(row["Points"])
                c_tokens = int(row["RewardTokens"])
                c_fungo = row["IsFungo"].lower() == 'true'
                
                exists = db.query(Challenge).filter(Challenge.name == c_name).first()
                if not exists:
                    new_challenge = Challenge(
                        name=c_name,
                        description=c_desc,
                        points=c_points,
                        reward_tokens=c_tokens,
                        is_fungo=c_fungo
                    )
                    db.add(new_challenge)
        db.commit()
        print("Challenges populated from CSV.")
    else:
        print("challenges.csv not found, skipping challenges population.")

    # --- Completions Population from CSV ---
    if os.path.exists("completions.csv"):
        print("Reading completions from completions.csv...")
        with open("completions.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                p_name = row["PattugliaName"]
                c_name = row["ChallengeName"]
                timestamp_str = row["Timestamp"]
                
                pattuglia = db.query(Pattuglia).filter(Pattuglia.name == p_name).first()
                challenge = db.query(Challenge).filter(Challenge.name == c_name).first()
                
                if pattuglia and challenge:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    
                    # Check if already exists (optional, but good for idempotency if running multiple times without drop)
                    # Since we drop tables in reset_db, we can just add.
                    new_completion = Completion(
                        pattuglia_id=pattuglia.id,
                        challenge_id=challenge.id,
                        timestamp=timestamp
                    )
                    db.add(new_completion)
                    
                    # Update score
                    pattuglia.current_score += challenge.points
                else:
                    print(f"Warning: Pattuglia '{p_name}' or Challenge '{c_name}' not found.")
        db.commit()
        print("Completions populated from CSV.")
    else:
        print("completions.csv not found, skipping completions population.")

    # --- Users Population ---
    # 1. Admin
    if not db.query(User).filter(User.username == "admin").first():
        admin_user = User(
            username="admin",
            password_hash=get_password_hash("admin"),
            role="admin"
        )
        db.add(admin_user)
        print("Admin user created.")

    # 2. Tech (Superuser)
    if not db.query(User).filter(User.username == "prog").first():
        tech_user = User(
            username="prog",
            password_hash=get_password_hash("esplo"),
            role="tech"
        )
        db.add(tech_user)
        print("Tech user created.")

    # 3. Unit Users
    # Create a user for each unit. Username = simplified name (lowercase, no spaces/special chars)
    all_units = db.query(Unita).all()
    for unit in all_units:
        # Simple username generation
        safe_username = "".join(c for c in unit.name if c.isalnum()).lower()
        
        if not db.query(User).filter(User.username == safe_username).first():
            unit_user = User(
                username=safe_username,
                password_hash=get_password_hash("scout"),
                role="unit",
                unita_id=unit.id
            )
            db.add(unit_user)
            print(f"User created for unit: {unit.name} ({safe_username})")

    # --- Credentials Export ---
    db.commit() # Ensure all users are committed before querying
    credentials = []
    credentials.append("--- CREDENZIALI DI ACCESSO ---")
    credentials.append("")
    credentials.append("ADMIN (Accesso completo):")
    credentials.append("Username: admin")
    credentials.append("Password: admin")
    credentials.append("")
    credentials.append("TECNICO (Inserimento Punti + Gestione Terreni):")
    credentials.append("Username: prog")
    credentials.append("Password: esplo")
    credentials.append("")
    credentials.append("UNITA (Classifica + Prenotazioni):")
    
    # Re-query to get all users including newly created ones
    all_unit_users = db.query(User).filter(User.role == 'unit').all()
    for u in all_unit_users:
        # We know the default password is 'scout'
        credentials.append(f"Unità: {u.unita.name}")
        credentials.append(f"Username: {u.username}")
        credentials.append(f"Password: scout")
        credentials.append("-" * 20)

    with open("credentials.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(credentials))
    
    print("Credentials exported to credentials.txt")

    db.commit()
    db.close()

if __name__ == "__main__":
    init_db()
