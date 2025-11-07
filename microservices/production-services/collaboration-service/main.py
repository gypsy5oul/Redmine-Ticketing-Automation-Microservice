#!/usr/bin/env python3
"""
Collaboration Service - Multi-member ticket collaboration

Port: 8008
Endpoints:
- POST /api/v1/collaboration/{ticket_id}/add - Add collaborator
- DELETE /api/v1/collaboration/{id} - Remove collaborator
- GET /api/v1/collaboration/ticket/{ticket_id} - Get collaborators
"""

from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from loguru import logger

# Import from shared modules
from shared.core.database import Base, get_db
from shared.core.config import settings
from shared.models import TicketCollaboration

app = FastAPI(title="Collaboration Service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health_check():
    return {"service": "collaboration-service", "status": "healthy"}

@app.post("/api/v1/collaboration/{ticket_id}/add", tags=["Collaboration"])
async def add_collaborator(ticket_id: int, data: dict, db: Session = Depends(get_db)):
    """Add collaborator to ticket"""
    try:
        collab = TicketCollaboration(
            ticket_id=ticket_id,
            team_member_id=data.get("team_member_id"),
            role=data.get("role", "secondary"),
            notes=data.get("notes", "")
        )
        db.add(collab)
        db.commit()
        db.refresh(collab)
        
        logger.info(f"✅ Collaborator {data.get('team_member_id')} added to ticket {ticket_id}")
        return {"success": True, "collaboration_id": collab.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/collaboration/{collab_id}", tags=["Collaboration"])
async def remove_collaborator(collab_id: int, db: Session = Depends(get_db)):
    """Remove collaborator"""
    try:
        collab = db.query(TicketCollaboration).filter(TicketCollaboration.id == collab_id).first()
        if not collab:
            raise HTTPException(status_code=404, detail="Collaboration not found")
        
        collab.is_active = False
        collab.left_at = datetime.now(timezone.utc)
        db.commit()
        
        logger.info(f"✅ Collaborator removed: {collab_id}")
        return {"success": True, "message": "Collaborator removed"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/collaboration/ticket/{ticket_id}", tags=["Collaboration"])
async def get_collaborators(ticket_id: int, db: Session = Depends(get_db)):
    """Get ticket collaborators"""
    try:
        collabs = db.query(TicketCollaboration).filter(
            TicketCollaboration.ticket_id == ticket_id,
            TicketCollaboration.is_active == True
        ).all()
        
        return {
            "success": True,
            "count": len(collabs),
            "collaborators": [
                {
                    "id": c.id,
                    "team_member_id": c.team_member_id,
                    "role": c.role,
                    "joined_at": c.joined_at.isoformat() if c.joined_at else None,
                    "time_spent_hours": c.time_spent_hours
                }
                for c in collabs
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.SERVICE_PORT, reload=True)
