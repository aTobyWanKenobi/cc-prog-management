from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import Pattuglia, Challenge, Unita, Completion, User, Terreno, Prenotazione
from app.auth import get_admin_user

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_admin_user)]
)

templates = Jinja2Templates(directory="app/templates")

# --- Dashboard ---
@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(get_admin_user)):
    completions = db.query(Completion).options(
        joinedload(Completion.pattuglia),
        joinedload(Completion.challenge)
    ).order_by(Completion.timestamp.desc()).limit(50).all()
    
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "completions": completions,
        "user": user,
        "active_tab": "dashboard"
    })

# --- Pattuglie Management ---
@router.get("/pattuglie", response_class=HTMLResponse)
async def admin_pattuglie(request: Request, db: Session = Depends(get_db), user: User = Depends(get_admin_user)):
    pattuglie = db.query(Pattuglia).options(joinedload(Pattuglia.unita)).all()
    unita = db.query(Unita).all()
    return templates.TemplateResponse("admin_pattuglie.html", {
        "request": request,
        "pattuglie": pattuglie,
        "unita": unita,
        "user": user,
        "active_tab": "pattuglie"
    })

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
    return RedirectResponse(url="/admin/pattuglie", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/pattuglie/{pattuglia_id}", response_class=HTMLResponse)
async def edit_pattuglia_form(pattuglia_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_admin_user)):
    pattuglia = db.query(Pattuglia).filter(Pattuglia.id == pattuglia_id).first()
    unita = db.query(Unita).all()
    if not pattuglia:
        raise HTTPException(status_code=404, detail="Pattuglia not found")
    
    # Get specific log for this pattuglia
    completions = db.query(Completion).filter(Completion.pattuglia_id == pattuglia_id).options(
        joinedload(Completion.challenge)
    ).order_by(Completion.timestamp.desc()).all()

    return templates.TemplateResponse("edit_pattuglia.html", {
        "request": request, 
        "pattuglia": pattuglia, 
        "unita": unita, 
        "completions": completions,
        "user": user
    })

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
    return RedirectResponse(url="/admin/pattuglie", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/pattuglie/{pattuglia_id}/delete")
async def delete_pattuglia(pattuglia_id: int, db: Session = Depends(get_db)):
    pattuglia = db.query(Pattuglia).filter(Pattuglia.id == pattuglia_id).first()
    if pattuglia:
        db.query(Completion).filter(Completion.pattuglia_id == pattuglia_id).delete()
        db.delete(pattuglia)
        db.commit()
    return RedirectResponse(url="/admin/pattuglie", status_code=status.HTTP_303_SEE_OTHER)

# --- Challenges Management ---
@router.get("/challenges", response_class=HTMLResponse)
async def admin_challenges(request: Request, db: Session = Depends(get_db), user: User = Depends(get_admin_user)):
    challenges = db.query(Challenge).all()
    return templates.TemplateResponse("admin_challenges.html", {
        "request": request,
        "challenges": challenges,
        "user": user,
        "active_tab": "challenges"
    })

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
    return RedirectResponse(url="/admin/challenges", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/challenges/{challenge_id}", response_class=HTMLResponse)
async def edit_challenge_form(challenge_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_admin_user)):
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    # Get specific log for this challenge
    completions = db.query(Completion).filter(Completion.challenge_id == challenge_id).options(
        joinedload(Completion.pattuglia)
    ).order_by(Completion.timestamp.desc()).all()

    return templates.TemplateResponse("edit_challenge.html", {
        "request": request, 
        "challenge": challenge,
        "completions": completions,
        "user": user
    })

@router.post("/challenges/{challenge_id}/edit")
async def edit_challenge(
    challenge_id: int, 
    name: str = Form(...), 
    description: str = Form(...), 
    points: int = Form(...),
    reward_tokens: int = Form(0),
    is_fungo: bool = Form(False),
    retroactive_update: bool = Form(False),
    db: Session = Depends(get_db)
):
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if challenge:
        old_points = challenge.points
        
        challenge.name = name
        challenge.description = description
        challenge.points = points
        challenge.reward_tokens = reward_tokens
        challenge.is_fungo = is_fungo
        
        if retroactive_update and old_points != points:
            # Recalculate scores for all affected pattuglie
            point_diff = points - old_points
            
            # Find all completions for this challenge
            completions = db.query(Completion).filter(Completion.challenge_id == challenge_id).all()
            affected_pattuglie_ids = set(c.pattuglia_id for c in completions)
            
            for pid in affected_pattuglie_ids:
                pattuglia = db.query(Pattuglia).filter(Pattuglia.id == pid).first()
                if pattuglia:
                    # Count how many times they completed THIS challenge
                    count = db.query(Completion).filter(
                        Completion.pattuglia_id == pid, 
                        Completion.challenge_id == challenge_id
                    ).count()
                    
                    # Adjust score
                    pattuglia.current_score += (point_diff * count)
        
        db.commit()
    return RedirectResponse(url="/admin/challenges", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/challenges/{challenge_id}/delete")
async def delete_challenge(challenge_id: int, db: Session = Depends(get_db)):
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if challenge:
        db.query(Completion).filter(Completion.challenge_id == challenge_id).delete()
        db.delete(challenge)
        db.commit()
    return RedirectResponse(url="/admin/challenges", status_code=status.HTTP_303_SEE_OTHER)

# --- Users Management ---
@router.get("/users", response_class=HTMLResponse)
async def admin_users(request: Request, db: Session = Depends(get_db), user: User = Depends(get_admin_user)):
    users = db.query(User).options(joinedload(User.unita)).all()
    return templates.TemplateResponse("admin_users.html", {
        "request": request,
        "users": users,
        "user": user,
        "active_tab": "users"
    })

@router.post("/users/{user_id}/password")
async def reset_user_password(user_id: int, password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        from app.auth import pwd_context
        user.password_hash = pwd_context.hash(password)
        db.commit()
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)

# --- Terreni Management ---

@router.get("/terreni", response_class=HTMLResponse)
async def admin_terreni(request: Request, db: Session = Depends(get_db), user: User = Depends(get_admin_user)):
    terreni = db.query(Terreno).all()
    return templates.TemplateResponse("admin_terreni.html", {
        "request": request,
        "user": user,
        "terreni": terreni,
        "active_tab": "terreni"
    })

@router.post("/terreni")
async def create_terreno(
    request: Request,
    name: str = Form(...),
    tags: str = Form(...),
    center_lat: str = Form(...),
    center_lon: str = Form(...),
    polygon: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_admin_user)
):
    new_terreno = Terreno(
        name=name,
        tags=tags,
        center_lat=center_lat,
        center_lon=center_lon,
        polygon=polygon
    )
    db.add(new_terreno)
    db.commit()
    return RedirectResponse(url="/admin/terreni", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/terreni/{terreno_id}", response_class=HTMLResponse)
async def edit_terreno(request: Request, terreno_id: int, db: Session = Depends(get_db), user: User = Depends(get_admin_user)):
    terreno = db.query(Terreno).filter(Terreno.id == terreno_id).first()
    if not terreno:
        raise HTTPException(status_code=404, detail="Terreno not found")
    
    prenotazioni = db.query(Prenotazione).filter(Prenotazione.terreno_id == terreno_id).order_by(Prenotazione.start_time.desc()).all()
    
    return templates.TemplateResponse("edit_terreno.html", {
        "request": request,
        "user": user,
        "terreno": terreno,
        "prenotazioni": prenotazioni,
        "active_tab": "terreni"
    })

@router.post("/terreni/{terreno_id}")
async def update_terreno(
    request: Request,
    terreno_id: int,
    name: str = Form(...),
    tags: str = Form(...),
    center_lat: str = Form(...),
    center_lon: str = Form(...),
    polygon: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_admin_user)
):
    terreno = db.query(Terreno).filter(Terreno.id == terreno_id).first()
    if not terreno:
        raise HTTPException(status_code=404, detail="Terreno not found")
    
    terreno.name = name
    terreno.tags = tags
    terreno.center_lat = center_lat
    terreno.center_lon = center_lon
    terreno.polygon = polygon
    
    db.commit()
    return RedirectResponse(url=f"/admin/terreni/{terreno_id}", status_code=status.HTTP_303_SEE_OTHER)

@router.post("/terreni/{terreno_id}/delete")
async def delete_terreno(request: Request, terreno_id: int, db: Session = Depends(get_db), user: User = Depends(get_admin_user)):
    terreno = db.query(Terreno).filter(Terreno.id == terreno_id).first()
    if terreno:
        db.delete(terreno)
        db.commit()
    return RedirectResponse(url="/admin/terreni", status_code=status.HTTP_303_SEE_OTHER)

# --- General Actions ---
@router.post("/rollback/{completion_id}")
async def rollback_completion(completion_id: int, request: Request, db: Session = Depends(get_db)):
    completion = db.query(Completion).filter(Completion.id == completion_id).first()
    if completion:
        # Deduct points
        pattuglia = completion.pattuglia
        challenge = completion.challenge
        pattuglia.current_score -= challenge.points
        
        db.delete(completion)
        db.commit()
    
    # Redirect back to where we came from if possible, or default to dashboard
    referer = request.headers.get("referer")
    if referer:
        return RedirectResponse(url=referer, status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
