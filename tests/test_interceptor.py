import pytest
from app.models.queue import ContentQueue, ContentStatus
from app.models.trust import TrustStore
from app.models.pending import PendingAction
from app.schemas.tools import GenericToolIntent
from app.services.interceptor import process_agent_intent


def test_interceptor_untrusted_action_paused(db_session):
    # Trust threshold = 3, initial trust = 0
    intent = GenericToolIntent(
        action_name="purge",
        target_id=1,
        reason="Test purge intent"
    )

    result = process_agent_intent(intent, db_session, threshold=3)

    assert result["status"] == "paused"
    assert result["autonomous"] is False
    assert "Requires human approval" in result["message"]
    assert "intent_id" in result

    # Verify queue was NOT mutated
    item_1 = db_session.query(ContentQueue).filter(ContentQueue.id == 1).first()
    assert item_1.status == ContentStatus.PENDING

    # Verify pending action recorded
    pending = db_session.query(PendingAction).filter(PendingAction.intent_id == result["intent_id"]).first()
    assert pending is not None
    assert pending.action_type == "purge"
    assert pending.target_row_id == 1
    assert pending.status == "PENDING"


def test_interceptor_trusted_action_executes_autonomously(db_session):
    # Set trust count for purge = 3 (threshold = 3)
    trust_record = db_session.query(TrustStore).filter(TrustStore.action_type == "purge").first()
    trust_record.success_count = 3
    db_session.commit()

    intent = GenericToolIntent(
        action_name="purge",
        target_id=1,
        reason="Autonomous purge test"
    )

    result = process_agent_intent(intent, db_session, threshold=3)

    assert result["status"] == "executed"
    assert result["autonomous"] is True
    assert "action_id" in result

    # Verify queue WAS mutated
    item_1 = db_session.query(ContentQueue).filter(ContentQueue.id == 1).first()
    assert item_1.status == ContentStatus.PURGED


def test_interceptor_invalid_target_id_raises_error(db_session):
    intent = GenericToolIntent(
        action_name="purge",
        target_id=99999,
        reason="Invalid target test"
    )

    with pytest.raises(ValueError, match="does not exist"):
        process_agent_intent(intent, db_session, threshold=3)
