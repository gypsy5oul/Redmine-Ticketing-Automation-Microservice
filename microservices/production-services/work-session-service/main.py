#!/usr/bin/env python3
"""
Work Session Service - Track active work vs waiting time

Port: 8011
Endpoints:
- POST /api/v1/worksession/{ticket_id}/start - Start work session
- POST /api/v1/worksession/{ticket_id}/pause - Pause work session
- POST /api/v1/worksession/{ticket_id}/stop - Stop work session
- GET /api/v1/worksession/ticket/{ticket_id} - Get ticket work sessions
"""

from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from loguru import logger

# Import from shared modules
from shared.core.database import Base, get_db
from shared.core.config import settings
from shared.models import WorkSession

app = FastAPI(title="Work Session Service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health_check():
    return {"service": "work-session-service", "status": "healthy"}

@app.post("/api/v1/worksession/{ticket_id}/start", tags=["WorkSession"])
async def start_session(ticket_id: int, data: dict, db: Session = Depends(get_db)):
    """Start work session"""
    try:
        session = WorkSession(
            ticket_id=ticket_id,
            team_member_id=data.get("team_member_id"),
            session_type="work",
            started_at=datetime.now(timezone.utc),
            status="active"
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        logger.info(f"✅ Work session started for ticket {ticket_id}")
        return {"success": True, "session_id": session.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/worksession/{ticket_id}/pause", tags=["WorkSession"])
async def pause_session(ticket_id: int, db: Session = Depends(get_db)):
    """Pause work session"""
    try:
        session = db.query(WorkSession).filter(
            WorkSession.ticket_id == ticket_id,
            WorkSession.status == "active"
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail="No active session found")

        session.status = "paused"
        db.commit()

        logger.info(f"⏸️ Work session paused for ticket {ticket_id}")
        return {"success": True, "message": "Session paused"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/worksession/{ticket_id}/stop", tags=["WorkSession"])
async def stop_session(ticket_id: int, db: Session = Depends(get_db)):
    """Stop work session"""
    try:
        session = db.query(WorkSession).filter(
            WorkSession.ticket_id == ticket_id,
            WorkSession.status.in_(["active", "paused"])
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail="No active session found")

        session.ended_at = datetime.now(timezone.utc)
        session.status = "completed"

        if session.started_at:
            duration = (session.ended_at - session.started_at).total_seconds() / 60
            session.duration_minutes = int(duration)

        db.commit()

        logger.info(f"✅ Work session stopped for ticket {ticket_id}")
        return {"success": True, "duration_minutes": session.duration_minutes}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/worksession/ticket/{ticket_id}", tags=["WorkSession"])
async def get_sessions(ticket_id: int, db: Session = Depends(get_db)):
    """Get work sessions for ticket"""
    try:
        sessions = db.query(WorkSession).filter(WorkSession.ticket_id == ticket_id).all()

        total_work_minutes = sum(s.duration_minutes for s in sessions if s.duration_minutes)

        return {
            "success": True,
            "count": len(sessions),
            "total_work_minutes": total_work_minutes,
            "sessions": [
                {
                    "id": s.id,
                    "team_member_id": s.team_member_id,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                    "duration_minutes": s.duration_minutes,
                    "status": s.status
                }
                for s in sessions
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.SERVICE_PORT, reload=True)
