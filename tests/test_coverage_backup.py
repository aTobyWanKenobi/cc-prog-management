import os
from datetime import datetime
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from app.models import Pattuglia, Prenotazione, Terreno, Unita
from app.services.backup_service import (
    execute_backup,
    generate_excel_riservazioni,
    generate_excel_sfide,
)


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
    dummy_db = tmp_path / "test.db"
    dummy_db.write_text("dummy database content")
    monkeypatch.setattr("app.services.backup_service.BACKUP_DIR", str(tmp_path))
    monkeypatch.setattr("app.services.backup_service.SQLALCHEMY_DATABASE_URL", f"sqlite:///{dummy_db}")

    mock_db = MagicMock()
    mock_session_local.return_value = mock_db

    # Test success
    success, msg, zip_path = execute_backup()
    assert success is True
    assert zip_path is not None
    assert os.path.exists(zip_path)

    # Test error
    mock_session_local.side_effect = Exception("Test Error")
    success, msg, zip_path = execute_backup()
    assert success is False
    assert "Errore" in msg


def test_cleanup_old_backups(tmp_path):
    from app.services.backup_service import cleanup_old_backups

    # 1. Non-existent directory
    cleanup_old_backups(str(tmp_path / "non_existent_dir"))

    # 2. Delete oldest backups (rolling window)
    # Let's create 12 backup runs (each having a sqlite and 2 excel files)
    for i in range(12):
        timestamp = f"20260604_{1000 + i}"
        for suffix in ["backup_db.sqlite", "sfide_e_punteggi.xlsx", "riservazioni_terreni.xlsx", "backup.zip"]:
            file_path = tmp_path / f"{timestamp}_{suffix}"
            file_path.write_text("content")

    cleanup_old_backups(str(tmp_path), max_backups=10)

    # Check that only the 10 newest runs remain
    for suffix in ["backup_db.sqlite", "sfide_e_punteggi.xlsx", "riservazioni_terreni.xlsx", "backup.zip"]:
        assert not os.path.exists(tmp_path / f"20260604_1000_{suffix}")
        assert not os.path.exists(tmp_path / f"20260604_1001_{suffix}")
        assert os.path.exists(tmp_path / f"20260604_1002_{suffix}")
        assert os.path.exists(tmp_path / f"20260604_1011_{suffix}")

    # 3. Exception in os.remove
    timestamp = "20260604_0900"
    file_path = tmp_path / f"{timestamp}_backup.zip"
    file_path.write_text("content")

    with patch("os.remove", side_effect=Exception("Failed to delete")):
        cleanup_old_backups(str(tmp_path), max_backups=10)

    # 4. Exception in listing
    with patch("os.listdir", side_effect=Exception("Failed to list")):
        cleanup_old_backups(str(tmp_path))
