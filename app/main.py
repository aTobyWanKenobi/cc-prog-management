from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, UTC, timedelta
import secrets

from app.database import engine, Base, get_db
from app.models import User, Unita
from app.routers import public, admin
from app.auth import get_password_hash, get_authenticated_user
from app.email_service import send_reset_password_email


# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Punteggiometro CC")

# Setup templates
templates = Jinja2Templates(directory="app/templates")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    return response


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(request, "forgot_password.html")


@app.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password_submit(
    request: Request, email: str = Form(...), db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if user:
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        # Token expires in 1 hour
        user.reset_token_expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(
            hours=1
        )
        db.commit()

        # Send email
        send_reset_password_email(email, token)

    # Always return success message to prevent user enumeration
    return templates.TemplateResponse(
        request,
        "forgot_password.html",
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

    user.hashed_password = get_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.commit()

    return templates.TemplateResponse(
        request,
        "password_reset_confirm.html",
        {"success": "Password aggiornata correttamente. Ora puoi effettuare il login."},
    )


@app.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request, db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)
):
    unita = None
    if user.unita_id:
        unita = db.query(Unita).filter(Unita.id == user.unita_id).first()
    return templates.TemplateResponse(request, "profile.html", {"user": user, "unita": unita})


# Include routers
app.include_router(public.router)
app.include_router(admin.router)
