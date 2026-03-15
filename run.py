from app import app
from app.models import Base, engine
from app.db_queries import init_db, sync_version_to_db, ensure_reminder_permissions, ensure_edition_settings, ensure_list_type_edition_column
from app.translation import load_translation_in_cache, migrateTranslations
from app.logger import log
from app.version import __version__

# Database initialization
Base.metadata.create_all(engine)
init_db()
sync_version_to_db()
ensure_reminder_permissions()
ensure_edition_settings()
ensure_list_type_edition_column()
migrateTranslations(overwrite=True)
load_translation_in_cache()

# VAPID key generation (for push notifications)
from app.notifications import _ensure_vapid_keys
_ensure_vapid_keys()

# v1 → v2 Migration (runs only when MIGRATION_V1_MYSQL_HOST is set)
try:
    from app.migration import check_and_run_migration
    check_and_run_migration()
except ImportError:
    pass

# Start scheduler
from app.scheduler import start_scheduler
start_scheduler(app)

if __name__ == '__main__':
    import os
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.environ.get('PORT', 5001))
    log('info', f'SharedMoments {__version__}')
    log('info', f'Starting the application on port {port} (debug={debug})')
    app.run(debug=debug, host='0.0.0.0', port=port, threaded=True)
