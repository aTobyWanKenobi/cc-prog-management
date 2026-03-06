from passlib.context import CryptContext

from app.models import Unita, User

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def setup_user(session, role="unit"):
    u = Unita(name="Test Unit", tipo="Reparto", email="testunit@bestiale2026.ch")
    session.add(u)
    session.commit()
    hashed = pwd_context.hash("password")
    user = User(username="testuser", password_hash=hashed, role=role, unita_id=u.id, email="testuser@bestiale2026.ch")
    session.add(user)
    session.commit()
    return user


def test_get_support_page_unauthenticated(client):
    response = client.get("/supporto", follow_redirects=False)
    assert response.status_code in [303, 307]


def test_get_support_page_authenticated(client, session):
    setup_user(session)
    client.post("/login", data={"username": "testuser", "password": "password", "login_role": "unit"})
    response = client.get("/supporto")
    assert response.status_code == 200
    assert "Contatta il Supporto" in response.text


def test_post_support_ticket(client, session):
    setup_user(session)
    client.post("/login", data={"username": "testuser", "password": "password", "login_role": "unit"})
    response = client.post(
        "/supporto", data={"subject": "Aiuto prenota", "message": "Non riesco a prenotare un terreno."}
    )
    assert response.status_code == 200
    assert "inviata con successo" in response.text
