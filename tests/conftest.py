import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.auth import get_current_user

import os

@pytest.fixture(name="session")
def session_fixture():
    """
    Creates a fresh database session for a test.
    Owns its own Engine to ensure complete isolation.
    """
    # Create isolated in-memory DB for this specific test
    # Usage of StaticPool means all connections from this engine access the same memory space
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    yield session
    
    session.close()
    engine.dispose()


@pytest.fixture(name="client")
def client_fixture(session):
    """
    Returns a TestClient with the dependency override for the DB session.
    """
    def override_get_db():
        try:
            yield session
        finally:
            pass # Session is closed by fixture

    app.dependency_overrides[get_db] = override_get_db
    # Clear other overrides if any (like auth overrides from previous tests if we didn't clean up)
    # app.dependency_overrides = {get_db: override_get_db} # Careful, might remove needed overrides
    
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    """
    Helper to get auth headers for different roles.
    Since we mock the DB, we might need to actually create users in the DB first 
    OR mock the token generation. 
    Let's use valid usage: Create user -> Login -> Get Token.
    """
    return {} # Placeholder if needed, but we can just use client.post("/login") helper

