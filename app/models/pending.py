import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, JSON
from app.core.database import Base


class PendingAction(Base):
    __tablename__ = "pending_actions"

    intent_id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    action_type = Column(String, nullable=False)
    target_row_id = Column(Integer, nullable=False)
    reason = Column(String, nullable=True)
    payload = Column(JSON, nullable=True)
    status = Column(String, default="PENDING", nullable=False)  # PENDING, APPROVED, REJECTED
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def to_dict(self):
        return {
            "intent_id": self.intent_id,
            "action_type": self.action_type,
            "target_row_id": self.target_row_id,
            "reason": self.reason,
            "payload": self.payload,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
