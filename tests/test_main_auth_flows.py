from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from app.models import User

MOCK_HASH = "$argon2id$v=19$m=65536,t=3,p=4$uDcGYOwdwzgHAIDwHmNMaQ$Zz9Nrb26WqJFip1NhJwp6ndqBVMgh15zjAUUHsJXNYU"


def test_login_role_validation(client, session):
    # Create tech user
    tech_user = User(username="tech_guy", password_hash=MOCK_HASH, role="tech")
    session.add(tech_user)
    session.commit()

    # Try to login as unit but role is tech -> fail
    response = client.post("/login", data={"username": "tech_guy", "password": "god", "login_role": "reparto"})
    assert response.status_code == 200
    assert "un Reparto Esploratori" in response.text

    # Try to login as direzione but role is tech -> fail
    response = client.post("/login", data={"username": "tech_guy", "password": "god", "login_role": "direzione"})
    assert response.status_code == 200
    assert "Non sei autorizzato" in response.text

    # Try to login as tech -> auth success and redirect
    response = client.post(
        "/login", data={"username": "tech_guy", "password": "god", "login_role": "staff"}, follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/gestione-terreni"


@patch("app.main.send_password_reset_email")
def test_password_reset_request(mock_send_email, client, session):
    user = User(username="forgot_pw", email="forgot@example.com", role="unit", password_hash=MOCK_HASH)
    session.add(user)
    session.commit()

    response = client.post("/password-reset-request", data={"email": "forgot@example.com"}, follow_redirects=True)
    assert response.status_code == 200
    assert "un link per reimpostare" in response.text

    mock_send_email.assert_called_once()

    # Verify token generated in db
    session.refresh(user)
    assert user.reset_token is not None
    assert user.reset_token_expires_at is not None


def test_password_reset_confirm(client, session):
    user = User(
        username="reset_me",
        role="unit",
        password_hash=MOCK_HASH,
        reset_token="valid_token",
        reset_token_expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1),
    )
    session.add(user)
    session.commit()

    # Access reset page
    response = client.get("/reset-password?token=valid_token")
    assert response.status_code == 200
    assert "Nuova Password" in response.text

    # Submit new password
    response = client.post("/reset-password-confirm", data={"token": "valid_token", "new_password": "new_secure_pw"})
    assert response.status_code == 200
    assert "aggiornata con successo" in response.text

    # Verify db updated and token cleared
    session.refresh(user)
    assert user.reset_token is None
    assert user.reset_token_expires_at is None

    from app.auth import verify_password

    assert verify_password("new_secure_pw", user.password_hash)


def test_password_reset_invalid_token(client):
    response = client.get("/reset-password?token=invalid_token")
    assert response.status_code == 200
    assert "invalido o scaduto" in response.text

    response = client.post("/reset-password-confirm", data={"token": "invalid_token", "new_password": "new_secure_pw"})
    assert response.status_code == 200
    assert "invalido o scaduto" in response.text
