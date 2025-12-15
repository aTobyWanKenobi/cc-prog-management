from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

# Configuration
SECRET_KEY = "CHANGE_THIS_IN_PRODUCTION_SECRET_KEY"  # In prod use env var
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter(tags=["auth"])


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta if expires_delta else datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Dependency to get current user from cookie
def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        # If no token, return None (allow public access to some pages if we wanted,
        # but here we want to redirect to login usually.
        # For dependencies that REQUIRE auth, we'll check this return value)
        return None

    # Remove "Bearer " prefix if present (though cookies usually just have the token)
    if token.startswith("Bearer "):
        token = token.split(" ")[1]

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None

    user = db.query(User).filter(User.username == username).first()
    return user


# --- Role Dependencies ---


def get_authenticated_user(user: User | None = Depends(get_current_user)):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_unit_user(user: User = Depends(get_authenticated_user)):
    # Unit user or higher (Tech, Admin)
    # Actually, unit pages are accessible to everyone logged in?
    # The requirement says "These users will get access to the public area".
    # So basically any logged in user.
    return user


def get_tech_user(user: User = Depends(get_authenticated_user)):
    if user.role not in ["tech", "admin"]:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    return user


def get_admin_user(user: User = Depends(get_authenticated_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough privileges")
    return user
