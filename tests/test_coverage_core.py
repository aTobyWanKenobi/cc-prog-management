import contextlib
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from jose import jwt

from app.auth import ALGORITHM, SECRET_KEY, get_admin_user, get_current_user, get_tech_user, get_unit_user
from app.database import get_db
from app.models import TerrenoCategoria, User


def test_auth_token_bearer_split():
    # Test line 54 string split
    mock_request = MagicMock()
    mock_request.cookies.get.return_value = "Bearer test_token"
    mock_db = MagicMock()
    # It will fail at jwt.decode, but line 54 will be covered
    res = get_current_user(mock_request, mock_db)
    assert res is None


def test_auth_token_no_sub():
    # Test line 60
    # Create valid signed JWT without 'sub'
    token = jwt.encode({"other": "claim"}, SECRET_KEY, algorithm=ALGORITHM)
    mock_request = MagicMock()
    mock_request.cookies.get.return_value = token
    mock_db = MagicMock()
    res = get_current_user(mock_request, mock_db)
    assert res is None


def test_get_unit_user():
    user = User(username="test", role="unit")
    assert get_unit_user(user) == user


def test_get_tech_user_fails():
    user = User(username="test", role="unit")
    with pytest.raises(HTTPException) as exc:
        get_tech_user(user)
    assert exc.value.status_code == 403


def test_get_admin_user_fails():
    user = User(username="test", role="tech")
    with pytest.raises(HTTPException) as exc:
        get_admin_user(user)
    assert exc.value.status_code == 403


def test_database_get_db():
    gen = get_db()
    db = next(gen)
    assert db is not None
    with contextlib.suppress(StopIteration):
        next(gen)


def test_models_categorie_terreni():
    is_valid, inv = TerrenoCategoria.validate_tags("")
    assert is_valid is False
    assert inv == ["empty"]

    is_valid, inv = TerrenoCategoria.validate_tags("   ")
    assert is_valid is False

    vals = TerrenoCategoria.all_values()
    assert "ACQUA" not in vals
