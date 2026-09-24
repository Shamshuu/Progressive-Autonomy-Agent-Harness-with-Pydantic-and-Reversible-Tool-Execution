import os
import sys

# Ensure repository root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, init_db
from app.models.queue import ContentQueue, ContentStatus
from app.models.trust import TrustStore
from app.models.action_log import ActionLog
from app.models.pending import PendingAction


def seed_database():
    print("Initializing database tables...")
    init_db()

    db = SessionLocal()
    try:
        # Clear existing data for fresh seed
        print("Clearing existing data...")
        db.query(ActionLog).delete()
        db.query(PendingAction).delete()
        db.query(ContentQueue).delete()
        db.query(TrustStore).delete()
        db.commit()

        # Seed 10 content queue rows
        sample_posts = [
            ("🚀 Launching our new AI Agent Harness v1.0 today!", ContentStatus.PENDING),
            ("📈 Check out our latest benchmark results on agent reliability.", ContentStatus.PENDING),
            ("⚠️ Maintenance scheduled for tonight at 10 PM UTC.", ContentStatus.POSTED),
            ("🎉 SaaStr 2026 Keynote Announcement - Join us live!", ContentStatus.PENDING),
            ("🐛 Fixed bug in queue scheduler preventing duplicate retries.", ContentStatus.FAILED),
            ("💡 Tip: Always enforce structural guardrails at the API boundary.", ContentStatus.PENDING),
            ("🔥 Breaking news: Progressive Autonomy solves agent vibe-coding risks.", ContentStatus.PENDING),
            ("📊 Quarterly Product Update: 99.99% deterministic state recovery.", ContentStatus.POSTED),
            ("❌ Failed network delivery on webhook notification payload.", ContentStatus.FAILED),
            ("🤖 The future of agent harnesses: reversible tool calls by default.", ContentStatus.PENDING),
        ]

        print(f"Seeding {len(sample_posts)} content queue rows...")
        for i, (text, status) in enumerate(sample_posts, start=1):
            item = ContentQueue(id=i, content_text=text, status=status)
            db.add(item)

        # Initialize trust store with 0 counts
        action_types = ["purge", "mark_posted", "retry", "mark_failed"]
        print(f"Initializing trust store for actions: {action_types} (success_count=0)...")
        for act in action_types:
            record = TrustStore(action_type=act, success_count=0)
            db.add(record)

        db.commit()
        print(" Database successfully seeded with 10 queue items and initial trust counters.")
    except Exception as e:
        db.rollback()
        print(f"❌ Failed to seed database: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
