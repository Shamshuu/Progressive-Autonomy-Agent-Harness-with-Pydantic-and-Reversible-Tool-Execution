import pytest
from app.models.queue import ContentQueue, ContentStatus
from app.models.trust import TrustStore
from app.models.action_log import ActionLog
from app.services.action_logger import execute_with_reversible_log
from app.services.restoration_engine import restore_from_log
from app.services.mutations import apply_purge, apply_mark_posted, apply_retry


def test_execute_with_reversible_log(db_session):
    # Target item 1 has initial status PENDING
    item_1 = db_session.query(ContentQueue).filter(ContentQueue.id == 1).first()
    assert item_1.status == ContentStatus.PENDING

    # Execute purge mutation with reversible logging
    log_entry = execute_with_reversible_log(
        db_session=db_session,
        action_type="purge",
        target_id=1,
        mutation_func=apply_purge
    )

    assert log_entry is not None
    assert log_entry.action_type == "purge"
    assert log_entry.target_row_id == 1
    assert log_entry.previous_state["status"] == "PENDING"
    assert log_entry.new_state["status"] == "PURGED"

    # Verify queue was mutated
    db_session.refresh(item_1)
    assert item_1.status == ContentStatus.PURGED


def test_restore_from_log_deterministic(db_session):
    # 1. Mutate item 1 from PENDING to PURGED
    log_entry = execute_with_reversible_log(
        db_session=db_session,
        action_type="purge",
        target_id=1,
        mutation_func=apply_purge
    )
    action_id = log_entry.action_id

    item_1 = db_session.query(ContentQueue).filter(ContentQueue.id == 1).first()
    assert item_1.status == ContentStatus.PURGED

    # Set trust count for purge to 2
    trust_record = db_session.query(TrustStore).filter(TrustStore.action_type == "purge").first()
    trust_record.success_count = 2
    db_session.commit()

    # 2. Perform restore from log
    success, restored_state, action_type, new_trust = restore_from_log(db_session, action_id)

    assert success is True
    assert restored_state["id"] == 1
    assert restored_state["status"] == "PENDING"
    assert action_type == "purge"
    # Verify trust penalty (Req 10): 2 - 1 = 1
    assert new_trust == 1

    # Verify content_queue row is restored in database
    db_session.refresh(item_1)
    assert item_1.status == ContentStatus.PENDING


def test_restore_trust_penalty_floors_at_zero(db_session):
    # Mutate item 1
    log_entry = execute_with_reversible_log(
        db_session=db_session,
        action_type="mark_posted",
        target_id=1,
        mutation_func=apply_mark_posted
    )
    action_id = log_entry.action_id

    # Trust count is currently 0
    trust_record = db_session.query(TrustStore).filter(TrustStore.action_type == "mark_posted").first()
    assert trust_record.success_count == 0

    # Restore action
    success, restored_state, action_type, new_trust = restore_from_log(db_session, action_id)
    assert success is True
    assert new_trust == 0  # Should not go below 0


def test_restore_nonexistent_action_raises_error(db_session):
    with pytest.raises(ValueError, match="not found"):
        restore_from_log(db_session, "nonexistent-action-uuid")
