import uuid
from typing import Callable, Any
from sqlalchemy.orm import Session
from app.models.queue import ContentQueue
from app.models.action_log import ActionLog


def execute_with_reversible_log(
    db_session: Session,
    action_type: str,
    target_id: int,
    mutation_func: Callable[[int, Session], Any]
) -> ActionLog:
    """
    Executes a mutation while capturing reversible state.
    Operates inside a database transaction: if logging fails, the mutation fails.
    """
    try:
        # 1. Fetch current state of target_id from content_queue
        item = db_session.query(ContentQueue).filter(ContentQueue.id == target_id).first()
        if not item:
            raise ValueError(f"Content queue item with ID {target_id} not found")

        # 2. Serialize current state to JSON (previous_state)
        previous_state = item.to_dict()

        # 3. Execute mutation_func(target_id, db_session)
        mutation_func(target_id, db_session)

        # 4. Fetch new state of target_id
        db_session.refresh(item)

        # 5. Serialize new state to JSON (new_state)
        new_state = item.to_dict()

        # 6. Insert into ActionLog (append-only)
        log_entry = ActionLog(
            action_id=str(uuid.uuid4()),
            action_type=action_type,
            target_row_id=target_id,
            previous_state=previous_state,
            new_state=new_state
        )
        db_session.add(log_entry)

        # 7. Commit transaction
        db_session.commit()
        db_session.refresh(log_entry)
        return log_entry
    except Exception as e:
        db_session.rollback()
        raise e
