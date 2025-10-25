"""Database initialization and utilities"""
import aiosqlite
import os
from pathlib import Path
from app.config import settings


# Database schema
SCHEMA = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    agent_type TEXT NOT NULL,
    status TEXT NOT NULL,
    input_data TEXT NOT NULL,
    output_data TEXT,
    estimated_cost REAL NOT NULL,
    actual_cost REAL,
    payment_status TEXT,
    payment_tx_hash TEXT,
    payment_auth_req_id TEXT,
    ciba_request_id TEXT,
    progress_message TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    started_at TEXT,
    completed_at TEXT,
    paid_at TEXT,
    metadata TEXT
);

CREATE INDEX IF NOT EXISTS idx_user_id ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_created_at ON tasks(created_at);

-- Task results table
CREATE TABLE IF NOT EXISTS task_results (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id),
    result_type TEXT,
    content TEXT,
    storage_path TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_task_id_results ON task_results(task_id);

-- CIBA requests table
CREATE TABLE IF NOT EXISTS ciba_requests (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id),
    user_id TEXT NOT NULL,
    auth_req_id TEXT,
    status TEXT NOT NULL,
    amount REAL NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    expires_at TEXT,
    approved_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_auth_req_id ON ciba_requests(auth_req_id);
CREATE INDEX IF NOT EXISTS idx_task_id_ciba ON ciba_requests(task_id);

-- Magic Link Approvals table (for email-based payment approval)
CREATE TABLE IF NOT EXISTS magic_link_approvals (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id),
    user_id TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    amount REAL NOT NULL,
    task_description TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL,
    approved_at TEXT,
    denied_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_token ON magic_link_approvals(token);
CREATE INDEX IF NOT EXISTS idx_task_id_magic ON magic_link_approvals(task_id);
CREATE INDEX IF NOT EXISTS idx_status_magic ON magic_link_approvals(status);
"""


async def init_db():
    """Initialize database with schema"""
    # Ensure data directory exists
    db_path = Path(settings.DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create tables
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        await db.executescript(SCHEMA)

        # Migration: Add ciba_request_id and progress_message columns if they don't exist
        try:
            # Check if columns exist
            cursor = await db.execute("PRAGMA table_info(tasks)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]

            if 'ciba_request_id' not in column_names:
                await db.execute("ALTER TABLE tasks ADD COLUMN ciba_request_id TEXT")
                print("✅ Added ciba_request_id column to tasks table")

            if 'progress_message' not in column_names:
                await db.execute("ALTER TABLE tasks ADD COLUMN progress_message TEXT")
                print("✅ Added progress_message column to tasks table")
        except Exception as e:
            print(f"⚠️  Migration warning: {e}")

        await db.commit()

    print(f"✅ Database initialized at {settings.DATABASE_PATH}")


async def get_db():
    """Get database connection (context manager)"""
    async with aiosqlite.connect(settings.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row  # Return rows as dict-like objects
        yield db


async def check_db_health() -> bool:
    """Check if database is healthy"""
    try:
        async with aiosqlite.connect(settings.DATABASE_PATH) as db:
            cursor = await db.execute("SELECT 1")
            await cursor.fetchone()
        return True
    except Exception as e:
        print(f"❌ Database health check failed: {e}")
        return False
