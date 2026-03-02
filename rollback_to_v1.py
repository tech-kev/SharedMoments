#!/usr/bin/env python3
"""Rollback script: removes all v2 migration data so migration can run fresh.

Usage:
    python rollback_to_v1.py [--force]

This script deletes:
1. The v2 SQLite database
2. All files in v2 upload directories (images, videos, music, profiles, thumbs)
3. The migration status and data files

The v1 data is untouched (read-only mount). After rollback, restart the app
with MIGRATION_V1_* env vars to re-run the migration.
"""
import argparse
import os
import shutil
import sys

BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'app'))
DB_PATH = os.path.join(BASEDIR, 'database', 'sharedmomentsv2.db')
MIGRATION_DATA_DIR = os.path.join(BASEDIR, 'migration_data')
UPLOADS_DIR = os.path.join(BASEDIR, 'uploads')

UPLOAD_SUBFOLDERS = ('images', 'videos', 'music', 'profiles', 'thumbs')


def main():
    parser = argparse.ArgumentParser(description='Rollback SharedMoments v2 migration')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')
    args = parser.parse_args()

    print('SharedMoments v2 Migration Rollback')
    print('=' * 40)
    print()
    print('This will DELETE:')
    print(f'  - v2 database:       {DB_PATH}')
    print(f'  - Migration data:    {MIGRATION_DATA_DIR}')
    for sub in UPLOAD_SUBFOLDERS:
        folder = os.path.join(UPLOADS_DIR, sub)
        if os.path.exists(folder):
            count = len([f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))])
            if count > 0:
                print(f'  - uploads/{sub}:  {count} files')
    print()
    print('The v1 data (MySQL + mounted uploads) is NOT affected.')
    print()

    if not args.force:
        answer = input('Type ROLLBACK to confirm: ').strip()
        if answer != 'ROLLBACK':
            print('Aborted.')
            sys.exit(0)

    # 1. Delete v2 database
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f'Deleted: {DB_PATH}')
    else:
        print(f'No database found at {DB_PATH}')

    # 2. Clear v2 upload directories
    for sub in UPLOAD_SUBFOLDERS:
        folder = os.path.join(UPLOADS_DIR, sub)
        if os.path.exists(folder):
            count = 0
            for f in os.listdir(folder):
                fpath = os.path.join(folder, f)
                if os.path.isfile(fpath):
                    os.remove(fpath)
                    count += 1
            if count > 0:
                print(f'Cleared: uploads/{sub} ({count} files)')

    # 3. Clear migration data (status, logs, backups, lock)
    if os.path.exists(MIGRATION_DATA_DIR):
        for entry in os.listdir(MIGRATION_DATA_DIR):
            path = os.path.join(MIGRATION_DATA_DIR, entry)
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        print(f'Cleared: {MIGRATION_DATA_DIR}')

    print()
    print('Rollback complete. Restart the app to re-run migration.')


if __name__ == '__main__':
    main()
