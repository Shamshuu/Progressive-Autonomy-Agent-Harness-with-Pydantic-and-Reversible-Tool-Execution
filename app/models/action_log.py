import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey
from app.core.database import Base


class ActionLog(Base):
    __tablename__ = "action_log"

    action_id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    action_type = Column(String, nullable=False)
    target_row_id = Column(Integer, ForeignKey("content_queue.id", ondelete="SET NULL"), nullable=True)
    previous_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=True)
    executed_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def to_dict(self):
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "target_row_id": self.target_row_id,
            "previous_state": self.previous_state,
            "new_state": self.new_state,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }
