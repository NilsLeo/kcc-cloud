#!/usr/bin/env python3
"""
Utility script to find and migrate orphaned sessions.

An orphaned session is one where:
- Session has jobs (conversion_jobs)
- Session has user_id set (was claimed)
- Files are still stored under the old alias path instead of email path

Usage:
    python migrate_orphaned_sessions.py --dry-run  # Just list orphaned sessions
    python migrate_orphaned_sessions.py --migrate  # Actually migrate them
"""

import sys
import argparse
from datetime import datetime


def find_orphaned_sessions(db):
    """
    Find sessions that have been claimed by users but haven't had their storage migrated.
    """
    from database import Session
    from utils.storage.s3_storage import S3Storage
    from utils.storage_migration import sanitize_email_for_path

    s3 = S3Storage()
    orphaned = []

    # Find all claimed sessions with jobs
    sessions = db.query(Session).filter(
        Session.user_id.isnot(None)
    ).all()

    print(f"\n🔍 Checking {len(sessions)} claimed sessions for orphaned storage...\n")

    for session in sessions:
        if not session.user or not session.user.email:
            continue

        if len(session.conversion_jobs) == 0:
            continue

        # Check if files exist under old alias path
        old_prefix = f"{session.alias}/"
        new_prefix = f"{sanitize_email_for_path(session.user.email)}/"

        old_files = s3.list_objects(prefix=old_prefix)

        if old_files:
            # Files still exist under alias path - this session needs migration
            orphaned.append({
                'session': session,
                'old_alias': session.alias,
                'email': session.user.email,
                'file_count': len(old_files),
                'job_count': len(session.conversion_jobs),
                'claimed_at': session.claimed_at
            })

            print(f"📦 Found orphaned storage:")
            print(f"   Session: {session.session_key}")
            print(f"   Alias: {session.alias} → {sanitize_email_for_path(session.user.email)}")
            print(f"   Email: {session.user.email}")
            print(f"   Jobs: {len(session.conversion_jobs)}")
            print(f"   Files: {len(old_files)}")
            print(f"   Claimed: {session.claimed_at}")
            print()

    return orphaned


def migrate_session(db, session_info, dry_run=True):
    """
    Migrate a single session's storage.
    """
    from utils.storage_migration import migrate_session_storage_paths

    session = session_info['session']
    old_alias = session_info['old_alias']
    email = session_info['email']

    if dry_run:
        print(f"[DRY RUN] Would migrate {session.session_key}")
        return None

    print(f"🚀 Migrating {session.session_key}...")

    try:
        stats = migrate_session_storage_paths(
            session=session,
            old_alias=old_alias,
            user_email=email
        )

        if stats['success']:
            print(f"   ✅ Success! Moved {stats['objects_moved']} objects")
        else:
            print(f"   ⚠️  Completed with {len(stats['errors'])} errors")

        return stats

    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return {'success': False, 'error': str(e)}


def main():
    parser = argparse.ArgumentParser(
        description='Find and migrate orphaned session storage'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Only list orphaned sessions without migrating'
    )
    parser.add_argument(
        '--migrate',
        action='store_true',
        help='Actually perform the migration'
    )
    parser.add_argument(
        '--session',
        type=str,
        help='Migrate only a specific session key'
    )

    args = parser.parse_args()

    if not args.dry_run and not args.migrate:
        parser.print_help()
        print("\n❌ Error: You must specify either --dry-run or --migrate")
        sys.exit(1)

    # Import here to avoid import errors in non-container environments
    from database import get_db_session

    db = get_db_session()

    try:
        print("="*70)
        print("  Orphaned Session Storage Migration Utility")
        print("="*70)

        if args.session:
            # Migrate specific session
            from database import Session
            session = db.query(Session).filter_by(session_key=args.session).first()

            if not session:
                print(f"\n❌ Session not found: {args.session}")
                sys.exit(1)

            if not session.user or not session.user.email:
                print(f"\n❌ Session has no associated user or email")
                sys.exit(1)

            session_info = {
                'session': session,
                'old_alias': session.alias,
                'email': session.user.email,
                'file_count': 0,  # Will be calculated during migration
                'job_count': len(session.conversion_jobs),
                'claimed_at': session.claimed_at
            }

            migrate_session(db, session_info, dry_run=args.dry_run)

        else:
            # Find all orphaned sessions
            orphaned = find_orphaned_sessions(db)

            if not orphaned:
                print("✅ No orphaned sessions found! All storage is properly organized.")
                sys.exit(0)

            print(f"\n📊 Summary: Found {len(orphaned)} session(s) with orphaned storage\n")

            if args.migrate:
                print("🚀 Starting migration...\n")

                total_success = 0
                total_errors = 0
                total_objects = 0

                for session_info in orphaned:
                    stats = migrate_session(db, session_info, dry_run=False)

                    if stats and stats.get('success'):
                        total_success += 1
                        total_objects += stats.get('objects_moved', 0)
                    else:
                        total_errors += 1

                print("\n" + "="*70)
                print("  Migration Complete!")
                print("="*70)
                print(f"  ✅ Successful: {total_success}")
                print(f"  ❌ Errors: {total_errors}")
                print(f"  📦 Total objects moved: {total_objects}")
                print("="*70)

            else:
                print("ℹ️  This was a dry run. Use --migrate to actually perform the migration.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
