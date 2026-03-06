import jwt
from datetime import datetime, timedelta, UTC
from passlib.context import CryptContext
from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
import os

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-it-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC).replace(tzinfo=None) + expires_delta
    else:
        expire = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_authenticated_user(request: Request, db: Session = Depends(get_db)):
    # Legacy redirect logic replaced by simpler dependency
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_tech_user(request: Request, db: Session = Depends(get_db)):
    user = get_authenticated_user(request, db)
    if user.role not in ["tech", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    return user


def get_admin_user(request: Request, db: Session = Depends(get_db)):
    user = get_authenticated_user(request, db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return user


def get_current_user_from_cookie(request: Request, db: Session):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        # Remove "Bearer " prefix if present
        if token.startswith("Bearer "):
            token = token[7:]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except jwt.PyJWTError:
        return None

    user = db.query(User).filter(User.username == username).first()
    return user


# Simple helper for templates to avoid circular imports in some cases
def Depends(factory):
    from fastapi import Depends as FastAPIDepends

    return FastAPIDepends(factory)
