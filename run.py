from app import app
from app.models import Base, engine
from app.db_queries import init_db
from app.translation import load_translation_in_cache, migrateTranslations
from app.logger import log

# Database initialization
Base.metadata.create_all(engine)
init_db()
migrateTranslations()
load_translation_in_cache()

# v1 → v2 Migration (runs only when MIGRATION_V1_MYSQL_HOST is set)
try:
    from app.migration import check_and_run_migration
    check_and_run_migration()
except ImportError:
    pass

if __name__ == '__main__':
    import os
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.environ.get('PORT', 5001))
    log('info', f'Starting the application on port {port} (debug={debug})')
    app.run(debug=debug, host='0.0.0.0', port=port, threaded=True)
