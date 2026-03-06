from fastapi import APIRouter, Request, Depends, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
import csv
import io

from app.database import get_db
from app.models import User, Unita, Pattuglia, Completion, Challenge, Terreno, Prenotazione
from app.auth import get_admin_user, get_tech_user, get_password_hash
from app.email_service import send_account_created_email

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request, db: Session = Depends(get_db), user: User = Depends(get_tech_user)
):
    users_count = db.query(User).count()
    units_count = db.query(Unita).count()
    pattuglie_count = db.query(Pattuglia).count()
    completions_count = db.query(Completion).count()

    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {
            "user": user,
            "stats": {
                "users": users_count,
                "units": units_count,
                "pattuglie": pattuglie_count,
                "completions": completions_count,
            },
        },
    )


@router.get("/users", response_class=HTMLResponse)
async def list_users(
    request: Request, db: Session = Depends(get_db), user: User = Depends(get_admin_user)
):
    users = db.query(User).options(joinedload(User.unita)).all()
    return templates.TemplateResponse(request, "admin/users.html", {"user": user, "users": users})


@router.get("/users/create", response_class=HTMLResponse)
async def create_user_page(
    request: Request, db: Session = Depends(get_db), user: User = Depends(get_admin_user)
):
    units = db.query(Unita).all()
    return templates.TemplateResponse(
        request, "admin/user_create.html", {"user": user, "units": units}
    )


@router.post("/users/create")
async def create_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    unita_id: int | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_admin_user),
):
    hashed_password = get_password_hash(password)
    new_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        role=role,
        unita_id=unita_id,
    )
    db.add(new_user)
    db.commit()

    # Send welcome email with credentials
    send_account_created_email(email, username, password)

    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/units", response_class=HTMLResponse)
async def list_units(
    request: Request, db: Session = Depends(get_db), user: User = Depends(get_tech_user)
):
    units = db.query(Unita).all()
    return templates.TemplateResponse(request, "admin/units.html", {"user": user, "units": units})


@router.get("/terreni", response_class=HTMLResponse)
async def list_terreni(
    request: Request, db: Session = Depends(get_db), user: User = Depends(get_tech_user)
):
    terreni = db.query(Terreno).all()
    return templates.TemplateResponse(
        request, "admin/terreni.html", {"user": user, "terreni": terreni}
    )


@router.get("/prenotazioni", response_class=HTMLResponse)
async def list_prenotazioni(
    request: Request, db: Session = Depends(get_db), user: User = Depends(get_tech_user)
):
    prenotazioni = (
        db.query(Prenotazione)
        .options(joinedload(Prenotazione.terreno), joinedload(Prenotazione.unita))
        .all()
    )
    return templates.TemplateResponse(
        request, "admin/prenotazioni.html", {"user": user, "prenotazioni": prenotazioni}
    )


@router.post("/users/delete/{user_id}")
async def delete_user(
    user_id: int, db: Session = Depends(get_db), user: User = Depends(get_admin_user)
):
    user_to_delete = db.query(User).filter(User.id == user_id).first()
    if user_to_delete:
        db.delete(user_to_delete)
        db.commit()
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)
