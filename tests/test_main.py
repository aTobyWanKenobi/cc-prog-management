import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# Setup in-memory DB for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_global_auth_required():
    response = client.get("/")
    assert response.status_code == 401


def test_global_auth_success():
    response = client.get("/", auth=("progesplo", "punteggiometro"))
    assert response.status_code == 200


def test_admin_auth_required():
    response = client.get("/admin", auth=("progesplo", "punteggiometro"))
    assert response.status_code == 401


def test_admin_auth_success():
    response = client.get("/admin", auth=("admin", "admin"))
    assert response.status_code == 200


def test_create_and_complete_flow():
    # 1. Create Unita (Admin)
    client.post("/admin/unita", data={"name": "Reparto 1", "sottocampo": "Nord"}, auth=("admin", "admin"))

    # 2. Create Pattuglia (Admin)
    client.post(
        "/admin/pattuglie",
        data={"name": "Aquile", "capo_pattuglia": "Mario", "unita_id": "1"},
        auth=("admin", "admin"),
    )

    # 3. Create Challenge (Admin)
    client.post(
        "/admin/challenges",
        data={"name": "Nodi", "description": "Fai un nodo", "points": "10"},
        auth=("admin", "admin"),
    )

    # 4. Check Ranking (Public) - Score 0
    response = client.get("/", auth=("progesplo", "punteggiometro"))
    assert "Aquile" in response.text
    assert "0" in response.text  # Score

    # 5. Register Completion (Public)
    client.post(
        "/complete", data={"pattuglia_id": "1", "challenge_id": "1"}, auth=("progesplo", "punteggiometro")
    )

    # 6. Check Ranking (Public) - Score 10
    response = client.get("/", auth=("progesplo", "punteggiometro"))
    assert "10" in response.text

    # 7. Try Duplicate Completion
    response = client.post(
        "/complete",
        data={"pattuglia_id": "1", "challenge_id": "1"},
        auth=("progesplo", "punteggiometro"),
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "error=already_completed" in response.headers["location"]


def test_rollback():
    # Setup data
    client.post("/admin/unita", data={"name": "Reparto 1", "sottocampo": "Nord"}, auth=("admin", "admin"))
    client.post(
        "/admin/pattuglie",
        data={"name": "Aquile", "capo_pattuglia": "Mario", "unita_id": "1"},
        auth=("admin", "admin"),
    )
    client.post(
        "/admin/challenges",
        data={"name": "Nodi", "description": "Fai un nodo", "points": "10"},
        auth=("admin", "admin"),
    )
    client.post(
        "/complete", data={"pattuglia_id": "1", "challenge_id": "1"}, auth=("progesplo", "punteggiometro")
    )

    # Verify score 10
    response = client.get("/", auth=("progesplo", "punteggiometro"))
    assert "10" in response.text

    # Rollback (Admin) - Need completion ID, assume 1
    client.post("/admin/rollback/1", auth=("admin", "admin"))

    # Verify score 0
    response = client.get("/", auth=("progesplo", "punteggiometro"))
    assert "0" in response.text
