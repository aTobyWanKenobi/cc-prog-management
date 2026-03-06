from fastapi import APIRouter, Request, Depends, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
import csv
import io

from app.database import get_db
from app.models import User, Unita, Pattuglia, Completion, Challenge, Terreno, Prenotazione
from app.auth import get_authenticated_user, get_tech_user, create_access_token, verify_password
from app.email_service import send_reservation_confirmation_email, send_reservation_rejected_email

router = APIRouter(tags=["public"])
templates = Jinja2Templates(directory="app/templates")


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Username o password non corretti"}
        )

    access_token = create_access_token(data={"sub": user.username})
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response


@router.get("/ranking", response_class=HTMLResponse)
async def ranking_page(
    request: Request, db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)
):
    pattuglie = (
        db.query(Pattuglia)
        .options(joinedload(Pattuglia.unita))
        .order_by(Pattuglia.current_score.desc())
        .all()
    )
    return templates.TemplateResponse(
        request, "ranking.html", {"pattuglie": pattuglie, "user": user}
    )


@router.get("/input", response_class=HTMLResponse)
async def input_page(
    request: Request, db: Session = Depends(get_db), user: User = Depends(get_tech_user)
):
    pattuglie = db.query(Pattuglia).all()
    challenges = db.query(Challenge).all()
    return templates.TemplateResponse(
        request, "input.html", {"pattuglie": pattuglie, "challenges": challenges, "user": user}
    )


@router.get("/gestione-terreni", response_class=HTMLResponse)
async def gestione_terreni_page(
    request: Request, db: Session = Depends(get_db), user: User = Depends(get_tech_user)
):
    prenotazioni = (
        db.query(Prenotazione)
        .options(joinedload(Prenotazione.terreno), joinedload(Prenotazione.unita))
        .filter(Prenotazione.status == "PENDING")
        .all()
    )
    return templates.TemplateResponse(
        request, "admin/gestione_terreni.html", {"user": user, "prenotazioni": prenotazioni}
    )


@router.post("/gestione-terreni/approve/{prenotazione_id}")
async def approve_prenotazione(
    prenotazione_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_tech_user),
):
    prenotazione = (
        db.query(Prenotazione)
        .options(joinedload(Prenotazione.terreno), joinedload(Prenotazione.unita))
        .filter(Prenotazione.id == prenotazione_id)
        .first()
    )
    if prenotazione:
        prenotazione.status = "APPROVED"
        db.commit()
        send_reservation_confirmation_email(
            unit_email=prenotazione.unita.email if prenotazione.unita else None,
            unit_name=prenotazione.unita.name if prenotazione.unita else "N/A",
            terrain_name=prenotazione.terreno.name if prenotazione.terreno else "N/A",
            start_time=prenotazione.start_time.strftime("%d/%m %H:%M"),
            end_time=prenotazione.end_time.strftime("%d/%m %H:%M"),
        )
    return RedirectResponse(url="/gestione-terreni", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/gestione-terreni/reject/{prenotazione_id}")
async def reject_prenotazione(
    prenotazione_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_tech_user),
):
    prenotazione = (
        db.query(Prenotazione)
        .options(joinedload(Prenotazione.terreno), joinedload(Prenotazione.unita))
        .filter(Prenotazione.id == prenotazione_id)
        .first()
    )
    if prenotazione:
        prenotazione.status = "REJECTED"
        db.commit()
        send_reservation_rejected_email(
            unit_email=prenotazione.unita.email if prenotazione.unita else None,
            unit_name=prenotazione.unita.name if prenotazione.unita else "N/A",
            terrain_name=prenotazione.terreno.name if prenotazione.terreno else "N/A",
            start_time=prenotazione.start_time.strftime("%d/%m %H:%M"),
            end_time=prenotazione.end_time.strftime("%d/%m %H:%M"),
        )
    return RedirectResponse(url="/gestione-terreni", status_code=status.HTTP_303_SEE_OTHER)


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

    return templates.TemplateResponse(request, "timeline.html", {"completions": unique_completions, "user": user})


# --- API ---
@router.get("/api/terreni/availability")
async def get_terreni_availability(start_date: datetime, end_date: datetime, db: Session = Depends(get_db)):
    """
    Returns list of terrains with their availability status for the given range.
    Status: FREE, PARTIAL, BOOKED
    """
    # Ensure naive datetimes for comparison with SQLite naive storage
    if start_date.tzinfo is not None:
        start_date = start_date.replace(tzinfo=None)
    if end_date.tzinfo is not None:
        end_date = end_date.replace(tzinfo=None)

    terreni = db.query(Terreno).all()
    results = []

    for t in terreni:
        # Find reservations overlapping with the requested range for this terrain
        # Overlap logic: (StartA <= EndB) and (EndA >= StartB)
        reservations = (
            db.query(Prenotazione)
            .filter(
                Prenotazione.terreno_id == t.id,
                Prenotazione.start_time < end_date,
                Prenotazione.end_time > start_date,
            )
            .all()
        )

        status = "FREE"
        if reservations:
            # Check if fully booked or partially
            # Simplification: If any reservation covers the entire requested range (unlikely for broad range)
            # or if reservations cover the *entirety* of the range?
            # User requirement:
            # "free terrain polygons in that slot should appear as green"
            # "partially available ones should appear in yellow"
            # "completely booked one should appear gray"

            # Use total seconds logic or simple overlap check?
            # If the requested range is small (e.g. 1 hour slot), it's binary (Free or Booked).
            # If the requested range is large (e.g. a day), it could be Partial.

            # Let's calculate covered duration
            total_duration = (end_date - start_date).total_seconds()
            covered_duration = 0

            # This is complex because reservations might overlap each other
            # (though DB shouldn't allow it for same terrain)
            # Assuming non-overlapping reservations for same terrain:
            for r in reservations:
                # Intersect reservation [r.start, r.end] with window [start, end]
                overlap_start = max(r.start_time, start_date)
                overlap_end = min(r.end_time, end_date)
                covered_duration += max(0, (overlap_end - overlap_start).total_seconds())

            if covered_duration >= total_duration:
                status = "BOOKED"
            elif covered_duration > 0:
                status = "PARTIAL"

        results.append(
            {
                "id": t.id,
                "name": t.name,
                "tags": t.tags,
                "polygon": t.polygon,
                "center_lat": t.center_lat,
                "center_lon": t.center_lon,
                "description": t.description,
                "image_urls": t.image_urls,
                "status": status,
                "reservations": [
                    {"start": r.start_time.isoformat(), "end": r.end_time.isoformat(), "unit_name": r.unita.name}
                    for r in reservations
                ],
            }
        )

    return results


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
    writer.writerow(["Posizione", "Pattuglia", "Capo Pattuglia", "Unit\u00e0", "Sottocampo", "Punteggio"])

    for index, p in enumerate(pattuglie):
        writer.writerow([index + 1, p.name, p.capo_pattuglia, p.unita.name, p.unita.sottocampo, p.current_score])

    output.seek(0)

    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=classifica_scout.csv"
    return response
