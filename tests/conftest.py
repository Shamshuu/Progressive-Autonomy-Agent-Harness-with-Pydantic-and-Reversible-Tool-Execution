import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.main import app
from app.models.queue import ContentQueue, ContentStatus
from app.models.trust import TrustStore
from app.models.action_log import ActionLog
from app.models.pending import PendingAction

from sqlalchemy.pool import StaticPool

# Use an in-memory SQLite database with StaticPool for isolated test execution
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)



@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        # Seed initial content queue
        items = [
            ContentQueue(id=1, content_text="Post 1", status=ContentStatus.PENDING),
            ContentQueue(id=2, content_text="Post 2", status=ContentStatus.POSTED),
            ContentQueue(id=3, content_text="Post 3", status=ContentStatus.FAILED),
            ContentQueue(id=4, content_text="Post 4", status=ContentStatus.PENDING),
        ]
        db.add_all(items)

        # Seed initial trust store
        trusts = [
            TrustStore(action_type="purge", success_count=0),
            TrustStore(action_type="mark_posted", success_count=0),
            TrustStore(action_type="retry", success_count=0),
            TrustStore(action_type="mark_failed", success_count=0),
        ]
        db.add_all(trusts)
        db.commit()

        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
