from datetime import datetime, timedelta

from app.models import Challenge, Completion, Pattuglia, Prenotazione, Terreno, Unita, User


def test_admin_remaining_endpoints(client, session):
    # Setup
    admin = User(
        username="admin_endpoint",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$uDcGYOwdwzgHAIDwHmNMaQ$Zz9Nrb26WqJFip1NhJwp6ndqBVMgh15zjAUUHsJXNYU",
        role="admin",
    )
    u = Unita(name="Lupi Endpoint", tipo="Reparto")
    patt = Pattuglia(name="Pattuglia Endpoint", capo_pattuglia="Test", unita=u)
    c = Challenge(name="Test Challenge", description="C", points=10)
    session.add_all([admin, u, patt, c])
    session.commit()
    t = Terreno(name="Terreno Endpoint", tags="SPORT", center_lat=46.0, center_lon=9.0, polygon="[]")
    session.add(t)
    session.commit()
    p = Prenotazione(
        unita=u,
        terreno=t,
        duration=2,
        status="PENDING",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=2),
    )
    session.add(p)
    comp = Completion(pattuglia_id=patt.id, challenge_id=c.id)
    session.add(comp)
    session.commit()

    # Login
    client.post("/login", data={"username": "admin_endpoint", "password": "god", "login_role": "direzione"})

    # Hit missing admin endpoints
    client.post("/reset-db", follow_redirects=False)
    client.post("/backup", follow_redirects=False)
    # Don't hit restore, it expects a file upload and fails otherwise. Or we hit it with no file to get 400?
    client.post("/restore", follow_redirects=False)

    client.get(f"/pattuglie/{patt.id}")
    client.get(f"/challenges/{c.id}")

    # Terreni
    client.post(
        "/terreni",
        data={
            "name": "New Terrain",
            "tags": "SPORT",
            "center_lat": 46.0,
            "center_lon": 9.0,
            "polygon": "[]",
            "desc": "",
        },
        follow_redirects=False,
    )
    client.get(f"/terreni/{t.id}")
    client.post(
        f"/terreni/{t.id}",
        data={"name": "Updated Terrain", "tags": "BIVACCO", "tipo_accesso": "entrambi"},
        follow_redirects=False,
    )

    # Delete prenotazione
    client.post(f"/prenotazioni/{p.id}/delete", follow_redirects=False)

    # Rollback
    client.post(f"/rollback/{comp.id}", follow_redirects=False)


def test_public_remaining_endpoints(client, session):
    tech = User(
        username="tech_endpoint",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$uDcGYOwdwzgHAIDwHmNMaQ$Zz9Nrb26WqJFip1NhJwp6ndqBVMgh15zjAUUHsJXNYU",
        role="tech",
    )
    u = Unita(name="Lupi Public", tipo="Reparto")
    patt = Pattuglia(name="Pattuglia Public", capo_pattuglia="Test", unita=u)
    c = Challenge(name="Test Challenge 2", description="C", points=10)
    session.add_all([tech, u, patt, c])
    session.commit()
    t = Terreno(name="Terreno Public", tags="SPORT", center_lat=46.0, center_lon=9.0, polygon="[]")
    session.add(t)
    session.commit()
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

    # Not logged in hits
    client.get("/")
    client.get("/timeline")

    # Login
    client.post("/login", data={"username": "tech_endpoint", "password": "god", "login_role": "staff"})

    client.get("/")
    client.get("/prenotazioni")

    # Hit missing public POST endpoints
    client.post(f"/prenotazioni/cancel/{p.id}", follow_redirects=False)

    # Create prenotazione form
    client.post(
        "/prenotazioni",
        data={
            "unita_id": str(u.id),
            "terreno_id": str(t.id),
            "start_time": datetime.now().strftime("%Y-%m-%dT%H:%M"),
            "end_time": (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"),
            "notes": "test",
        },
        follow_redirects=False,
    )
    client.post(
        "/prenotazioni",
        data={"unita_id": "invalid", "terreno_id": str(t.id), "start_time": "", "end_time": ""},
        follow_redirects=False,
    )  # Validation branch

    client.post(f"/prenotazioni/update-notes/{p.id}", data={"notes": "new note"}, follow_redirects=False)

    # Complete
    client.post("/complete", data={"pattuglia_id": str(patt.id), "challenge_id": str(c.id)}, follow_redirects=False)

    # Manual
    client.post(
        "/manual-adjustment",
        data={"pattuglia_id": str(patt.id), "points": "10", "reason": "bonus"},
        follow_redirects=False,
    )

    client.get("/timeline")

    client.get("/export/ranking", follow_redirects=False)
    client.post("/supporto", data={"subject": "Help", "message": "Help me!"}, follow_redirects=False)

    # API
    start = datetime.now().isoformat()
    end = (datetime.now() + timedelta(days=1)).isoformat()
    client.get(f"/api/terreni/availability?start={start}&end={end}&duration=2")
