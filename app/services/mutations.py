from sqlalchemy.orm import Session
from app.models.queue import ContentQueue, ContentStatus


def apply_purge(target_id: int, db: Session) -> ContentQueue:
    item = db.query(ContentQueue).filter(ContentQueue.id == target_id).first()
    if not item:
        raise ValueError(f"Content queue item with ID {target_id} not found")
    item.status = ContentStatus.PURGED
    db.flush()
    return item


def apply_mark_posted(target_id: int, db: Session) -> ContentQueue:
    item = db.query(ContentQueue).filter(ContentQueue.id == target_id).first()
    if not item:
        raise ValueError(f"Content queue item with ID {target_id} not found")
    item.status = ContentStatus.POSTED
    db.flush()
    return item


def apply_retry(target_id: int, db: Session) -> ContentQueue:
    item = db.query(ContentQueue).filter(ContentQueue.id == target_id).first()
    if not item:
        raise ValueError(f"Content queue item with ID {target_id} not found")
    item.status = ContentStatus.PENDING
    db.flush()
    return item


def apply_mark_failed(target_id: int, db: Session) -> ContentQueue:
    item = db.query(ContentQueue).filter(ContentQueue.id == target_id).first()
    if not item:
        raise ValueError(f"Content queue item with ID {target_id} not found")
    item.status = ContentStatus.FAILED
    db.flush()
    return item


MUTATION_REGISTRY = {
    "purge": apply_purge,
    "mark_posted": apply_mark_posted,
    "retry": apply_retry,
    "mark_failed": apply_mark_failed,
}
