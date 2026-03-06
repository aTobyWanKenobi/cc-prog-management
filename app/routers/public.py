import csv
import io
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from app.auth import get_authenticated_user, get_tech_user
from app.database import get_db
from app.email_service import (
    send_reservation_approved_email,
    send_reservation_rejected_email,
    send_reservation_requested_email,
    send_support_email,
)
from app.models import Challenge, Completion, Pattuglia, Prenotazione, Terreno, Unita, User

router = APIRouter(
    dependencies=[Depends(get_authenticated_user)]  # All public routes require at least being logged in
)

templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def ranking_page(
    request: Request,
    sottocampo_filter: str | None = None,
    tipo_filter: str | None = "Reparto",
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
):
    if user.role == "unit" and user.unita and user.unita.tipo == "Posto":
        return RedirectResponse(url="/prenotazioni", status_code=status.HTTP_303_SEE_OTHER)

    query = db.query(Pattuglia).join(Unita).filter(Unita.tipo == "Reparto").options(joinedload(Pattuglia.unita))

    # Filter logic for Sottocampo
    if sottocampo_filter and sottocampo_filter.strip():
        query = query.filter(Unita.sottocampo == sottocampo_filter)
    else:
        sottocampo_filter = None

    # Filter logic for Tipo
    if tipo_filter and tipo_filter.strip():
        query = query.filter(Unita.tipo == tipo_filter)
    else:
        tipo_filter = None

    # Sort by score desc
    pattuglie = query.order_by(Pattuglia.current_score.desc()).all()

    # Calculate rank
    for index, p in enumerate(pattuglie):
        p.rank = index + 1

    all_unita = db.query(Unita).order_by(Unita.name).all()

    # Get unique sottocampi
    sottocampi = sorted(list(set(u.sottocampo for u in all_unita if u.sottocampo)))

    # Get unique tipi
    tipi_unita = sorted(list(set(u.tipo for u in all_unita if u.tipo)))

    return templates.TemplateResponse(
        request,
        "ranking.html",
        {
            "pattuglie": pattuglie,
            "unita": all_unita,
            "sottocampi": sottocampi,
            "tipi_unita": tipi_unita,
            "current_sottocampo_filter": sottocampo_filter,
            "current_tipo_filter": tipo_filter,
            "user": user,
        },
    )


@router.get("/prenotazioni", response_class=HTMLResponse)
async def prenotazioni_page(
    request: Request, db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)
):
    user_reservations = []
    if user.role == "unit" and user.unita_id:
        user_reservations = (
            db.query(Prenotazione)
            .options(joinedload(Prenotazione.terreno))
            .filter(Prenotazione.unita_id == user.unita_id)
            .order_by(Prenotazione.start_time)
            .all()
        )
    elif user.role in ["tech", "admin"]:
        # Tech/admin see all reservations
        user_reservations = (
            db.query(Prenotazione)
            .options(joinedload(Prenotazione.terreno), joinedload(Prenotazione.unita))
            .order_by(Prenotazione.start_time)
            .all()
        )

    return templates.TemplateResponse(
        request, "prenotazioni.html", {"user": user, "user_reservations": user_reservations}
    )


