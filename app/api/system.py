from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.queue import ContentQueue
from app.models.trust import TrustStore
from app.models.action_log import ActionLog
from app.schemas.api import (
    RestoreRequest,
    RestoreResponse,
    ContentQueueItem,
    TrustStoreItem,
    ActionLogItem,
)
from app.services.restoration_engine import restore_from_log

router = APIRouter(prefix="/api/system", tags=["System & State Restoration"])


@router.post("/restore", response_model=RestoreResponse)
def restore_action_state(
    request: RestoreRequest,
    db: Session = Depends(get_db)
):
    """
    Deterministically reverses an action using the previous_state snapshot in action_log.
    Incurs a trust penalty to the associated tool type (decrements success_count by 1).
    """
    try:
        success, restored_state, action_type, new_trust = restore_from_log(db, request.action_id)
        target_id = restored_state.get("id")
        return RestoreResponse(
            status="success",
            success=success,
            message=f"State successfully restored for item {target_id} from action '{request.action_id}'. Trust penalized.",
            action_id=request.action_id,
            action_type=action_type,
            target_id=target_id,
            restored_state=restored_state,
            new_trust_count=new_trust
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rollback failed: {str(e)}")


@router.get("/queue", response_model=List[ContentQueueItem])
def get_queue(db: Session = Depends(get_db)):
    """
    Returns all items in content_queue.
    """
    items = db.query(ContentQueue).order_by(ContentQueue.id.asc()).all()
    return [
        ContentQueueItem(
            id=item.id,
            content_text=item.content_text,
            status=item.status.value if hasattr(item.status, "value") else str(item.status),
            created_at=item.created_at.isoformat() if item.created_at else None,
            updated_at=item.updated_at.isoformat() if item.updated_at else None
        )
        for item in items
    ]


@router.get("/trust", response_model=List[TrustStoreItem])
def get_trust_scores(db: Session = Depends(get_db)):
    """
    Returns trust counters for all tool types.
    """
    records = db.query(TrustStore).all()
    return [
        TrustStoreItem(
            action_type=r.action_type,
            success_count=r.success_count
        )
        for r in records
    ]


@router.get("/logs", response_model=List[ActionLogItem])
def get_action_logs(db: Session = Depends(get_db)):
    """
    Returns the append-only action log ledger.
    """
    logs = db.query(ActionLog).order_by(ActionLog.executed_at.desc()).all()
    return [
        ActionLogItem(
            action_id=log.action_id,
            action_type=log.action_type,
            target_row_id=log.target_row_id,
            previous_state=log.previous_state,
            new_state=log.new_state,
            executed_at=log.executed_at.isoformat() if log.executed_at else None
        )
        for log in logs
    ]
