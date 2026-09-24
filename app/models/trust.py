from sqlalchemy import Column, String, Integer
from app.core.database import Base


class TrustStore(Base):
    __tablename__ = "trust_store"

    action_type = Column(String, primary_key=True, index=True)
    success_count = Column(Integer, default=0, nullable=False)

    def to_dict(self):
        return {
            "action_type": self.action_type,
            "success_count": self.success_count,
        }
