import pytest
from app.models.queue import ContentQueue, ContentStatus
from app.models.trust import TrustStore


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "trust_threshold" in data


def test_agent_execute_untrusted_flow(client, db_session):
    # Execute untrusted purge on row 1
    response = client.post("/api/agent/execute", json={
        "prompt": "Please purge queue item 1",
        "target_id": 1
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "paused"
    assert data["autonomous"] is False
    assert data["intent_id"] is not None

    # Verify queue not modified
    item = db_session.query(ContentQueue).filter(ContentQueue.id == 1).first()
    assert item.status == ContentStatus.PENDING


def test_hitl_pending_and_approve_flow(client, db_session):
    # 1. Trigger untrusted action
    exec_resp = client.post("/api/agent/execute", json={
        "prompt": "Mark item 1 as posted",
        "target_id": 1
    })
    intent_id = exec_resp.json()["intent_id"]

    # 2. List pending
    pending_resp = client.get("/api/hitl/pending")
    assert pending_resp.status_code == 200
    pending_list = pending_resp.json()
    assert any(p["intent_id"] == intent_id for p in pending_list)

    # 3. Approve action
    app_resp = client.post(f"/api/hitl/approve/{intent_id}")
    assert app_resp.status_code == 200
    app_data = app_resp.json()
    assert app_data["status"] == "success"
    assert app_data["trust_count"] == 1
    action_id = app_data["action_id"]

    # 4. Verify item updated to POSTED
    item = db_session.query(ContentQueue).filter(ContentQueue.id == 1).first()
    assert item.status == ContentStatus.POSTED

    # 5. Restore action via API (POST /api/system/restore)
    restore_resp = client.post("/api/system/restore", json={"action_id": action_id})
    assert restore_resp.status_code == 200
    rest_data = restore_resp.json()
    assert rest_data["status"] == "success"
    assert rest_data["restored_state"]["status"] == "PENDING"
    assert rest_data["new_trust_count"] == 0

    # 6. Verify item restored in DB
    db_session.refresh(item)
    assert item.status == ContentStatus.PENDING


def test_autonomous_execution_at_trust_threshold(client, db_session):
    # Set trust for retry to 3
    trust_record = db_session.query(TrustStore).filter(TrustStore.action_type == "retry").first()
    trust_record.success_count = 3
    db_session.commit()

    # Item 3 is initially FAILED
    item_3 = db_session.query(ContentQueue).filter(ContentQueue.id == 3).first()
    assert item_3.status == ContentStatus.FAILED

    # Trigger agent retry on item 3
    exec_resp = client.post("/api/agent/execute", json={
        "prompt": "Retry item 3",
        "target_id": 3
    })
    assert exec_resp.status_code == 200
    data = exec_resp.json()
    assert data["status"] == "executed"
    assert data["autonomous"] is True

    # Item 3 is now PENDING
    db_session.refresh(item_3)
    assert item_3.status == ContentStatus.PENDING


def test_get_queue_and_trust_endpoints(client):
    q_resp = client.get("/api/system/queue")
    assert q_resp.status_code == 200
    assert len(q_resp.json()) == 4

    t_resp = client.get("/api/system/trust")
    assert t_resp.status_code == 200
    assert len(t_resp.json()) >= 4
