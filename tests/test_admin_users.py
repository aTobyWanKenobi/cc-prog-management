from unittest.mock import patch

from app.models import User

# Uses fixtures from conftest.py implicitly when passed as arguments
# (admin_client, db_session)

MOCK_HASH = "$argon2id$v=19$m=65536,t=3,p=4$uDcGYOwdwzgHAIDwHmNMaQ$Zz9Nrb26WqJFip1NhJwp6ndqBVMgh15zjAUUHsJXNYU"


def test_admin_users_page(client, session):
    from app.models import User

    admin = User(username="admin", password_hash=MOCK_HASH, role="admin")
    session.add(admin)
    session.commit()

    # Login manually
    client.post("/login", data={"username": "admin", "password": "god", "login_role": "direzione"})

    response = client.get("/admin/users")
    assert response.status_code == 200
    assert "Gestione Utenti" in response.text
    assert "admin" in response.text


@patch("secrets.choice")
def test_create_user(mock_choice, client, session):
    from app.models import User

    admin = User(username="admin", password_hash=MOCK_HASH, role="admin")
    session.add(admin)
    session.commit()
    client.post("/login", data={"username": "admin", "password": "god", "login_role": "direzione"})

    # Mock password generation to return 'a' 12 times
    mock_choice.return_value = "a"

    response = client.post(
        "/admin/users", data={"username": "new_scout", "email": "scout@example.com", "role": "unit", "unita_id": "1"}
    )
    assert response.status_code == 200
    assert "Utente creato con successo:" in response.text
    assert "new_scout" in response.text
    assert "aaaaaaaaaaaa" in response.text

    user = session.query(User).filter(User.username == "new_scout").first()
    assert user is not None
    assert user.email == "scout@example.com"
    assert user.role == "unit"
    assert user.unita_id == 1


def test_edit_user(client, session):
    # Admin
    admin = User(username="admin", password_hash=MOCK_HASH, role="admin")
    session.add(admin)

    # Create dummy user to edit
    new_user = User(username="edit_me", role="unit", password_hash=MOCK_HASH)
    session.add(new_user)
    session.commit()
    user_id = new_user.id
    client.post("/login", data={"username": "admin", "password": "god", "login_role": "direzione"})

    response = client.post(
        f"/admin/users/{user_id}/edit",
        data={"username": "edited_scout", "email": "edited@example.com", "role": "tech", "unita_id": "1"},
    )
    assert response.status_code == 200
    assert response.url.path == "/admin/users"

    user = session.query(User).filter(User.id == user_id).first()
    assert user.username == "edited_scout"
    assert user.email == "edited@example.com"
    assert user.role == "tech"


def test_reset_user_password(client, session):
    from app.models import User

    admin = User(username="admin", password_hash=MOCK_HASH, role="admin")
    session.add(admin)
    new_user = User(username="pw_reset_me", role="unit", password_hash=MOCK_HASH)
    session.add(new_user)
    session.commit()
    user_id = new_user.id

    client.post("/login", data={"username": "admin", "password": "god", "login_role": "direzione"})

    response = client.post(f"/admin/users/{user_id}/password", data={"password": "new_secure_password"})
    assert response.status_code == 200
    assert response.url.path == "/admin/users"

    user = session.query(User).filter(User.id == user_id).first()
    from app.auth import verify_password

    assert verify_password("new_secure_password", user.password_hash)


def test_delete_user(client, session):
    from app.models import User

    admin = User(username="admin", password_hash=MOCK_HASH, role="admin")
    session.add(admin)
    new_user = User(username="delete_me", role="unit", password_hash=MOCK_HASH)
    session.add(new_user)
    session.commit()
    user_id = new_user.id
    client.post("/login", data={"username": "admin", "password": "god", "login_role": "direzione"})

    response = client.post(f"/admin/users/{user_id}/delete")
    assert response.status_code == 200
    assert response.url.path == "/admin/users"

    user = session.query(User).filter(User.id == user_id).first()
    assert user is None
