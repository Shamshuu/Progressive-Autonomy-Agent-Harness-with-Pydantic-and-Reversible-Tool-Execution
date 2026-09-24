import uuid
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.queue import ContentQueue, ContentStatus
from app.models.action_log import ActionLog
from app.services.trust_engine import decrement_trust


def restore_from_log(db_session: Session, action_id: str) -> Tuple[bool, Dict[str, Any], str, int]:
    """
    Restores a specific row to its previous state based on the append-only action log.
    Incurs a trust penalty to the associated tool type (Req 10).
    Returns (success, restored_state, action_type, new_trust_count).
    """
    try:
        # 1. Find ActionLog by action_id
        log_entry = db_session.query(ActionLog).filter(ActionLog.action_id == action_id).first()
        if not log_entry:
            raise ValueError(f"ActionLog entry with action_id '{action_id}' not found.")

        if not log_entry.previous_state:
            raise ValueError(f"ActionLog entry '{action_id}' does not contain previous_state data.")

        target_id = log_entry.target_row_id
        action_type = log_entry.action_type
        previous_state = log_entry.previous_state

        # 2. Update content_queue where id = target_id with previous_state values
        item = db_session.query(ContentQueue).filter(ContentQueue.id == target_id).first()
        if not item:
            # If item was somehow hard deleted, re-insert it
            status_val = previous_state.get("status", "PENDING")
            item = ContentQueue(
                id=target_id,
                content_text=previous_state.get("content_text", ""),
                status=ContentStatus(status_val) if hasattr(ContentStatus, status_val) else ContentStatus.PENDING
            )
            db_session.add(item)
        else:
            status_val = previous_state.get("status", item.status)
            if isinstance(status_val, str) and hasattr(ContentStatus, status_val):
                item.status = ContentStatus(status_val)
            item.content_text = previous_state.get("content_text", item.content_text)

        db_session.flush()
        db_session.refresh(item)
        restored_dict = item.to_dict()

        # 3. Decrement trust counter for this action_type (Requirement 10)
        new_trust = decrement_trust(db_session, action_type)

        # 4. Record the rollback event itself in append-only ActionLog
        rollback_log = ActionLog(
            action_id=str(uuid.uuid4()),
            action_type=f"rollback:{action_type}",
            target_row_id=target_id,
            previous_state=log_entry.new_state,
            new_state=restored_dict
        )
        db_session.add(rollback_log)

        # 5. Commit transaction
        db_session.commit()
        return True, restored_dict, action_type, new_trust
    except Exception as e:
        db_session.rollback()
        raise e
