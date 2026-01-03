import csv
import io

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.auth import get_authenticated_user, get_tech_user
from app.database import get_db
from app.models import Challenge, Completion, Pattuglia, Unita, User

router = APIRouter(
    dependencies=[Depends(get_authenticated_user)]  # All public routes require at least being logged in
)

templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def ranking_page(
    request: Request,
    sottocampo_filter: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
):
    query = db.query(Pattuglia).join(Unita).options(joinedload(Pattuglia.unita))

    # Filter logic
    if sottocampo_filter and sottocampo_filter.strip():
        query = query.filter(Unita.sottocampo == sottocampo_filter)
    else:
        sottocampo_filter = None

    # Sort by score desc
    pattuglie = query.order_by(Pattuglia.current_score.desc()).all()

    # Calculate rank
    for index, p in enumerate(pattuglie):
        p.rank = index + 1

    all_unita = db.query(Unita).order_by(Unita.name).all()

    # Get unique sottocampi
    sottocampi = sorted(list(set(u.sottocampo for u in all_unita)))

    return templates.TemplateResponse(
        "ranking.html",
        {
            "request": request,
            "pattuglie": pattuglie,
            "unita": all_unita,
            "sottocampi": sottocampi,
            "current_sottocampo_filter": sottocampo_filter,
            "user": user,
        },
    )


@router.get("/prenotazioni", response_class=HTMLResponse)
async def prenotazioni_page(request: Request, user: User = Depends(get_authenticated_user)):
    return templates.TemplateResponse("prenotazioni.html", {"request": request, "user": user})


@router.get("/input", response_class=HTMLResponse)
async def input_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_tech_user)):
    pattuglie = db.query(Pattuglia).order_by(Pattuglia.name).all()
    challenges = db.query(Challenge).order_by(Challenge.name).all()
    return templates.TemplateResponse(
        "input.html", {"request": request, "pattuglie": pattuglie, "challenges": challenges, "user": user}
    )


@router.get("/gestione-terreni", response_class=HTMLResponse)
async def gestione_terreni_page(request: Request, user: User = Depends(get_tech_user)):
    return templates.TemplateResponse("gestione_terreni.html", {"request": request, "user": user})


@router.post("/complete")
async def register_completion(
    pattuglia_id: int = Form(...),
    challenge_id: int = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_tech_user),
):
    # Check if already completed
    existing = (
        db.query(Completion)
        .filter(Completion.pattuglia_id == pattuglia_id, Completion.challenge_id == challenge_id)
        .first()
    )

    if existing:
        return RedirectResponse(url="/input?error=already_completed", status_code=status.HTTP_303_SEE_OTHER)

    # Register completion
    new_completion = Completion(pattuglia_id=pattuglia_id, challenge_id=challenge_id)
    db.add(new_completion)

    # Update score
    pattuglia = db.query(Pattuglia).filter(Pattuglia.id == pattuglia_id).first()
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()

    if pattuglia and challenge:
        pattuglia.current_score += challenge.points
        db.commit()

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/timeline", response_class=HTMLResponse)
async def timeline_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)):
    completions = (
        db.query(Completion)
        .options(joinedload(Completion.pattuglia), joinedload(Completion.challenge))
        .order_by(Completion.timestamp.desc())
        .limit(100)
        .all()
    )

    # Deduplicate in case of race conditions or join artifacts
    # We use a set of IDs to ensure we only show unique completion IDs
    # If the user meant "same semantic completion", we might need more,
    # but let's start by ensuring unique IDs.
    # Actually, SQLAlchemy `.all()` on this query usually returns unique objects.
    # Let's filter by (pattuglia, challenge) if they appear consecutively?
    # No, let's just use `unique_completions` based on ID.
    unique_completions = []
    seen_ids = set()
    for c in completions:
        if c.id not in seen_ids:
            unique_completions.append(c)
            seen_ids.add(c.id)

    # Also, lets explicitly handle the case where "double clicks" might have created 2 entries
    # with diff IDs but same content
    # by checking if (pattuglia_id, challenge_id) was just seen?
    # No, that might hide legitimate re-completions if allowed (though /complete blocks it).
    # Let's trust unique IDs for now unless the user confirms double database entries.

    return templates.TemplateResponse(
        "timeline.html", {"request": request, "completions": unique_completions, "user": user}
    )


# --- Export ---
@router.get("/export/ranking")
async def export_ranking(db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)):
    # Technically only tech/admin should export? Or maybe units too?
    # Requirement: "witouth the export button" for units.
    # So we should block it or just hide it. Let's block it for 'unit' role to be safe.
    if user.role == "unit":
        raise HTTPException(status_code=403, detail="Not authorized")

    pattuglie = db.query(Pattuglia).options(joinedload(Pattuglia.unita)).order_by(Pattuglia.current_score.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Posizione", "Pattuglia", "Capo Pattuglia", "Unità", "Sottocampo", "Punteggio"])

    for index, p in enumerate(pattuglie):
        writer.writerow([index + 1, p.name, p.capo_pattuglia, p.unita.name, p.unita.sottocampo, p.current_score])

    output.seek(0)

    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=classifica_scout.csv"
    return response
