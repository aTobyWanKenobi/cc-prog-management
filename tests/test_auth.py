from datetime import timedelta

from jose import jwt

# Since get_password_hash is in init_db usually, check where it is.
# Checking app/auth.py... it has verify_password but likely uses pwd_context directly.
from passlib.context import CryptContext

from app.auth import ALGORITHM, SECRET_KEY, create_access_token, verify_password
from app.models import User

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def test_hash_and_verify_password():
    password = "secret_password"
    hashed = pwd_context.hash(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)


def test_jwt_token_creation():
    data = {"sub": "testuser"}
    token = create_access_token(data=data, expires_delta=timedelta(minutes=5))

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "testuser"
    assert "exp" in payload


def test_login_flow(client, session):
    # Create user
    hashed_pwd = pwd_context.hash("testpass")
    user = User(username="testlogin", password_hash=hashed_pwd, role="unit")
    session.add(user)
    session.commit()

    # 1. Successful Login
    response = client.post(
        "/login",
        data={"username": "testlogin", "password": "testpass"},
        follow_redirects=False,  # Standard login redirects to / or /admin
    )
    # Allows 302, 303 or 200 depending on implementation. In main.py it redirects.
    assert response.status_code == 303
    assert "access_token" in response.cookies
    token = response.cookies["access_token"]
    assert token is not None

    # 2. Wrong Password
    response = client.post("/login", data={"username": "testlogin", "password": "wrongpass"})
    assert response.status_code == 200
    assert "Credenziali non valide" in response.text

    # 3. Non-existent User
    response = client.post("/login", data={"username": "ghost", "password": "any"})
    assert response.status_code == 200
    assert "Credenziali non valide" in response.text

    response = client.get("/logout", follow_redirects=False)
    assert response.status_code == 303
    # Check cookie is cleared (max-age=0 or empty)
    # Starlette TestClient cookie handling can be tricky, check headers 'set-cookie'
    assert 'access_token=""' in response.headers["set-cookie"] or "Max-Age=0" in response.headers["set-cookie"]


def test_invalid_token(client):
    # Set bad cookie
    client.cookies.set("access_token", "badtoken")
    # Protected route
    response = client.get("/export/ranking")  # uses get_authenticated_user
    # Should fail auth -> 401 -> Redirect to login (200)
    assert response.status_code == 200
    assert "Login" in response.text
