# 🚀 Instructions to Run and Test Progressive Autonomy Agent Harness

This guide provides end-to-end Git Bash `curl` commands and step-by-step instructions to test every feature of the Progressive Autonomy Agent Harness from start to finish.

---

## 🛠️ Step 0: Start Services & Seed Database

In your Git Bash terminal, start the Docker containers and seed the initial queue items:

```bash
# 1. Start Docker containers (App on :8000, Postgres on :5433)
docker compose up -d

# 2. Seed 10 initial rows and initialize trust counters to 0
python scripts/seed_db.py
```

---

## 🩺 Step 1: Health Check

Verify that the FastAPI application is running and healthy:

```bash
curl -s -X GET http://localhost:8000/health | json_pp
```

**Expected Output:**
```json
{
  "mock_llm_enabled": true,
  "project": "Progressive Autonomy Agent Harness",
  "status": "healthy",
  "trust_threshold": 3
}
```

---

## 📋 Step 2: Inspect Initial Queue & Trust Scores

Check the initial queue items and verify that all trust scores start at `0`:

```bash
# View Content Queue
curl -s -X GET http://localhost:8000/api/system/queue | json_pp

# View Trust Scores (all starting at 0)
curl -s -X GET http://localhost:8000/api/system/trust | json_pp
```

---

## 🛑 Step 3: Trigger an Untrusted Destructive Action (HITL Gating)

Send an agent prompt instructing a `purge` on Item `1`. Since `purge` trust is `0` (`< TRUST_THRESHOLD=3`), the structural guardrail **halts execution**:

```bash
curl -s -X POST http://localhost:8000/api/agent/execute \
  -H "Content-Type: application/json" \
  -d '{"prompt": "The queue item is corrupt. Purge item 1 immediately.", "target_id": 1}' | json_pp
```

**Expected Output (Paused for Human Review):**
```json
{
  "action_type": "purge",
  "autonomous": false,
  "data": {
    "current_trust": 0,
    "pending_intent": {
      "action_type": "purge",
      "intent_id": "YOUR_INTENT_ID",
      "status": "PENDING",
      "target_row_id": 1
    },
    "threshold_required": 3
  },
  "intent_id": "YOUR_INTENT_ID",
  "message": "Action paused. Requires human approval.",
  "status": "paused",
  "target_id": 1
}
```

---

## 🔎 Step 4: List Paused Actions in the HITL Queue

Query the pending queue and extract the `intent_id`:

```bash
# List all paused actions
curl -s -X GET http://localhost:8000/api/hitl/pending | json_pp

# Save the latest intent_id to a bash variable
INTENT_ID_1=$(curl -s -X GET http://localhost:8000/api/hitl/pending | grep -o '"intent_id":"[^"]*' | head -1 | cut -d'"' -f4)
echo "Captured Intent ID: $INTENT_ID_1"
```

---

## ✅ Step 5: Human Approves the Action

Approve the pending intent. This applies the mutation, records the pre/post state snapshot in `action_log`, and increments `success_count` to `1`:

```bash
curl -s -X POST "http://localhost:8000/api/hitl/approve/$INTENT_ID_1" | json_pp
```

**Expected Output:**
```json
{
  "action_id": "ACTION_UUID_1",
  "action_type": "purge",
  "message": "Action 'purge' on item 1 approved and executed successfully.",
  "status": "success",
  "target_id": 1,
  "trust_count": 1
}
```

---

## 🎓 Step 6: Graduate Tool to Full Autonomy ($N = 3$)

Approve 2 more actions to graduate `purge` to autonomous mode:

```bash
# --- Approval 2/3 (Item 2) ---
EXEC_2=$(curl -s -X POST http://localhost:8000/api/agent/execute -H "Content-Type: application/json" -d '{"prompt": "Purge item 2", "target_id": 2}')
INTENT_ID_2=$(echo $EXEC_2 | grep -o '"intent_id":"[^"]*' | cut -d'"' -f4)
curl -s -X POST "http://localhost:8000/api/hitl/approve/$INTENT_ID_2" | json_pp

# --- Approval 3/3 (Item 3) ---
EXEC_3=$(curl -s -X POST http://localhost:8000/api/agent/execute -H "Content-Type: application/json" -d '{"prompt": "Purge item 3", "target_id": 3}')
INTENT_ID_3=$(echo $EXEC_3 | grep -o '"intent_id":"[^"]*' | cut -d'"' -f4)
curl -s -X POST "http://localhost:8000/api/hitl/approve/$INTENT_ID_3" | json_pp

# Verify trust is now 3
curl -s -X GET http://localhost:8000/api/system/trust | json_pp
```

---

## ⚡ Step 7: Test Autonomous Execution (Bypasses HITL)

Now that `success_count >= 3`, executing a `purge` on Item `4` executes **autonomously and immediately**:

```bash
AUTO_RES=$(curl -s -X POST http://localhost:8000/api/agent/execute \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Purge item 4 because it is stale.", "target_id": 4}')

echo $AUTO_RES | json_pp
```

**Expected Output:**
```json
{
  "action_id": "AUTO_ACTION_ID",
  "action_type": "purge",
  "autonomous": true,
  "message": "Action 'purge' executed autonomously (trust level: 3/3).",
  "status": "executed",
  "target_id": 4
}
```

---

## 🔄 Step 8: Deterministic Rollback & Trust Penalty

Reverse the autonomous purge on Item `4`. The harness restores row `4` back to its previous state (`PENDING`) and **penalizes trust** (decrements `success_count` by 1):

```bash
# 1. Extract the action_id from the autonomous execution
ACTION_ID=$(echo $AUTO_RES | grep -o '"action_id":"[^"]*' | cut -d'"' -f4)
echo "Restoring Action ID: $ACTION_ID"

# 2. Call the restore endpoint
curl -s -X POST http://localhost:8000/api/system/restore \
  -H "Content-Type: application/json" \
  -d "{\"action_id\": \"$ACTION_ID\"}" | json_pp
```

**Expected Output:**
```json
{
  "action_id": "AUTO_ACTION_ID",
  "action_type": "purge",
  "message": "State successfully restored for item 4 from action 'AUTO_ACTION_ID'. Trust penalized.",
  "new_trust_count": 2,
  "restored_state": {
    "id": 4,
    "status": "PENDING"
  },
  "status": "success",
  "success": true,
  "target_id": 4
}
```

---

## 📜 Step 9: Verify Queue & Audit Ledger

Verify that Item `4` is back to `PENDING` and view the immutable append-only action log:

```bash
# Check Queue (Item 4 is restored to PENDING)
curl -s -X GET http://localhost:8000/api/system/queue | json_pp

# Check Trust Store (Purge trust dropped back to 2)
curl -s -X GET http://localhost:8000/api/system/trust | json_pp

# View the Append-Only Action Log with previous_state and new_state snapshots
curl -s -X GET http://localhost:8000/api/system/logs | json_pp
```

---

## 🧪 Automated Failure Simulation & Test Suite

You can also run the full automated failure simulation script or pytest suite:

```bash
# Run the automated failure simulation
python scripts/simulate_failure.py

# Run all unit and integration tests
pytest -v tests/
```
