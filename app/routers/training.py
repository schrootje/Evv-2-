from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel

from app.database import get_db
from app.models.training import Player, TrainingSession, Attendance

router = APIRouter(prefix="/training", tags=["Training"])
templates = Jinja2Templates(directory="app/templates")


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class PlayerCreate(BaseModel):
    name: str
    number: Optional[int] = None


class SessionCreate(BaseModel):
    date: str  # ISO format: YYYY-MM-DD
    location: Optional[str] = None
    notes: Optional[str] = None


class AttendanceUpdate(BaseModel):
    present: bool
    note: Optional[str] = None


# ── HTML views ────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    sessions = (
        db.query(TrainingSession)
        .options(joinedload(TrainingSession.attendances).joinedload(Attendance.player))
        .order_by(TrainingSession.date.desc())
        .all()
    )
    players = db.query(Player).filter(Player.active == True).order_by(Player.name).all()
    return templates.TemplateResponse(
        "training/dashboard.html",
        {"request": request, "sessions": sessions, "players": players},
    )


@router.get("/sessie/{session_id}", response_class=HTMLResponse)
def session_detail(session_id: int, request: Request, db: Session = Depends(get_db)):
    session = (
        db.query(TrainingSession)
        .options(joinedload(TrainingSession.attendances).joinedload(Attendance.player))
        .filter(TrainingSession.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sessie niet gevonden")

    players = db.query(Player).filter(Player.active == True).order_by(Player.name).all()

    # Build lookup: player_id -> attendance
    attendance_map = {a.player_id: a for a in session.attendances}

    # Ensure every active player has an attendance record
    for player in players:
        if player.id not in attendance_map:
            att = Attendance(session_id=session.id, player_id=player.id, present=False)
            db.add(att)
    db.commit()
    db.refresh(session)

    attendance_map = {a.player_id: a for a in session.attendances}
    present_count = sum(1 for a in session.attendances if a.present)
    absent_count = len(players) - present_count

    return templates.TemplateResponse(
        "training/session.html",
        {
            "request": request,
            "session": session,
            "players": players,
            "attendance_map": attendance_map,
            "present_count": present_count,
            "absent_count": absent_count,
        },
    )


# ── Form handlers (HTML form posts) ──────────────────────────────────────────

@router.post("/speler/toevoegen")
def add_player(
    name: str = Form(...),
    number: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    num = int(number) if number and number.strip() else None
    player = Player(name=name.strip(), number=num)
    db.add(player)
    db.commit()
    return RedirectResponse(url="/training/", status_code=303)


@router.post("/speler/{player_id}/verwijder")
def delete_player(player_id: int, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Speler niet gevonden")
    player.active = False
    db.commit()
    return RedirectResponse(url="/training/", status_code=303)


@router.post("/sessie/aanmaken")
def create_session(
    date: str = Form(...),
    location: str = Form(""),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    dt = datetime.strptime(date, "%Y-%m-%d")
    session = TrainingSession(
        date=dt,
        location=location.strip() or None,
        notes=notes.strip() or None,
    )
    db.add(session)
    db.commit()

    # Pre-create attendance rows for all active players
    players = db.query(Player).filter(Player.active == True).all()
    for player in players:
        att = Attendance(session_id=session.id, player_id=player.id, present=False)
        db.add(att)
    db.commit()

    return RedirectResponse(url=f"/training/sessie/{session.id}", status_code=303)


@router.post("/sessie/{session_id}/verwijder")
def delete_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(TrainingSession).filter(TrainingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sessie niet gevonden")
    db.delete(session)
    db.commit()
    return RedirectResponse(url="/training/", status_code=303)


@router.post("/sessie/{session_id}/aanwezigheid")
def save_attendance(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    # Will be handled via JSON API below; this endpoint for future form use
    return RedirectResponse(url=f"/training/sessie/{session_id}", status_code=303)


# ── JSON API ──────────────────────────────────────────────────────────────────

@router.post("/api/aanwezigheid/{attendance_id}")
def toggle_attendance(attendance_id: int, body: AttendanceUpdate, db: Session = Depends(get_db)):
    att = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="Aanwezigheid record niet gevonden")
    att.present = body.present
    att.note = body.note
    db.commit()
    return {"id": att.id, "present": att.present}


@router.get("/api/sessies")
def list_sessions(db: Session = Depends(get_db)):
    sessions = db.query(TrainingSession).order_by(TrainingSession.date.desc()).all()
    return [
        {
            "id": s.id,
            "date": s.date.strftime("%Y-%m-%d"),
            "location": s.location,
            "notes": s.notes,
        }
        for s in sessions
    ]


@router.get("/api/spelers")
def list_players(db: Session = Depends(get_db)):
    players = db.query(Player).filter(Player.active == True).order_by(Player.name).all()
    return [{"id": p.id, "name": p.name, "number": p.number} for p in players]


@router.get("/api/statistieken/{player_id}")
def player_stats(player_id: int, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Speler niet gevonden")
    total = db.query(Attendance).filter(Attendance.player_id == player_id).count()
    present = db.query(Attendance).filter(
        Attendance.player_id == player_id, Attendance.present == True
    ).count()
    return {
        "player": player.name,
        "total_sessions": total,
        "present": present,
        "absent": total - present,
        "percentage": round((present / total * 100) if total else 0, 1),
    }
