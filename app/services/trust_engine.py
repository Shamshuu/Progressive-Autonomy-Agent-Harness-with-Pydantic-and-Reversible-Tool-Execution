from sqlalchemy.orm import Session
from app.models.trust import TrustStore
from app.core.config import settings


def get_or_create_trust_record(db: Session, action_type: str) -> TrustStore:
    record = db.query(TrustStore).filter(TrustStore.action_type == action_type).first()
    if not record:
        record = TrustStore(action_type=action_type, success_count=0)
        db.add(record)
        db.commit()
        db.refresh(record)
    return record


def get_trust_count(db: Session, action_type: str) -> int:
    record = db.query(TrustStore).filter(TrustStore.action_type == action_type).first()
    if not record:
        return 0
    return record.success_count


def is_trusted(db: Session, action_type: str, threshold: int = None) -> bool:
    if threshold is None:
        threshold = settings.TRUST_THRESHOLD
    count = get_trust_count(db, action_type)
    return count >= threshold


def increment_trust(db: Session, action_type: str) -> int:
    record = get_or_create_trust_record(db, action_type)
    record.success_count += 1
    db.commit()
    db.refresh(record)
    return record.success_count


def decrement_trust(db: Session, action_type: str) -> int:
    record = get_or_create_trust_record(db, action_type)
    # Deduct trust on rollback, minimum 0
    record.success_count = max(0, record.success_count - 1)
    db.commit()
    db.refresh(record)
    return record.success_count
