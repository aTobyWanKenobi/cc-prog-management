from app.models import User, Unita, Pattuglia, Challenge, Completion
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def setup_admin_and_data(session):
    # Admin
    admin = User(username="admin", password_hash=pwd_context.hash("admin"), role="admin")
    session.add(admin)
    
    # Unit
    unit = Unita(name="Test Unit", sottocampo="Nord")
    session.add(unit)
    session.commit()
    
    return admin, unit

def test_pattuglia_crud(client, session):
    admin, unit = setup_admin_and_data(session)
    client.post("/login", data={"username": "admin", "password": "admin"})
    
    # Create
    response = client.post(
        "/admin/pattuglie",
        data={"name": "Foxes", "capo_pattuglia": "Alice", "unita_id": str(unit.id)},
        follow_redirects=False
    )
    assert response.status_code == 303
    
    p = session.query(Pattuglia).filter(Pattuglia.name == "Foxes").first()
    assert p is not None
    assert p.unita_id == unit.id
    
    # Edit
    response = client.post(
        f"/admin/pattuglie/{p.id}/edit",
        data={"name": "Super Foxes", "capo_pattuglia": "Bob", "unita_id": str(unit.id)},
        follow_redirects=False
    )
    assert response.status_code == 303
    session.refresh(p)
    assert p.name == "Super Foxes"
    assert p.capo_pattuglia == "Bob"
    
    # Delete
    response = client.post(f"/admin/pattuglie/{p.id}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert session.query(Pattuglia).filter(Pattuglia.id == p.id).first() is None

def test_score_recalculation(client, session):
    admin, unit = setup_admin_and_data(session)
    client.post("/login", data={"username": "admin", "password": "admin"})
    
    # Setup: Pattuglia + Challenge + Completion
    p = Pattuglia(name="Lions", capo_pattuglia="Simba", unita_id=unit.id, current_score=10)
    c = Challenge(name="Roar", description="Loud", points=10, reward_tokens=0)
    session.add(p)
    session.add(c)
    session.commit()
    
    comp = Completion(pattuglia_id=p.id, challenge_id=c.id)
    session.add(comp)
    session.commit()
    
    # Edit Challenge point value WITHOUT retroactive
    client.post(
        f"/admin/challenges/{c.id}/edit",
        data={
            "name": "Roar", 
            "description": "Loud", 
            "points": "20", # Changed from 10 to 20
            "reward_tokens": "0",
            "is_fungo": False,
            "retroactive_update": False 
        },
        follow_redirects=False
    )
    session.refresh(p)
    assert p.current_score == 10 # Should NOT change
    
    # Edit Challenge point value WITH retroactive
    client.post(
        f"/admin/challenges/{c.id}/edit",
        data={
            "name": "Roar", 
            "description": "Loud", 
            "points": "50", # Changed from 20 to 50 (Diff +30 vs old value in DB)
            # Wait, logic compares input vs DB old value.
            # DB has 20 now. Input 50. Diff +30.
            "reward_tokens": "0",
            "is_fungo": False,
            "retroactive_update": True 
        },
        follow_redirects=False
    )
    session.refresh(p)
    # Original score 10. 
    # Logic: diff = 50 - 20 = 30.
    # Count = 1 completion.
    # New score = 10 + 30 = 40.
    assert p.current_score == 40
