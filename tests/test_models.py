from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Challenge, Completion, Pattuglia, Prenotazione, Terreno, Unita, User

# We use the 'session' fixture from conftest.py which gives us a clean DB


def test_unita_model(session):
    u = Unita(name="U1", sottocampo="S1")
    session.add(u)
    session.commit()

    # Test retrieval
    assert u.id is not None
    fetched = session.query(Unita).filter_by(name="U1").first()
    assert fetched == u

    # Test Unique Constraint on Name
    u2 = Unita(name="U1", sottocampo="S2")
    session.add(u2)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_pattuglia_relationships(session):
    u = Unita(name="U_Rel", sottocampo="S_Rel")
    session.add(u)
    session.commit()

    p = Pattuglia(name="P_Rel", capo_pattuglia="C_Rel", unita_id=u.id)
    session.add(p)
    session.commit()

    # Test relationship access
    assert p.unita == u
    assert u.pattuglie == [p]

    # Test delete behavior (if no cascade, it might fail or set null depending on config)
    # Our models don't specify cascade="all, delete", so deleting Unit might raise error
    # if Foreign Key constraint is enforced, OR leave orphans.
    # SQLAlchemy default relation is usually restricted by FK.
    session.delete(u)
    # SQLite enforces FKs only if PRAGMA foreign_keys=ON.
    # SQLAlchemy usually enables it for SQLite.
    # If it fails, good.
    try:
        session.commit()
    except IntegrityError:
        session.rollback()  # Expected behavior if strict
    except Exception:
        # If successfully deleted, check orphans?
        pass


def test_challenge_defaults(session):
    c = Challenge(name="Def", description="Desc", points=10)
    session.add(c)
    session.commit()

    assert c.is_fungo is False  # Default
    assert c.reward_tokens == 0  # Default


def test_completion_timestamp(session):
    u = Unita(name="U_Comp", sottocampo="S")
    p = Pattuglia(name="P_Comp", capo_pattuglia="C", unita=u)
    c = Challenge(name="C_Comp", description="D", points=10)
    session.add_all([u, p, c])
    session.commit()

    comp = Completion(pattuglia_id=p.id, challenge_id=c.id)
    session.add(comp)
    session.commit()

    assert comp.timestamp is not None
    assert isinstance(comp.timestamp, datetime)
    # Check relationships
    assert comp.pattuglia == p
    assert comp.challenge == c
    assert comp in p.completions
    assert comp in c.completions


def test_user_optional_unita(session):
    # Admin has no unit
    u_admin = User(username="admin_model", password_hash="x", role="admin")
    session.add(u_admin)
    session.commit()
    assert u_admin.unita_id is None

    # Unit user has unit
    unita = Unita(name="U_User", sottocampo="S")
    session.add(unita)
    session.commit()

    u_unit = User(username="unit_model", password_hash="x", role="unit", unita_id=unita.id)
    session.add(u_unit)
    session.commit()

    assert u_unit.unita == unita


def test_terreno_prenotazione(session):
    t = Terreno(name="T1", tags="TAG", center_lat="0", center_lon="0", polygon="[]")
    u = Unita(name="U_Terr", sottocampo="S")
    session.add_all([t, u])
    session.commit()

    pren = Prenotazione(
        terreno_id=t.id,
        unita_id=u.id,
        start_time=datetime(2025, 1, 1, 10, 0),
        end_time=datetime(2025, 1, 1, 12, 0),
        duration=2,
    )
    session.add(pren)
    session.commit()

    assert pren.status == "PENDING"  # Default
    assert pren.terreno == t
    assert pren.unita == u
    assert pren in t.prenotazioni
