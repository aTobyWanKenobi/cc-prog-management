from app.models import Unita, User


def test_login_invalid_posto(client, session):
    # Tests line 76-77
    user = User(
        username="fake_posto",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$uDcGYOwdwzgHAIDwHmNMaQ$Zz9Nrb26WqJFip1NhJwp6ndqBVMgh15zjAUUHsJXNYU",
        role="unit",
    )
    unita = Unita(name="Fake", tipo="Reparto")
    user.unita = unita
    session.add(unita)
    session.add(user)
    session.commit()
    response = client.post("/login", data={"username": "fake_posto", "password": "god", "login_role": "posto"})
    assert "L&#39;unità non è un Posto" in response.text


def test_login_invalid_staff(client, session):
    # Tests line 79
    user = User(
        username="fake_staff_user",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$uDcGYOwdwzgHAIDwHmNMaQ$Zz9Nrb26WqJFip1NhJwp6ndqBVMgh15zjAUUHsJXNYU",
        role="unit",
    )
    session.add(user)
    session.commit()
    response = client.post("/login", data={"username": "fake_staff_user", "password": "god", "login_role": "staff"})
    assert "Non sei autorizzato" in response.text


def test_password_reset_page(client):
    # Tests line 110
    response = client.get("/password-reset")
    assert response.status_code == 200
