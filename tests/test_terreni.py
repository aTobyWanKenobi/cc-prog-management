from datetime import datetime

from passlib.context import CryptContext

from app.models import Prenotazione, Terreno, Unita, User

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def setup_admin(session):
    hashed = pwd_context.hash("admin")
    admin = User(username="admin", password_hash=hashed, role="admin")
    session.add(admin)
    session.commit()
    return admin


def test_terreno_crud(client, session):
    setup_admin(session)
    client.post("/login", data={"username": "admin", "password": "admin"})

    # Create
    response = client.post(
        "/admin/terreni",
        data={
            "name": "Football Field",
            "tags": "SPORT,GRASS",
            "center_lat": "46.1",
            "center_lon": "9.1",
            "polygon": "[[0,0],[1,1]]",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    t = session.query(Terreno).filter(Terreno.name == "Football Field").first()
    assert t is not None
    assert t.tags == "SPORT,GRASS"

    # Edit
    response = client.post(
        f"/admin/terreni/{t.id}",
        data={
            "name": "Soccer Field",
            "tags": "SPORT",
            "center_lat": "46.2",
            "center_lon": "9.2",
            "polygon": "[[0,0],[2,2]]",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    session.refresh(t)
    assert t.name == "Soccer Field"

    # Delete
    response = client.post(f"/admin/terreni/{t.id}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert session.query(Terreno).filter(Terreno.id == t.id).first() is None


def test_reservation_visibility(client, session):
    # Setup data
    setup_admin(session)
    client.post("/login", data={"username": "admin", "password": "admin"})

    t = Terreno(name="Forest", tags="BOSCO", center_lat="0", center_lon="0", polygon="[]")
    u = Unita(name="Scouts", sottocampo="S")
    session.add(t)
    session.add(u)
    session.commit()

    p = Prenotazione(
        terreno_id=t.id,
        unita_id=u.id,
        start_time=datetime(2025, 7, 10, 10, 0),
        end_time=datetime(2025, 7, 10, 12, 0),
        duration=2,
        status="PENDING",
    )
    session.add(p)
    session.commit()

    # Admin Edit page should show reservations
    response = client.get(f"/admin/terreni/{t.id}")
    assert response.status_code == 200
    assert "Scouts" in response.text
    assert "PENDING" in response.text
