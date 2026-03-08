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
    client.post("/login", data={"username": "admin", "password": "admin", "login_role": "direzione"})

    # Create with tipo_accesso
    response = client.post(
        "/admin/terreni",
        data={
            "name": "Football Field",
            "tags": "SPORT,BIVACCO",
            "center_lat": "46.1",
            "center_lon": "9.1",
            "polygon": "[[0,0],[1,1]]",
            "tipo_accesso": "reparto",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    t = session.query(Terreno).filter(Terreno.name == "Football Field").first()
    assert t is not None
    assert t.tags == "SPORT,BIVACCO"
    assert t.tipo_accesso == "reparto"

    # Edit with different tipo_accesso
    response = client.post(
        f"/admin/terreni/{t.id}",
        data={
            "name": "Soccer Field",
            "tags": "SPORT",
            "center_lat": "46.2",
            "center_lon": "9.2",
            "polygon": "[[0,0],[2,2]]",
            "tipo_accesso": "entrambi",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    session.refresh(t)
    assert t.name == "Soccer Field"
    assert t.tipo_accesso == "entrambi"

    # Delete
    response = client.post(f"/admin/terreni/{t.id}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert session.query(Terreno).filter(Terreno.id == t.id).first() is None


def test_gestione_terreni_filtering_staff(client, session):
    from app.models import Unita, User

    MOCK_HASH = "$argon2id$v=19$m=65536,t=3,p=4$uDcGYOwdwzgHAIDwHmNMaQ$Zz9Nrb26WqJFip1NhJwp6ndqBVMgh15zjAUUHsJXNYU"
    tech = User(username="tech", password_hash=MOCK_HASH, role="tech")
    session.add(tech)

    # Setup Unita
    u1 = Unita(name="Reparto Test", tipo="reparto")
    session.add(u1)
    session.commit()

    # Setup Terreni
    t1 = Terreno(name="t1", tags="", center_lat="0", center_lon="0", polygon="[]")
    t2 = Terreno(name="t2", tags="", center_lat="0", center_lon="0", polygon="[]")
    session.add(t1)
    session.add(t2)
    session.commit()

    # Setup reservations
    r1 = Prenotazione(
        unita_id=u1.id,
        terreno_id=t1.id,
        start_time=datetime.now(),
        end_time=datetime.now(),
        status="PENDING",
        duration=1,
    )
    r2 = Prenotazione(
        unita_id=u1.id,
        terreno_id=t2.id,
        start_time=datetime.now(),
        end_time=datetime.now(),
        status="APPROVED",
        duration=1,
    )
    session.add(r1)
    session.add(r2)
    session.commit()

    # Login as tech
    client.post("/login", data={"username": "tech", "password": "god", "login_role": "staff"})

    # Get all terrains
    response = client.get("/gestione-terreni")
    assert response.status_code == 200
    # Both active should be found conceptually
    assert "t1" in response.text
    assert "t2" in response.text

    # Filter by t1
    response_filtered = client.get(f"/gestione-terreni?terreno_id={t1.id}")
    assert response_filtered.status_code == 200


def test_reservation_visibility(client, session):
    # Setup data
    setup_admin(session)
    client.post("/login", data={"username": "admin", "password": "admin", "login_role": "direzione"})

    t = Terreno(name="Forest", tags="BIVACCO", center_lat="0", center_lon="0", polygon="[]")
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
