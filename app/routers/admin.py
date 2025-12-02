from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import Pattuglia, Challenge, Unita, Completion, User
from app.auth import get_admin_user

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_admin_user)]
)

templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(get_admin_user)):
    pattuglie = db.query(Pattuglia).options(joinedload(Pattuglia.unita)).all()
    challenges = db.query(Challenge).all()
    unita = db.query(Unita).all()
    completions = db.query(Completion).options(
        joinedload(Completion.pattuglia),
        joinedload(Completion.challenge)
    ).order_by(Completion.timestamp.desc()).limit(50).all()
    users = db.query(User).options(joinedload(User.unita)).all()
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "pattuglie": pattuglie,
        "challenges": challenges,
        "unita": unita,
        "completions": completions,
        "users": users,
        "user": user
    })

@router.post("/users/{user_id}/password")
async def reset_user_password(user_id: int, password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        from app.auth import pwd_context
        user.password_hash = pwd_context.hash(password)
        db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/unita")
async def create_unita(name: str = Form(...), sottocampo: str = Form(...), db: Session = Depends(get_db)):
    new_unita = Unita(name=name, sottocampo=sottocampo)
    db.add(new_unita)
    db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/pattuglie")
async def create_pattuglia(
    name: str = Form(...), 
    capo_pattuglia: str = Form(...), 
    unita_id: int = Form(...), 
    db: Session = Depends(get_db)
):
    new_pattuglia = Pattuglia(name=name, capo_pattuglia=capo_pattuglia, unita_id=unita_id)
    db.add(new_pattuglia)
    db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/challenges")
async def create_challenge(
    name: str = Form(...), 
    description: str = Form(...), 
    points: int = Form(...), 
    is_fungo: bool = Form(False), 
    reward_tokens: int = Form(0),
    db: Session = Depends(get_db)
):
    new_challenge = Challenge(
        name=name, 
        description=description, 
        points=points, 
        is_fungo=is_fungo, 
        reward_tokens=reward_tokens
    )
    db.add(new_challenge)
    db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/rollback/{completion_id}")
async def rollback_completion(completion_id: int, db: Session = Depends(get_db)):
    completion = db.query(Completion).filter(Completion.id == completion_id).first()
    if completion:
        # Deduct points
        pattuglia = completion.pattuglia
        challenge = completion.challenge
        pattuglia.current_score -= challenge.points
        
        db.delete(completion)
        db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

# --- CRUD Operations ---

@router.post("/pattuglie/{pattuglia_id}/delete")
async def delete_pattuglia(pattuglia_id: int, db: Session = Depends(get_db)):
    pattuglia = db.query(Pattuglia).filter(Pattuglia.id == pattuglia_id).first()
    if pattuglia:
        # Delete associated completions first? Or rely on cascade?
        # SQLAlchemy default is usually set null or restrict. Let's manually delete completions to be safe/clean.
        db.query(Completion).filter(Completion.pattuglia_id == pattuglia_id).delete()
        db.delete(pattuglia)
        db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/challenges/{challenge_id}/delete")
async def delete_challenge(challenge_id: int, db: Session = Depends(get_db)):
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if challenge:
        db.query(Completion).filter(Completion.challenge_id == challenge_id).delete()
        db.delete(challenge)
        db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

# --- Edit Operations ---

@router.get("/pattuglie/{pattuglia_id}", response_class=HTMLResponse)
async def edit_pattuglia_form(pattuglia_id: int, request: Request, db: Session = Depends(get_db)):
    pattuglia = db.query(Pattuglia).filter(Pattuglia.id == pattuglia_id).first()
    unita = db.query(Unita).all()
    if not pattuglia:
        raise HTTPException(status_code=404, detail="Pattuglia not found")
    return templates.TemplateResponse("edit_pattuglia.html", {"request": request, "pattuglia": pattuglia, "unita": unita})

@router.post("/pattuglie/{pattuglia_id}/edit")
async def edit_pattuglia(
    pattuglia_id: int, 
    name: str = Form(...), 
    capo_pattuglia: str = Form(...), 
    unita_id: int = Form(...), 
    db: Session = Depends(get_db)
):
    pattuglia = db.query(Pattuglia).filter(Pattuglia.id == pattuglia_id).first()
    if pattuglia:
        pattuglia.name = name
        pattuglia.capo_pattuglia = capo_pattuglia
        pattuglia.unita_id = unita_id
        db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/challenges/{challenge_id}", response_class=HTMLResponse)
async def edit_challenge_form(challenge_id: int, request: Request, db: Session = Depends(get_db)):
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return templates.TemplateResponse("edit_challenge.html", {"request": request, "challenge": challenge})

@router.post("/challenges/{challenge_id}/edit")
async def edit_challenge(
    challenge_id: int, 
    name: str = Form(...), 
    description: str = Form(...), 
    reward_tokens: int = Form(0),
    is_fungo: bool = Form(False),
    db: Session = Depends(get_db)
):
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if challenge:
        challenge.name = name
        challenge.description = description
        challenge.reward_tokens = reward_tokens
        challenge.is_fungo = is_fungo
        db.commit()
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)

# --- Export moved to public.py ---
