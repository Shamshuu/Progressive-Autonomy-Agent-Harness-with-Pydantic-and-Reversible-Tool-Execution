from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.pending import PendingAction
from app.schemas.api import PendingActionResponse, ApproveResponse
from app.services.action_logger import execute_with_reversible_log
from app.services.trust_engine import increment_trust
from app.services.mutations import MUTATION_REGISTRY

router = APIRouter(prefix="/api/hitl", tags=["Human In The Loop"])


@router.get("/pending", response_model=List[PendingActionResponse])
def get_pending_actions(db: Session = Depends(get_db)):
    """
    Returns an array of paused tool execution intents waiting for human review.
    """
    pending = db.query(PendingAction).filter(PendingAction.status == "PENDING").all()
    return [
        PendingActionResponse(
            intent_id=p.intent_id,
            action_type=p.action_type,
            target_row_id=p.target_row_id,
            reason=p.reason,
            payload=p.payload,
            status=p.status,
            created_at=p.created_at.isoformat() if p.created_at else None
        )
        for p in pending
    ]


@router.post("/approve/{intent_id}", response_model=ApproveResponse, status_code=status.HTTP_200_OK)
def approve_pending_action(
    intent_id: str,
    db: Session = Depends(get_db)
):
    """
    Executes a paused tool intent upon explicit human approval:
    1. Runs mutation with before/after state capture in append-only action_log.
    2. Increments success_count for that action_type in trust_store by 1.
    3. Updates pending_action status to APPROVED.
    """
    pending = db.query(PendingAction).filter(PendingAction.intent_id == intent_id).first()
    if not pending:
        raise HTTPException(status_code=404, detail=f"Pending intent with ID '{intent_id}' not found.")

    if pending.status != "PENDING":
        raise HTTPException(
            status_code=400,
            detail=f"Intent '{intent_id}' is already {pending.status}."
        )

    action_type = pending.action_type
    target_id = pending.target_row_id

    if action_type not in MUTATION_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unsupported action type '{action_type}'.")

    mutation_func = MUTATION_REGISTRY[action_type]

    try:
        # Execute mutation with reversible log
        log_entry = execute_with_reversible_log(
            db_session=db,
            action_type=action_type,
            target_id=target_id,
            mutation_func=mutation_func
        )

        # Increment trust counter
        new_trust_count = increment_trust(db, action_type)

        # Update pending record status
        pending.status = "APPROVED"
        db.commit()

        return ApproveResponse(
            status="success",
            message=f"Action '{action_type}' on item {target_id} approved and executed successfully.",
            action_id=log_entry.action_id,
            action_type=action_type,
            target_id=target_id,
            trust_count=new_trust_count,
            previous_state=log_entry.previous_state,
            new_state=log_entry.new_state
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to execute approved action: {str(e)}")


@router.post("/reject/{intent_id}")
def reject_pending_action(
    intent_id: str,
    db: Session = Depends(get_db)
):
    """
    Rejects a paused tool intent without mutating content_queue or updating trust.
    """
    pending = db.query(PendingAction).filter(PendingAction.intent_id == intent_id).first()
    if not pending:
        raise HTTPException(status_code=404, detail=f"Pending intent with ID '{intent_id}' not found.")

    if pending.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Intent '{intent_id}' is already {pending.status}.")

    pending.status = "REJECTED"
    db.commit()
    return {"status": "success", "message": f"Intent '{intent_id}' rejected."}
