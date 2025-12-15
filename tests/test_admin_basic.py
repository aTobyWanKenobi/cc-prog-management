from passlib.context import CryptContext

from app.models import Challenge, User

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def create_admin_user(session):
    hashed = pwd_context.hash("admin")
    admin = User(username="admin", password_hash=hashed, role="admin")
    session.add(admin)
    session.commit()
    return admin


def auth_header(client):
    # Logs in as admin and returns headers/cookies logic handled by client session
    client.post("/login", data={"username": "admin", "password": "admin"})


def test_admin_dashboard_access(client, session):
    create_admin_user(session)
    client.post("/login", data={"username": "admin", "password": "admin"})

    response = client.get("/admin/")
    assert response.status_code == 200
    assert "Dashboard" in response.text


def test_manage_users(client, session):
    create_admin_user(session)
    client.post("/login", data={"username": "admin", "password": "admin"})

    # Users list
    response = client.get("/admin/users")
    assert response.status_code == 200
    assert "admin" in response.text

    # Reset password flow
    # First create a user to reset
    user = User(username="victim", password_hash="oldhash", role="unit")
    session.add(user)
    session.commit()

    response = client.post(f"/admin/users/{user.id}/password", data={"password": "newpassword"}, follow_redirects=False)
    assert response.status_code == 303

    session.refresh(user)
    assert pwd_context.verify("newpassword", user.password_hash)


def test_challenge_crud(client, session):
    create_admin_user(session)
    client.post("/login", data={"username": "admin", "password": "admin"})

    # Create
    response = client.post(
        "/admin/challenges",
        data={
            "name": "Fire Building",
            "description": " Build a fire",
            "points": "50",
            "reward_tokens": "5",
            "is_fungo": False,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303

    chal = session.query(Challenge).filter(Challenge.name == "Fire Building").first()
    assert chal is not None
    assert chal.points == 50

    # Edit
    response = client.post(
        f"/admin/challenges/{chal.id}/edit",
        data={
            "name": "Fire Building Extreme",
            "description": "Bigger fire",
            "points": "100",
            "reward_tokens": "10",
            "is_fungo": False,
            "retroactive_update": False,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    session.refresh(chal)
    assert chal.name == "Fire Building Extreme"
    assert chal.points == 100

    # Delete
    response = client.post(f"/admin/challenges/{chal.id}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert session.query(Challenge).filter(Challenge.id == chal.id).first() is None


def test_admin_get_pages(client, session):
    create_admin_user(session)
    client.post("/login", data={"username": "admin", "password": "admin"})

    assert client.get("/admin/pattuglie").status_code == 200
    assert client.get("/admin/challenges").status_code == 200
    assert client.get("/admin/terreni").status_code == 200
    assert client.get("/admin/users").status_code == 200
