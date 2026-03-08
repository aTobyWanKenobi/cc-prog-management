import os
import shutil
from datetime import datetime

import openpyxl
from sqlalchemy.orm import Session

from app.database import SQLALCHEMY_DATABASE_URL, SessionLocal
from app.models import Pattuglia, Prenotazione

BACKUP_DIR = os.getenv("BACKUP_DIR", "data/backups")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")

# Ensure backup dir exists
os.makedirs(BACKUP_DIR, exist_ok=True)


def generate_excel_sfide(db: Session, filepath: str):
    wb = openpyxl.Workbook()
    ws = wb.active
    if not ws:
        ws = wb.create_sheet()
    ws.title = "Sfide e Punteggi"

    # Header
    ws.append(["Unita", "Pattuglia", "Punteggio Attuale", "Capo Pattuglia"])

    pattuglie = db.query(Pattuglia).all()
    for p in pattuglie:
        ws.append([p.unita.name if p.unita else "N/A", p.name, p.current_score, p.capo_pattuglia])

    wb.save(filepath)


def generate_excel_riservazioni(db: Session, filepath: str):
    wb = openpyxl.Workbook()
    ws = wb.active
    if not ws:
        ws = wb.create_sheet()
    ws.title = "Riservazioni Terreni"

    # Header
    ws.append(["Terreno", "Unita", "Inizio", "Fine", "Durata (h)", "Stato", "Note"])

    prenotazioni = db.query(Prenotazione).all()
    for p in prenotazioni:
        terreno_name = p.terreno.name if p.terreno else "N/A"
        unita_name = p.unita.name if p.unita else "N/A"
        start = p.start_time.strftime("%Y-%m-%d %H:%M") if p.start_time else ""
        end = p.end_time.strftime("%Y-%m-%d %H:%M") if p.end_time else ""

        ws.append([terreno_name, unita_name, start, end, p.duration, p.status, p.notes or ""])

    wb.save(filepath)


def push_to_google_drive(filepath: str):
    """
    Placeholder for Google Drive integration.
    Logs the action or interacts with Google Drive API if configured.
    """
    if not GOOGLE_DRIVE_FOLDER_ID:
        print(f"Skipping Google Drive push for {filepath} (no folder ID configured)")
        return False
    print(f"Simulating push of {filepath} to Google Drive folder {GOOGLE_DRIVE_FOLDER_ID}")
    return True


def execute_backup() -> tuple[bool, str]:
    """
    Executes the full backup process:
    1. Copies DB
    2. Generates Excels
    3. Pushes to Google Drive
    Returns (Success, message)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "")

    try:
        # 1. DB Copy
        backup_db_path = os.path.join(BACKUP_DIR, f"{timestamp}_backup_db.sqlite")
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_db_path)
            push_to_google_drive(backup_db_path)

        # 2. Excels
        db = SessionLocal()
        try:
            sfide_path = os.path.join(BACKUP_DIR, f"{timestamp}_sfide_e_punteggi.xlsx")
            generate_excel_sfide(db, sfide_path)
            push_to_google_drive(sfide_path)

            riserv_path = os.path.join(BACKUP_DIR, f"{timestamp}_riservazioni_terreni.xlsx")
            generate_excel_riservazioni(db, riserv_path)
            push_to_google_drive(riserv_path)
        finally:
            db.close()

        return True, "Backup completato con successo"
    except Exception as e:
        print(f"Backup failed: {e}")
        return False, f"Errore durante il backup: {str(e)}"