@router.post("/prenotazioni/cancel/{prenotazione_id}")
async def cancel_prenotazione(
    prenotazione_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
):
    prenotazione = db.query(Prenotazione).filter(Prenotazione.id == prenotazione_id).first()
    if not prenotazione:
        raise HTTPException(status_code=404, detail="Prenotazione non trovata")

    # Units can only cancel their own PENDING reservations
    if user.role == "unit" and (prenotazione.unita_id != user.unita_id or prenotazione.status != "PENDING"):
        raise HTTPException(status_code=403, detail="Non puoi annullare questa prenotazione")

    prenotazione.status = "CANCELLED"
    db.commit()
    return RedirectResponse(url="/prenotazioni", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/prenotazioni")
async def create_prenotazione(
    terreno_id: int = Form(...),
    start_date: str = Form(...),
    start_hour: int = Form(...),
    duration: int = Form(...),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
):
    if user.role != "unit" or not user.unita_id:
        raise HTTPException(status_code=403, detail="Solo le unità possono prenotare terreni.")

    terreno = db.query(Terreno).filter(Terreno.id == terreno_id).first()
    if not terreno:
        raise HTTPException(status_code=404, detail="Terreno non trovato.")

    tipo_unita = user.unita.tipo.lower() if user.unita else None
    if tipo_unita and terreno.tipo_accesso != "entrambi" and terreno.tipo_accesso != tipo_unita:
        raise HTTPException(
            status_code=403, detail=f"Questo terreno non è disponibile per la tua branca ({tipo_unita.capitalize()})."
        )

    if start_hour < 7 or start_hour + duration > 25:
        raise HTTPException(status_code=400, detail="Prenotazioni permesse solo tra le 07:00 e le 01:00.")

    if duration < 1 or duration > 4:
        raise HTTPException(status_code=400, detail="Durata deve essere tra 1 e 4 ore.")

    try:
        if start_hour == 24:
            base_date = datetime.strptime(start_date, "%Y-%m-%d")
            start_time = base_date + timedelta(days=1)
        else:
            start_time = datetime.strptime(f"{start_date} {start_hour:02d}:00", "%Y-%m-%d %H:00")
    except ValueError:
        raise HTTPException(status_code=400, detail="Data o ora non valida.") from None

    end_time = start_time + timedelta(hours=duration)

    # Check for overlapping reservations on the same terrain
    overlap = (
        db.query(Prenotazione)
        .filter(
            Prenotazione.terreno_id == terreno_id,
            Prenotazione.status == "APPROVED",
            Prenotazione.start_time < end_time,
            Prenotazione.end_time > start_time,
        )
        .first()
    )

    if overlap:
        return RedirectResponse(url="/prenotazioni?error=overlap", status_code=status.HTTP_303_SEE_OTHER)

    new_prenotazione = Prenotazione(
        terreno_id=terreno_id,
        unita_id=user.unita_id,
        start_time=start_time,
        end_time=end_time,
        duration=duration,
        notes=notes,
        status="PENDING",
    )
    db.add(new_prenotazione)
    db.commit()

    # Send email notification
    terreno = db.query(Terreno).filter(Terreno.id == terreno_id).first()
    unita = db.query(Unita).filter(Unita.id == user.unita_id).first()
    if terreno and unita:
        send_reservation_requested_email(
            unit_email=unita.email,
            unit_name=unita.name,
            terrain_name=terreno.name,
            start_time=start_time.strftime("%d/%m %H:%M"),
            end_time=end_time.strftime("%d/%m %H:%M"),
        )

    return RedirectResponse(url="/prenotazioni?success=1", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/prenotazioni/update-notes/{prenotazione_id}")
async def update_prenotazione_notes(
    prenotazione_id: int,
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
):
    prenotazione = db.query(Prenotazione).filter(Prenotazione.id == prenotazione_id).first()
    if not prenotazione:
        raise HTTPException(status_code=404, detail="Prenotazione non trovata")

    # Only owner or admin/tech can edit notes
    if user.role == "unit" and prenotazione.unita_id != user.unita_id:
        raise HTTPException(status_code=403, detail="Non sei autorizzato a modificare queste note.")

    prenotazione.notes = notes
    db.commit()
    return RedirectResponse(url="/prenotazioni?success=notes_updated", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/input", response_class=HTMLResponse)
async def input_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_tech_user)):
    pattuglie = db.query(Pattuglia).join(Unita).filter(Unita.tipo == "Reparto").order_by(Pattuglia.name).all()
    challenges = db.query(Challenge).order_by(Challenge.name).all()
    return templates.TemplateResponse(
        request, "input.html", {"pattuglie": pattuglie, "challenges": challenges, "user": user}
    )


@router.get("/gestione-terreni", response_class=HTMLResponse)
async def gestione_terreni_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_tech_user)):
    pending = (
        db.query(Prenotazione)
        .options(joinedload(Prenotazione.terreno), joinedload(Prenotazione.unita))
        .filter(Prenotazione.status == "PENDING")
        .order_by(Prenotazione.start_time)
        .all()
    )
    approved = (
        db.query(Prenotazione)
        .options(joinedload(Prenotazione.terreno), joinedload(Prenotazione.unita))
        .filter(Prenotazione.status == "APPROVED")
        .order_by(Prenotazione.start_time.desc())
        .limit(20)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "gestione_terreni.html",
        {"user": user, "pending": pending, "approved": approved},
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

        # Reject overlapping PENDING reservations
        overlapping = (
            db.query(Prenotazione)
            .filter(
                Prenotazione.terreno_id == prenotazione.terreno_id,
                Prenotazione.id != prenotazione.id,
                Prenotazione.status == "PENDING",
                Prenotazione.start_time < prenotazione.end_time,
                Prenotazione.end_time > prenotazione.start_time,
            )
            .all()
        )

        for overlap in overlapping:
            overlap.status = "REJECTED"

        db.commit()
        send_reservation_approved_email(
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

    # Validate Posto
    pattuglia = db.query(Pattuglia).options(joinedload(Pattuglia.unita)).filter(Pattuglia.id == pattuglia_id).first()
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()

    if not pattuglia or not challenge:
        return RedirectResponse(url="/input?error=not_found", status_code=status.HTTP_303_SEE_OTHER)

    if pattuglia.unita.tipo == "Posto":
        return RedirectResponse(url="/input?error=invalid_unit_type", status_code=status.HTTP_303_SEE_OTHER)

    # Register completion
    new_completion = Completion(pattuglia_id=pattuglia_id, challenge_id=challenge_id)
    db.add(new_completion)

    # Update score
    pattuglia.current_score += challenge.points
    db.commit()

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/timeline", response_class=HTMLResponse)
async def timeline_page(request: Request, db: Session = Depends(get_db), user: User = Depends(get_authenticated_user)):
    if user.role == "unit" and user.unita and user.unita.tipo == "Posto":
        return RedirectResponse(url="/prenotazioni", status_code=status.HTTP_303_SEE_OTHER)

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
async def get_terreni_availability(
    start_date: datetime,
    end_date: datetime,
    db: Session = Depends(get_db),
    user: User = Depends(get_authenticated_user),
):
    """
    Returns list of terrains with their availability status for the given range.
    Status: FREE, PARTIAL, BOOKED
    """
    # Ensure naive datetimes for comparison with SQLite naive storage
    if start_date.tzinfo is not None:
        start_date = start_date.replace(tzinfo=None)
    if end_date.tzinfo is not None:
        end_date = end_date.replace(tzinfo=None)

    terreni_query = db.query(Terreno)

    tipo_unita = None
    if user.role == "unit" and user.unita:
        tipo_unita = user.unita.tipo.lower()

    if tipo_unita:
        terreni_query = terreni_query.filter(Terreno.tipo_accesso.in_(["entrambi", tipo_unita]))

    terreni = terreni_query.all()
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
            approved_covered = 0
            pending_covered = 0

            for r in reservations:
                overlap_start = max(r.start_time, start_date)
                overlap_end = min(r.end_time, end_date)
                dur = max(0, (overlap_end - overlap_start).total_seconds())
                if getattr(r, "status", "APPROVED") == "APPROVED":
                    approved_covered += dur
                elif getattr(r, "status", "") == "PENDING":
                    pending_covered += dur

            if approved_covered >= total_duration:
                status = "BOOKED"
            elif approved_covered > 0 or pending_covered > 0:
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
                    {
                        "id": r.id,
                        "start": r.start_time.isoformat(),
                        "end": r.end_time.isoformat(),
                        "unit_name": r.unita.name,
                        "notes": r.notes if (user.role in ["admin", "tech"] or user.unita_id == r.unita_id) else "",
                    }
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

    pattuglie = (
        db.query(Pattuglia)
        .join(Unita)
        .filter(Unita.tipo == "Reparto")
        .options(joinedload(Pattuglia.unita))
        .order_by(Pattuglia.current_score.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Posizione", "Pattuglia", "Capo Pattuglia", "Unità", "Sottocampo", "Punteggio"])

    for index, p in enumerate(pattuglie):
        writer.writerow([index + 1, p.name, p.capo_pattuglia, p.unita.name, p.unita.sottocampo, p.current_score])

    output.seek(0)

    # Explicitly convert to bytes to avoid encoding issues in streaming
    csv_data = output.getvalue()
    response = StreamingResponse(io.BytesIO(csv_data.encode("utf-8")), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=classifica_scout.csv"
    return response


@router.get("/supporto", response_class=HTMLResponse)
async def supporto_page(request: Request, user: User = Depends(get_authenticated_user)):
    """Render the support contact form."""
    return templates.TemplateResponse(request, "support.html", {"user": user})


@router.post("/supporto", response_class=HTMLResponse)
async def post_supporto(
    request: Request,
    subject: str = Form(...),
    message: str = Form(...),
    user: User = Depends(get_authenticated_user),
):
    """Handle support form submission."""
    try:
        user_name = user.unita.name if user.unita else user.username
        role = user.role
        email = user.email if user.email else (user.unita.email if hasattr(user, "unita") and user.unita else None)
        send_support_email(user_email=email, user_name=user_name, subject=subject, message=message, role=role)
        return templates.TemplateResponse(request, "support.html", {"user": user, "success": True})
    except Exception as e:
        return templates.TemplateResponse(
            request, "support.html", {"user": user, "error": f"Errore durante l'invio: {str(e)}"}
        )
