import os
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, get_password_hash, verify_password
from app.database import Base, engine, get_db
from app.email_service import send_password_reset_email
from app.models import User
from app.routers import admin, public

# Create tables (if not using init_db)
Base.metadata.create_all(bind=engine)

app = FastAPI()

if not os.path.exists("app/static"):
    os.makedirs("app/static")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")


# Login Routes
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(request, "login.html", {"error": "Credenziali non valide"})

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=f"{access_token}", httponly=True)
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response


# Password Reset Routes
@app.get("/password-reset", response_class=HTMLResponse)
async def password_reset_page(request: Request):
    return templates.TemplateResponse(request, "password_reset_request.html")


@app.post("/password-reset-request", response_class=HTMLResponse)
async def password_reset_request(request: Request, email: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if user:
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=2)
        db.commit()

        # In production, domain should be dynamic or injected via env vars
        reset_link = f"{request.base_url}reset-password?token={token}"
        send_password_reset_email(user.email, reset_link)

    # Always return success message to prevent email enumeration
    return templates.TemplateResponse(
        request,
        "password_reset_request.html",
        {"success": "Se l'email esiste, ti abbiamo inviato un link per reimpostare la password."},
    )


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == token).first()
    if (
        not user
        or not user.reset_token_expires_at
        or user.reset_token_expires_at < datetime.now(UTC).replace(tzinfo=None)
    ):
        return templates.TemplateResponse(
            request,
            "password_reset_confirm.html",
            {"error": "Il link è invalido o scaduto. Richiedi un nuovo reset."},
        )
    return templates.TemplateResponse(request, "password_reset_confirm.html", {"token": token})


@app.post("/reset-password-confirm", response_class=HTMLResponse)
async def reset_password_confirm(
    request: Request,
    token: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.reset_token == token).first()
    if (
        not user
        or not user.reset_token_expires_at
        or user.reset_token_expires_at < datetime.now(UTC).replace(tzinfo=None)
    ):
        return templates.TemplateResponse(
            request,
            "password_reset_confirm.html",
            {"error": "Il link è invalido o scaduto. Richiedi un nuovo reset."},
        )

    user.password_hash = get_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.commit()

    return templates.TemplateResponse(
        request, "login.html", {"error": "Password aggiornata con successo. Ora puoi fare il login."}
    )


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    response = await call_next(request)
    return response


@app.exception_handler(status.HTTP_401_UNAUTHORIZED)
async def unauthorized_exception_handler(request: Request, exc: HTTPException):
    return RedirectResponse(url="/login")


app.include_router(public.router)
app.include_router(admin.router)
