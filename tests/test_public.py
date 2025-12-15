from app.models import User, Unita, Pattuglia, Challenge, Completion
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def setup_tech_user(session):
    hashed = pwd_context.hash("tech")
    user = User(username="prog", password_hash=hashed, role="tech")
    session.add(user)
    session.commit()
    return user

def setup_basic_game_data(session):
    u = Unita(name="U1", sottocampo="S1")
    session.add(u)
    session.commit()
    
    p = Pattuglia(name="P1", capo_pattuglia="C1", unita_id=u.id, current_score=0)
    c = Challenge(name="C1", description="D1", points=100)
    session.add(p)
    session.add(c)
    session.commit()
    return p, c

def test_ranking_page_access(client, session):
    # Public page, but needs auth? 
    # router dependency: get_authenticated_user.
    # So anonymous should strictly fail 401, which redirects to login (200).
    response = client.get("/")
    assert response.status_code == 200
    assert "Login" in response.text or "password" in response.text
    
    # Auth user
    setup_tech_user(session)
    client.post("/login", data={"username": "prog", "password": "tech"})
    response = client.get("/")
    assert response.status_code == 200

def test_complete_challenge_flow(client, session):
    setup_tech_user(session)
    client.post("/login", data={"username": "prog", "password": "tech"})
    p, c = setup_basic_game_data(session)
    
    # 1. Complete
    response = client.post(
        "/complete",
        data={"pattuglia_id": str(p.id), "challenge_id": str(c.id)},
        follow_redirects=False
    )
    assert response.status_code == 303
    
    session.refresh(p)
    assert p.current_score == 100
    assert session.query(Completion).count() == 1
    
    # 2. Duplicate Check
    response = client.post(
        "/complete",
        data={"pattuglia_id": str(p.id), "challenge_id": str(c.id)},
        follow_redirects=False
    )
    # Expect redirect to error
    assert response.status_code == 303
    assert "error=already_completed" in response.headers["location"]
    
    session.refresh(p)
    assert p.current_score == 100 # No change

def test_ranking_order(client, session):
    setup_tech_user(session)
    client.post("/login", data={"username": "prog", "password": "tech"})
    
    u = Unita(name="U1", sottocampo="S1")
    session.add(u)
    session.commit()
    
    p1 = Pattuglia(name="Low", capo_pattuglia="L", unita_id=u.id, current_score=10)
    p2 = Pattuglia(name="High", capo_pattuglia="H", unita_id=u.id, current_score=50)
    session.add(p1)
    session.add(p2)
    session.commit()
    
    response = client.get("/")
    # Check that High comes before Low in HTML
    content = response.text
    idx_high = content.find("High")
    idx_low = content.find("Low")
    assert idx_high < idx_low

def test_export_ranking_permission(client, session):
    # Tech can export
    setup_tech_user(session)
    client.post("/login", data={"username": "prog", "password": "tech"})
    response = client.get("/export/ranking")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    
    # Unit user cannot export
    hashed = pwd_context.hash("unit")
    # Must ensure unique username from other tests if DB not cleared? 
    # Fixture clears DB, so 'unituser' is fine.
    u_user = User(username="unituser", password_hash=hashed, role="unit")
    session.add(u_user)
    session.commit()
    
    resp = client.post(
        "/login", 
        data={"username": "unituser", "password": "unit"},
        follow_redirects=False
    )
    assert resp.status_code == 303 # Ensure login worked
    
    response = client.get("/export/ranking")
    assert response.status_code == 403

def test_other_public_pages(client, session):
    # Setup tech user for input pages
    setup_tech_user(session)
    client.post("/login", data={"username": "prog", "password": "tech"})
    
    # Prenotazioni
    response = client.get("/prenotazioni")
    assert response.status_code == 200
    
    # Input
    response = client.get("/input")
    assert response.status_code == 200
    
    # Gestione Terreni
    response = client.get("/gestione-terreni")
    assert response.status_code == 200
    
    # Timeline
    response = client.get("/timeline")
    assert response.status_code == 200

def test_ranking_filter(client, session):
    setup_tech_user(session)
    client.post("/login", data={"username": "prog", "password": "tech"})
    
    u1 = Unita(name="U_Filter1", sottocampo="Nord")
    u2 = Unita(name="U_Filter2", sottocampo="Sud")
    session.add_all([u1, u2])
    session.commit()
    
    p1 = Pattuglia(name="P_Filter1", capo_pattuglia="C1", unita_id=u1.id)
    p2 = Pattuglia(name="P_Filter2", capo_pattuglia="C2", unita_id=u2.id)
    session.add_all([p1, p2])
    session.commit()
    
    # Filter Nord
    response = client.get("/?sottocampo_filter=Nord")
    assert response.status_code == 200
    assert "P_Filter1" in response.text
    assert "P_Filter2" not in response.text
    
    # Filter Sud
    response = client.get("/?sottocampo_filter=Sud")
    assert response.status_code == 200
    assert "P_Filter2" in response.text
    assert "P_Filter1" not in response.text
