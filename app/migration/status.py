"""Migration status tracking via JSON file."""
import json
import os
from datetime import datetime

STATUS_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'migration_data')
STATUS_FILE = os.path.join(STATUS_DIR, 'migration_status.json')

STEPS = [
    'backup_db',
    'migrate_users',
    'migrate_settings',
    'migrate_feed_items',
    'migrate_bucketlist',
    'migrate_filmlist',
    'migrate_moments',
    'migrate_countdown',
    'migrate_files',
    'post_migration',
]


def _ensure_dir():
    os.makedirs(STATUS_DIR, exist_ok=True)


def load_status():
    """Load migration status from JSON file. Returns None if not found."""
    if not os.path.exists(STATUS_FILE):
        return None
    with open(STATUS_FILE, 'r') as f:
        return json.load(f)


def save_status(status):
    """Save migration status to JSON file."""
    _ensure_dir()
    with open(STATUS_FILE, 'w') as f:
        json.dump(status, f, indent=2, default=str)


def create_status(dry_run=False):
    """Create a fresh migration status with all steps pending."""
    status = {
        'version': '2.0',
        'started_at': datetime.now().isoformat(),
        'completed_at': None,
        'backup_path': None,
        'dry_run': dry_run,
        'steps': {}
    }
    for step in STEPS:
        status['steps'][step] = {'status': 'pending'}
    save_status(status)
    return status


def update_step(status, step_name, step_status, error=None):
    """Update a migration step's status."""
    status['steps'][step_name] = {
        'status': step_status,
        'timestamp': datetime.now().isoformat()
    }
    if error:
        status['steps'][step_name]['error'] = str(error)
    save_status(status)


def is_step_completed(status, step_name):
    """Check if a step has already been completed."""
    step = status.get('steps', {}).get(step_name, {})
    return step.get('status') == 'completed'


def mark_migration_complete(status):
    """Mark the entire migration as complete."""
    status['completed_at'] = datetime.now().isoformat()
    save_status(status)


def is_migration_complete():
    """Check if migration has already been completed (ignores dry-run)."""
    status = load_status()
    if status is None:
        return False
    if status.get('dry_run', False):
        return False
    return status.get('completed_at') is not None


def delete_status():
    """Remove the migration status file."""
    if os.path.exists(STATUS_FILE):
        os.remove(STATUS_FILE)
