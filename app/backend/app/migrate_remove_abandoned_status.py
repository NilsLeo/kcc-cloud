#!/usr/bin/env python3
"""
Migration: Remove legacy ABANDONED status and column.

Actions:
- Update any rows with status='ABANDONED' to status='CANCELLED'.
- Drop column 'abandoned_at' from 'conversion_jobs' if it exists.

Notes:
- Requires SQLite 3.35+ for ALTER TABLE DROP COLUMN. If unavailable,
  the script will report the error so you can run a manual recreate.
"""

import os
import sqlite3

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/jobs.db")
DB_PATH = DATABASE_URL.replace("sqlite:///", "")


def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def main():
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        # 1) Normalize legacy status values
        print("Updating legacy ABANDONED statuses to CANCELLED (if any)...")
        cur.execute("UPDATE conversion_jobs SET status='CANCELLED' WHERE status='ABANDONED'")
        print(f"✓ Rows updated: {conn.total_changes}")

        # 2) Drop abandoned_at column if present
        if column_exists(cur, "conversion_jobs", "abandoned_at"):
            print("Dropping column abandoned_at from conversion_jobs...")
            try:
                cur.execute("ALTER TABLE conversion_jobs DROP COLUMN abandoned_at")
                print("✓ Dropped abandoned_at column")
            except Exception as e:
                print("❌ ALTER TABLE DROP COLUMN failed. Your SQLite may be too old.")
                print("   Error:", e)
                print(
                    "\nWorkaround: Recreate table without abandoned_at. "
                    "Run these steps manually if needed:"
                )
                print("  - Create new table without the column, copy data, drop old, rename new.")
                raise
        else:
            print("✓ Column abandoned_at not present — nothing to drop")

        conn.commit()
        print("\n✅ Migration completed successfully!")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
