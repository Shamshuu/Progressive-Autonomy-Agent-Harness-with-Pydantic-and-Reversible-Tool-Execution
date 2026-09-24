from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum
import enum
from app.core.database import Base


class ContentStatus(str, enum.Enum):
    PENDING = "PENDING"
    POSTED = "POSTED"
    FAILED = "FAILED"
    PURGED = "PURGED"


class ContentQueue(Base):
    __tablename__ = "content_queue"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    content_text = Column(String, nullable=False)
    status = Column(
        SQLEnum(ContentStatus, values_callable=lambda x: [e.value for e in x], native_enum=False),
        nullable=False,
        default=ContentStatus.PENDING
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "content_text": self.content_text,
            "status": self.status.value if isinstance(self.status, ContentStatus) else str(self.status),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
