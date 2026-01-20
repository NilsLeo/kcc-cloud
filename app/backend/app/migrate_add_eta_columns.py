#!/usr/bin/env python3
"""
Database migration script to add ETA tracking columns.
"""

import sqlite3
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/jobs.db")
# Extract path from SQLAlchemy URL
db_path = DATABASE_URL.replace("sqlite:///", "")

print(f"Connecting to database: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(conversion_jobs)")
    columns = [col[1] for col in cursor.fetchall()]

    if "processing_started_at" not in columns:
        print("Adding processing_started_at column...")
        cursor.execute("ALTER TABLE conversion_jobs ADD COLUMN processing_started_at DATETIME")
        print("✓ Added processing_started_at column")
    else:
        print("✓ processing_started_at column already exists")

    if "estimated_duration_seconds" not in columns:
        print("Adding estimated_duration_seconds column...")
        cursor.execute("ALTER TABLE conversion_jobs ADD COLUMN estimated_duration_seconds INTEGER")
        print("✓ Added estimated_duration_seconds column")
    else:
        print("✓ estimated_duration_seconds column already exists")

    conn.commit()
    conn.close()

    print("\n✅ Migration completed successfully!")

except Exception as e:
    print(f"\n❌ Migration failed: {e}")
    raise
