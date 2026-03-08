from datetime import datetime, timedelta

from app.email_service import (
    send_reservation_approved_email,
    send_reservation_rejected_email,
    send_reservation_requested_email,
    send_support_email,
)
from app.models import Prenotazione, Terreno, Unita, User


def test_approve_overlap_resolution(client, session):
    # Setup Admin
    MOCK_HASH = "$argon2id$v=19$m=65536,t=3,p=4$uDcGYOwdwzgHAIDwHmNMaQ$Zz9Nrb26WqJFip1NhJwp6ndqBVMgh15zjAUUHsJXNYU"
    admin = User(username="admin_user_overlap", password_hash=MOCK_HASH, role="admin", email="admin@test.com")
    session.add(admin)

    # Setup Terreno and Unitas
    t = Terreno(name="Campo Base", tags="SPORT", center_lat=46.0, center_lon=9.0, polygon="[]")
    u1 = Unita(name="Lupi", email="lupi@test.com", tipo="Reparto")
    u2 = Unita(name="Volpi", email="volpi@test.com", tipo="Reparto")
    u3 = Unita(name="Orsi", email="orsi@test.com", tipo="Reparto")
    session.add_all([t, u1, u2, u3])
    session.commit()

    # Create 3 overlapping reservations
    now = datetime.now()
    p1 = Prenotazione(
        unita=u1, terreno=t, duration=2, status="PENDING", start_time=now, end_time=now + timedelta(hours=2)
    )
    p2 = Prenotazione(
        unita=u2,
        terreno=t,
        duration=2,
        status="PENDING",
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=3),
    )
    p3 = Prenotazione(
        unita=u3,
        terreno=t,
        duration=2,
        status="PENDING",
        start_time=now + timedelta(hours=3),
        end_time=now + timedelta(hours=5),
    )  # Not overlapping p1
    session.add_all([p1, p2, p3])
    session.commit()

    # Login Admin
    client.post("/login", data={"username": "admin_user_overlap", "password": "god", "login_role": "direzione"})

    # Approve p1
    res = client.post(f"/gestione-terreni/approve/{p1.id}", follow_redirects=False)
    assert res.status_code == 303

    # Check states
    session.refresh(p1)
    session.refresh(p2)
    session.refresh(p3)

    assert p1.status == "APPROVED"
    assert p2.status == "REJECTED"  # Overlapped with p1
    assert p3.status == "PENDING"  # Did not overlap with p1


def test_reject_prenotazione(client, session):
    # Setup
    MOCK_HASH = "$argon2id$v=19$m=65536,t=3,p=4$uDcGYOwdwzgHAIDwHmNMaQ$Zz9Nrb26WqJFip1NhJwp6ndqBVMgh15zjAUUHsJXNYU"
    admin = User(username="admin_reject", password_hash=MOCK_HASH, role="admin", email="admin@test.com")
    t = Terreno(name="Campo 2", tags="SPORT", center_lat=46.0, center_lon=9.0, polygon="[]")
    u = Unita(name="Lupi 2", email="lupi@test.com", tipo="Reparto")
    session.add_all([admin, t, u])

    p = Prenotazione(
        unita=u,
        terreno=t,
        duration=2,
        status="PENDING",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=2),
    )
    session.add(p)
    session.commit()

    client.post("/login", data={"username": "admin_reject", "password": "god", "login_role": "direzione"})
    res = client.post(f"/gestione-terreni/reject/{p.id}", follow_redirects=False)
    assert res.status_code == 303

    session.refresh(p)
    assert p.status == "REJECTED"


def test_email_service_functions(monkeypatch):
    # Just call them to cover the branch where emails are sent or logged
    monkeypatch.setenv("SENDGRID_API_KEY", "")  # Fallback to logging

    send_reservation_requested_email("test@test.com", "Lupi", "Base", "2026", "2026")
    send_reservation_approved_email("test@test.com", "Lupi", "Base", "2026", "2026")
    send_reservation_rejected_email("test@test.com", "Lupi", "Base", "2026", "2026")
    send_reservation_requested_email(None, "Lupi", "Base", "2026", "2026")
    send_reservation_approved_email(None, "Lupi", "Base", "2026", "2026")
    send_reservation_rejected_email(None, "Lupi", "Base", "2026", "2026")
    send_support_email("test@test.com", "Name", "Subject", "Message", "unit")

    # We will exclude sendgrid API tests here to avoid complexity.
