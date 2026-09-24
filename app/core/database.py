from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Generator
from app.core.config import settings

# If DATABASE_URL starts with postgres://, replace with postgresql:// for SQLAlchemy compatibility
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(bind_engine=None):
    from app.models.queue import ContentQueue
    from app.models.trust import TrustStore
    from app.models.action_log import ActionLog
    from app.models.pending import PendingAction
    
    target_engine = bind_engine or engine
    try:
        Base.metadata.create_all(bind=target_engine)
    except Exception as e:
        print(f"Warning: could not initialize database tables: {e}")

