import uuid
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models.queue import ContentQueue
from app.models.pending import PendingAction
from app.schemas.tools import GenericToolIntent
from app.services.trust_engine import is_trusted, get_trust_count
from app.services.action_logger import execute_with_reversible_log
from app.services.mutations import MUTATION_REGISTRY
from app.core.config import settings


def process_agent_intent(
    intent: GenericToolIntent,
    db_session: Session,
    threshold: int = None
) -> Dict[str, Any]:
    """
    Intercepts LLM tool intents and applies structural progressive autonomy trust logic.
    - If trusted (counter >= threshold): executes via append-only reversible log.
    - If untrusted (counter < threshold): halts execution, records pending approval task.
    """
    if threshold is None:
        threshold = settings.TRUST_THRESHOLD

    action_type = intent.action_name.lower().strip()
    target_id = intent.target_id

    # 1. Validate target_id exists in content_queue
    item = db_session.query(ContentQueue).filter(ContentQueue.id == target_id).first()
    if not item:
        raise ValueError(f"Target queue item with ID {target_id} does not exist.")

    # 2. Check if mutation is supported
    if action_type not in MUTATION_REGISTRY:
        raise ValueError(f"Unsupported tool action '{action_type}'. Valid actions: {list(MUTATION_REGISTRY.keys())}")

    mutation_func = MUTATION_REGISTRY[action_type]

    # 3. Check trust level
    current_trust = get_trust_count(db_session, action_type)
    trusted = is_trusted(db_session, action_type, threshold=threshold)

    if trusted:
        # Autonomous execution
        log_entry = execute_with_reversible_log(
            db_session=db_session,
            action_type=action_type,
            target_id=target_id,
            mutation_func=mutation_func
        )
        return {
            "status": "executed",
            "message": f"Action '{action_type}' executed autonomously (trust level: {current_trust}/{threshold}).",
            "action_type": action_type,
            "target_id": target_id,
            "action_id": log_entry.action_id,
            "autonomous": True,
            "data": {
                "previous_state": log_entry.previous_state,
                "new_state": log_entry.new_state
            }
        }
    else:
        # Untrusted: Pause execution and record pending approval
        pending_record = PendingAction(
            intent_id=str(uuid.uuid4()),
            action_type=action_type,
            target_row_id=target_id,
            reason=intent.reason or f"Automated intent for {action_type}",
            payload={"action_name": action_type, "target_id": target_id, "reason": intent.reason},
            status="PENDING"
        )
        db_session.add(pending_record)
        db_session.commit()
        db_session.refresh(pending_record)

        return {
            "status": "paused",
            "message": "Action paused. Requires human approval.",
            "action_type": action_type,
            "target_id": target_id,
            "intent_id": pending_record.intent_id,
            "autonomous": False,
            "data": {
                "current_trust": current_trust,
                "threshold_required": threshold,
                "pending_intent": pending_record.to_dict()
            }
        }
