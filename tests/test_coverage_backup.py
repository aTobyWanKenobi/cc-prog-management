import os
from datetime import datetime
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from app.models import Pattuglia, Prenotazione, Terreno, Unita
from app.services.backup_service import (
    execute_backup,
    generate_excel_riservazioni,
    generate_excel_sfide,
    push_to_google_drive,
)


def test_push_to_google_drive(monkeypatch):
    monkeypatch.setattr("app.services.backup_service.GOOGLE_DRIVE_FOLDER_ID", "")
    assert push_to_google_drive("test") is False

    monkeypatch.setattr("app.services.backup_service.GOOGLE_DRIVE_FOLDER_ID", "123")
    assert push_to_google_drive("test") is True


def test_generate_excel_sfide(session: Session, tmp_path):
    u = Unita(name="Test Unita")
    p = Pattuglia(name="Lupi", unita=u, current_score=0, capo_pattuglia="Alice")
    session.add(u)
    session.add(p)
    # Test without unit for the N/A branch
    p2 = Pattuglia(name="Volpi", unita=u, current_score=10, capo_pattuglia="Bob")
    session.add(p2)
    session.commit()
    file_path = str(tmp_path / "sfide.xlsx")
    generate_excel_sfide(session, file_path)
    assert os.path.exists(file_path)


def test_generate_excel_riservazioni(session: Session, tmp_path):
    t = Terreno(name="Test", tags="SPORT", center_lat=46.0, center_lon=9.0, polygon="[]")
    session.add(t)
    u = Unita(name="Test Unita")
    session.add(u)
    session.commit()

    p = Prenotazione(
        unita=u, terreno=t, duration=2, status="PENDING", start_time=datetime.now(), end_time=datetime.now()
    )
    p2 = Prenotazione(
        unita=u, terreno=t, duration=1, status="APPROVED", start_time=datetime.now(), end_time=datetime.now()
    )  # Test edge cases
    session.add(p)
    session.add(p2)
    session.commit()
    file_path = str(tmp_path / "riservazioni.xlsx")
    generate_excel_riservazioni(session, file_path)
    assert os.path.exists(file_path)


@patch("app.services.backup_service.SessionLocal")
def test_execute_backup(mock_session_local, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.backup_service.BACKUP_DIR", str(tmp_path))
    monkeypatch.setattr("app.services.backup_service.SQLALCHEMY_DATABASE_URL", "sqlite:///test.db")

    mock_db = MagicMock()
    mock_session_local.return_value = mock_db

    # Test success
    success, msg = execute_backup()
    assert success is True

    # Test error
    mock_session_local.side_effect = Exception("Test Error")
    success, msg = execute_backup()
    assert success is False
    assert "Errore" in msg
