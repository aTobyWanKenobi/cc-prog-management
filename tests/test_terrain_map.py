from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.main import app
from app.models import Prenotazione, Terreno, Unita, User

# Note: completion_status might not be in models, just checking imports.
# Actually completion_status is not a model.
# Note: completion_status might not be in models, just checking imports.
# Actually completion_status is not a model.
# from app.database import get_db # Not needed if we trust conftest overrides or use session directly

# client = TestClient(app) # Remove global client, use fixture


def test_terreno_fields(session: Session):
    # Check if new fields exist
    t = Terreno(
        name="Test Terrain",
        tags="TEST",
        center_lat="0",
        center_lon="0",
        polygon="[]",
        description="Desc",
        image_urls='["http://example.com"]',
    )
    session.add(t)
    session.commit()
    session.refresh(t)

    assert t.description == "Desc"
    assert "http" in t.image_urls


def test_api_availability(client, session: Session):
    # Setup Data
    # Terrain
    t = Terreno(name="MapTest", tags="A", center_lat="0", center_lon="0", polygon="[]")
    session.add(t)
    session.commit()

    # Unit
    u = Unita(name="TestUnitMap", sottocampo="Test")
    session.add(u)
    session.commit()

    # Reservation: Today 14:00 - 16:00
    base_date = datetime(2026, 7, 25, 0, 0, 0)  # Use the future date for consistency
    res_start = base_date + timedelta(hours=14)
    res_end = base_date + timedelta(hours=16)

    p = Prenotazione(
        terreno_id=t.id, unita_id=u.id, start_time=res_start, end_time=res_end, duration=2, status="APPROVED"
    )
    session.add(p)
    session.commit()

    # Authenticate
    user = User(username="mapuser", password_hash="hash", role="unit", unita_id=u.id)
    session.add(user)
    session.commit()

    # Use dependency override for user authentication
    from app.auth import get_authenticated_user

    app.dependency_overrides[get_authenticated_user] = lambda: user

    # Test 1: Query exact overlap (BOOKED)
    response = client.get(
        "/api/terreni/availability", params={"start_date": res_start.isoformat(), "end_date": res_end.isoformat()}
    )

    assert response.status_code == 200
    data = response.json()
    target = next(x for x in data if x["id"] == t.id)
    assert target["status"] == "BOOKED"

    # Test 2: Partial Overlap (Time window wider: 12:00 - 18:00)
    response = client.get(
        "/api/terreni/availability",
        params={
            "start_date": (res_start - timedelta(hours=2)).isoformat(),
            "end_date": (res_end + timedelta(hours=2)).isoformat(),
        },
    )
    data = response.json()
    target = next(x for x in data if x["id"] == t.id)
    assert target["status"] == "PARTIAL"

    # Test 3: No Overlap (Next day)
    response = client.get(
        "/api/terreni/availability",
        params={
            "start_date": (res_start + timedelta(days=1)).isoformat(),
            "end_date": (res_end + timedelta(days=1)).isoformat(),
        },
    )
    data = response.json()
    target = next(x for x in data if x["id"] == t.id)
    assert target["status"] == "FREE"

    # Cleanup
    app.dependency_overrides = {}
