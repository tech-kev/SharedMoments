"""Main migration orchestrator for v1 → v2 SharedMoments migration."""
import json
import os
import shutil
import time
from datetime import datetime

from app.migration.migration_logger import migration_log as log, get_log_file_path
from app.migration.status import (
    STEPS, load_status, create_status, update_step,
    is_step_completed, mark_migration_complete, is_migration_complete,
)
from app.migration.v1_reader import (
    v1_configured, test_connection, discover_schema, read_settings,
    read_settings_full, read_feed_items, read_bucketlist, read_filmlist,
    read_moments, read_countdown, get_v1_setting, get_row_value,
)

BASEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MIGRATION_DATA_DIR = os.path.join(BASEDIR, 'migration_data')
BACKUP_DIR = os.path.join(MIGRATION_DATA_DIR, 'backup')
V2_DB_PATH = os.path.join(BASEDIR, 'database', 'sharedmomentsv2.db')

IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi', 'webm', 'mkv'}
MUSIC_EXTENSIONS = {'mp3'}

# v1 relationship status text → v2 integer ID
RELATIONSHIP_STATUS_MAP = {
    # German
    'zusammen': '1', 'in einer beziehung': '1',
    'verlobt': '2',
    'verheiratet': '3',
    'es ist kompliziert': '4', 'kompliziert': '4',
    'offen': '5', 'offene beziehung': '5',
    # English
    'in a relationship': '1', 'together': '1', 'dating': '1',
    'engaged': '2',
    'married': '3',
    "it's complicated": '4', 'complicated': '4',
    'open': '5', 'open relationship': '5',
    # Spanish
    'en una relación': '1',
    'casado': '3', 'casada': '3',
    'en una relación abierta': '5',
    'en una relación complicada': '4',
    # Portuguese
    'em um relacionamento': '1',
    'em um relacionamento aberto': '5',
    'em um relacionamento complicado': '4',
    # Numeric pass-through
    '1': '1', '2': '2', '3': '3', '4': '4', '5': '5',
}

# v1 contentType → v2 contentType
CONTENT_TYPE_MAP = {
    'picture': 'image',
    'image': 'image',
    'photo': 'image',
    'video': 'video',
    'video-mov': 'video',
    'gallery': 'galleryStartWithImage',
    'galleryStartWithImage': 'galleryStartWithImage',
    'galleryStartWithVideo': 'galleryStartWithVideo',
    'text': 'text',
}

# Counters for summary
_summary = {
    'users_created': 0,
    'users_placeholder': 0,
    'settings_migrated': 0,
    'files_copied': 0,
    'files_size_bytes': 0,
    'feed_items': 0,
    'bucketlist_items': 0,
    'filmlist_items': 0,
    'moments': 0,
    'countdowns': 0,
    'warnings': 0,
}


def _warn(prefix, msg):
    _summary['warnings'] += 1
    log('warning', f'{prefix} {msg}')


def _strip_upload_prefix(url):
    """Strip v1 upload path prefixes from contentURL."""
    if not url:
        return ''
    prefixes = [
        './upload/feed_items/', './upload/stock_items/',
        '/upload/feed_items/', '/upload/stock_items/',
        'upload/feed_items/', 'upload/stock_items/',
    ]
    for prefix in prefixes:
        if url.startswith(prefix):
            return url[len(prefix):]
    return url


def _transform_content_url(v1_url):
    """Transform a v1 contentURL (possibly semicolon-separated) to v2 format."""
    if not v1_url:
        return ''
    parts = v1_url.split(';')
    transformed = [_strip_upload_prefix(p.strip()) for p in parts if p.strip()]
    return ';'.join(transformed)


def _map_content_type(v1_type):
    """Map v1 contentType to v2 contentType."""
    if not v1_type:
        return 'text'
    return CONTENT_TYPE_MAP.get(v1_type.lower().strip(), v1_type)


def _get_upload_folder_for_ext(ext):
    """Return the v2 upload subfolder name based on file extension."""
    ext = ext.lower()
    if ext in VIDEO_EXTENSIONS:
        return 'videos'
    if ext in MUSIC_EXTENSIONS:
        return 'music'
    return 'images'


def check_and_run_migration():
    """Entry point: called from run.py on startup."""
    if not v1_configured():
        return

    # File lock FIRST: only one gunicorn worker runs migration
    import fcntl
    os.makedirs(MIGRATION_DATA_DIR, exist_ok=True)
    lock_path = os.path.join(MIGRATION_DATA_DIR, '.migration.lock')
    lock_fd = open(lock_path, 'w')
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (IOError, OSError):
        lock_fd.close()
        return  # Another worker is already running migration

    try:
        if is_migration_complete():
            log('info', '[Migration] Already completed, skipping')
            return
        _run_migration(lock_fd)
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


def _run_migration(lock_fd):
    """Run the actual migration (called with file lock held)."""
    dry_run = os.environ.get('MIGRATION_DRY_RUN', 'false').lower() == 'true'
    prefix = '[Migration DRY-RUN]' if dry_run else '[Migration]'
    start_time = time.time()

    # Reset counters
    for key in _summary:
        _summary[key] = 0

    log('info', f'{prefix} v1 MySQL env vars detected, starting migration...')

    if not test_connection():
        log('error', f'{prefix} Cannot connect to v1 MySQL — aborting migration')
        return

    # Discover and log v1 schema
    schema = discover_schema()
    log('info', f'{prefix} v1 database schema:')
    for table, info in schema.items():
        cols = ', '.join(f'{c[0]} ({c[1]})' for c in info['columns'])
        log('info', f'{prefix}   {table} ({info["row_count"]} rows): {cols}')

    # Load or create migration status
    # Dry-runs always start fresh; real runs ignore previous dry-run status
    status = load_status()
    if status is None or dry_run or status.get('dry_run', False):
        status = create_status(dry_run=dry_run)

    # Dry-run: write report file
    if dry_run:
        _write_dry_run_report(schema, prefix)

    # Run each step
    step_functions = {
        'backup_db': _step_backup_db,
        'migrate_users': _step_migrate_users,
        'migrate_settings': _step_migrate_settings,
        'migrate_feed_items': _step_migrate_feed_items,
        'migrate_bucketlist': _step_migrate_bucketlist,
        'migrate_filmlist': _step_migrate_filmlist,
        'migrate_moments': _step_migrate_moments,
        'migrate_countdown': _step_migrate_countdown,
        'migrate_files': _step_migrate_files,
        'post_migration': _step_post_migration,
    }

    for step_name in STEPS:
        if is_step_completed(status, step_name):
            log('info', f'{prefix} Step "{step_name}" already completed, skipping')
            continue

        func = step_functions.get(step_name)
        if not func:
            _warn(prefix, f'No function for step "{step_name}", skipping')
            continue

        log('info', f'{prefix} Starting step "{step_name}"...')
        update_step(status, step_name, 'in_progress')
        try:
            func(status, dry_run, prefix)
            update_step(status, step_name, 'completed')
            log('info', f'{prefix} Step "{step_name}" completed')
        except Exception as e:
            update_step(status, step_name, 'failed', error=e)
            log('error', f'{prefix} Step "{step_name}" FAILED: {e}')
            import traceback
            log('error', traceback.format_exc())
            return  # Stop on failure

    mark_migration_complete(status)

    # Print summary
    duration = time.time() - start_time
    _print_summary(prefix, duration)


def _print_summary(prefix, duration):
    """Print a structured migration summary."""
    s = _summary
    total_items = s['feed_items'] + s['bucketlist_items'] + s['filmlist_items'] + s['moments'] + s['countdowns']
    size_mb = s['files_size_bytes'] / (1024 * 1024) if s['files_size_bytes'] > 0 else 0

    log('info', f'{prefix} === MIGRATION COMPLETE ===')
    log('info', f'{prefix} Duration: {duration:.1f}s')
    log('info', f'{prefix} Users: {s["users_created"]} created ({s["users_placeholder"]} with placeholder emails)')
    log('info', f'{prefix} Items: {total_items} migrated (Feed: {s["feed_items"]}, Bucket: {s["bucketlist_items"]}, Film: {s["filmlist_items"]}, Moments: {s["moments"]}, Countdown: {s["countdowns"]})')
    log('info', f'{prefix} Files: {s["files_copied"]} copied ({size_mb:.1f} MB)')
    log('info', f'{prefix} Settings: {s["settings_migrated"]} migrated')
    log('info', f'{prefix} Warnings: {s["warnings"]} (see above)')
    log_path = get_log_file_path()
    if log_path:
        log('info', f'{prefix} Log file: {log_path}')


def _write_dry_run_report(schema, prefix):
    """Write a dry-run report file."""
    os.makedirs(MIGRATION_DATA_DIR, exist_ok=True)
    report_path = os.path.join(MIGRATION_DATA_DIR, 'migration_dry_run_report.txt')
    v1_upload_path = os.environ.get('MIGRATION_V1_UPLOAD_PATH', '')

    v1_settings = read_settings()

    lines = [
        'SharedMoments v1 → v2 Migration Dry-Run Report',
        f'Generated: {datetime.now().isoformat()}',
        '',
        '== MySQL Connection ==',
        f'Host: {os.environ.get("MIGRATION_V1_MYSQL_HOST", "?")}',
        f'Port: {os.environ.get("MIGRATION_V1_MYSQL_PORT", "3306")}',
        f'Database: {os.environ.get("MIGRATION_V1_MYSQL_DB", "?")}',
        f'Status: Connected',
        '',
        '== v1 Database Tables ==',
    ]

    # Only show tables relevant to migration
    skip_tables = {'users', 'sessions', 'pushtokens', 'sidemenu'}
    for table, info in schema.items():
        if table.lower() not in skip_tables:
            lines.append(f'  {table}: {info["row_count"]} rows')

    # User info from settings (v1 stores users as settings, not in users table)
    user_a = get_v1_setting(v1_settings, 'userA') or ''
    user_b = get_v1_setting(v1_settings, 'userB') or ''
    user_names = [n for n in [str(user_a).strip(), str(user_b).strip()] if n]
    lines.append(f'  Users (from settings): {len(user_names)} ({", ".join(user_names) if user_names else "none"})')

    lines.append('')
    lines.append('== v1 Upload Files ==')
    if v1_upload_path and os.path.exists(v1_upload_path):
        file_count = sum(len(files) for _, _, files in os.walk(v1_upload_path))
        total_size = sum(
            os.path.getsize(os.path.join(r, f))
            for r, _, files in os.walk(v1_upload_path)
            for f in files
        )
        lines.append(f'  Path: {v1_upload_path}')
        lines.append(f'  Files: {file_count}')
        lines.append(f'  Size: {total_size / (1024*1024):.1f} MB')
    else:
        lines.append(f'  Path: {v1_upload_path or "(not set)"}')
        lines.append(f'  Status: Not available')

    # Per-type counts
    lines.append('')
    lines.append('== Data to Migrate ==')
    lines.append(f'  Settings: {len(v1_settings)} entries')
    lines.append(f'  Feed items: {len(read_feed_items())} entries → Home (listType=1)')
    lines.append(f'  Bucket list: {len(read_bucketlist())} entries → Bucket List (listType=4)')
    lines.append(f'  Film list: {len(read_filmlist())} entries → Movie List (listType=3)')
    lines.append(f'  Moments: {len(read_moments())} entries → Moments (listType=2)')
    full_settings = read_settings_full()
    has_countdown = full_settings.get('countdown', {}).get('value', '') not in ('', 'Countdown')
    lines.append(f'  Countdown: {"1 (from settings)" if has_countdown else "0"} → Countdown (listType=5)')

    lines.append('')
    lines.append('== Transformations ==')
    lines.append('  ContentType: picture→image, video→video, gallery→galleryStartWithImage')
    lines.append('  ContentURL: ./upload/feed_items/file.jpg → file.jpg (prefix stripped)')
    lines.append('  Files sorted into: images/, videos/, music/ by extension')
    lines.append('  Relationship status: text mapped to integer ID (1-5)')
    lines.append('  Item edition: set to "couples"')

    lines.append('')
    lines.append('== Placeholder Data ==')
    lines.append('  User emails: migration_pending_<name>@placeholder.local')
    lines.append('  User names: "Migration: <v1_username>" if original name is missing')
    lines.append('  These must be updated on the post-migration page before the app is usable.')

    report_content = '\n'.join(lines)
    with open(report_path, 'w') as f:
        f.write(report_content)

    # Also log the report content
    for line in lines:
        log('info', f'{prefix} [REPORT] {line}')

    log('info', f'{prefix} Dry-run report written to {report_path}')


# ==================== Step Implementations ====================


def _step_backup_db(status, dry_run, prefix):
    """Backup v2 SQLite DB and dump v1 MySQL data."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f'v1_backup_{timestamp}')

    if dry_run:
        log('info', f'{prefix} Would create backup at {backup_path}/')
        return

    os.makedirs(os.path.join(backup_path, 'db'), exist_ok=True)

    # 1. Backup v2 SQLite
    if os.path.exists(V2_DB_PATH):
        shutil.copy2(V2_DB_PATH, os.path.join(backup_path, 'db', 'sharedmomentsv2.db'))
        log('info', f'{prefix} v2 SQLite DB backed up')

    # 2. Dump v1 MySQL via INSERT statements
    dump_path = os.path.join(backup_path, 'db', 'v1_mysql_dump.sql')
    _dump_v1_mysql(dump_path, prefix)

    status['backup_path'] = backup_path


def _dump_v1_mysql(dump_path, prefix):
    """Export v1 MySQL tables as INSERT statements (no external mysqldump needed)."""
    from app.migration.v1_reader import get_v1_connection

    conn = get_v1_connection()
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]

    with open(dump_path, 'w') as f:
        f.write(f'-- SharedMoments v1 MySQL dump\n')
        f.write(f'-- Generated: {datetime.now().isoformat()}\n\n')

        for table in tables:
            cursor.execute(f"SELECT * FROM `{table}`")
            rows = cursor.fetchall()
            if not rows:
                f.write(f'-- Table `{table}`: 0 rows\n\n')
                continue

            # Get column names
            col_names = [desc[0] for desc in cursor.description]
            f.write(f'-- Table `{table}`: {len(rows)} rows\n')

            for row in rows:
                values = []
                for val in row:
                    if val is None:
                        values.append('NULL')
                    elif isinstance(val, (int, float)):
                        values.append(str(val))
                    else:
                        escaped = str(val).replace("'", "''")
                        values.append(f"'{escaped}'")
                cols_str = ', '.join(f'`{c}`' for c in col_names)
                vals_str = ', '.join(values)
                f.write(f"INSERT INTO `{table}` ({cols_str}) VALUES ({vals_str});\n")
            f.write('\n')

    cursor.close()
    conn.close()

    dump_size = os.path.getsize(dump_path)
    if dump_size == 0:
        _warn(prefix, 'MySQL dump file is empty!')
    else:
        log('info', f'{prefix} v1 MySQL dump: {dump_path} ({dump_size} bytes)')


def _step_migrate_files(status, dry_run, prefix):
    """Copy v1 upload files to v2 directory structure."""
    v1_upload_path = os.environ.get('MIGRATION_V1_UPLOAD_PATH', '')
    if not v1_upload_path or not os.path.exists(v1_upload_path):
        log('info', f'{prefix} No v1 upload path — skipping file migration')
        return

    v2_uploads = os.path.join(BASEDIR, 'uploads')
    copied = 0
    skipped = 0
    total_size = 0

    for root, dirs, files in os.walk(v1_upload_path):
        for filename in files:
            src = os.path.join(root, filename)
            ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            subfolder = _get_upload_folder_for_ext(ext)
            dest_dir = os.path.join(v2_uploads, subfolder)
            dest = os.path.join(dest_dir, filename)

            if os.path.exists(dest):
                skipped += 1
                continue

            file_size = os.path.getsize(src)

            if dry_run:
                log('debug', f'{prefix} Would copy {src} → {dest} ({file_size} bytes)')
                copied += 1
                total_size += file_size
                continue

            os.makedirs(dest_dir, exist_ok=True)
            shutil.copy2(src, dest)
            # Set readable permissions (owner + group read/write)
            os.chmod(dest, 0o644)
            # Verify file size matches
            dest_size = os.path.getsize(dest)
            if dest_size != file_size:
                _warn(prefix, f'Size mismatch: {filename} (src={file_size}, dest={dest_size})')
            copied += 1
            total_size += file_size

    _summary['files_copied'] = copied
    _summary['files_size_bytes'] = total_size
    log('info', f'{prefix} Files: {copied} copied, {skipped} already existed ({total_size / (1024*1024):.1f} MB)')


def _step_migrate_users(status, dry_run, prefix):
    """Create v2 users from v1 userA/userB settings.

    v1 structure: settings table with option='userA'/'userB',
    value=name, specialvalue=birthday (YYYY-MM-DD).
    v1 users table has username/password_salt/password_hash.
    """
    from app.models import User, UserRole, Role, SessionLocal

    v1_settings = read_settings()
    if not v1_settings:
        _warn(prefix, 'No v1 settings found — cannot migrate users')
        return

    session = SessionLocal()
    try:
        # Check if non-system users already exist
        existing_users = session.query(User).filter(User.id > 1).count()
        if existing_users > 0:
            log('info', f'{prefix} v2 users already exist ({existing_users}), skipping user migration')
            return

        admin_role = session.query(Role).filter(Role.roleName == 'Admin').first()
        adult_role = session.query(Role).filter(Role.roleName == 'Adult').first()

        users_created = []

        # v1 settings: option='userA' → value=name, specialvalue=birthday
        for user_key, role in [('userA', admin_role), ('userB', adult_role)]:
            user_setting = get_v1_setting(v1_settings, user_key)
            # user_setting is the 'value' column (= name)
            first_name = str(user_setting).strip() if user_setting else ''

            # Get birthday from specialvalue — need to read raw row
            birthday = _get_v1_setting_specialvalue(user_key)

            if not first_name:
                first_name = f'Migration: {user_key}'
                _warn(prefix, f'No name found for {user_key}, using placeholder: "{first_name}"')

            safe_name = first_name.lower().replace(' ', '_')
            placeholder_email = f'migration_pending_{safe_name}@placeholder.local'

            log('info', f'{prefix} Creating user: {first_name} (from v1 {user_key}, birthday={birthday}, email={placeholder_email})')

            if dry_run:
                users_created.append(user_key)
                _summary['users_created'] += 1
                _summary['users_placeholder'] += 1
                continue

            new_user = User(
                firstName=first_name,
                lastName='',
                email=placeholder_email,
                profilePicture='',
            )
            new_user.hash_password('changeme')

            if birthday:
                try:
                    from dateutil.parser import parse as parse_date
                    new_user.birthDate = parse_date(str(birthday)).date()
                except Exception:
                    _warn(prefix, f'Could not parse birthday "{birthday}" for {user_key}')

            session.add(new_user)
            session.flush()

            if role:
                session.add(UserRole(userID=new_user.id, roleID=role.id))

            from app.models import UserSetting
            session.add(UserSetting(userID=new_user.id, name='language', value='en', icon='language', edition='all', category='about', type='text'))
            session.add(UserSetting(userID=new_user.id, name='darkmode', value='FALSE', icon='dark_mode', edition='all', category='about', type='text'))

            users_created.append(user_key)
            _summary['users_created'] += 1
            _summary['users_placeholder'] += 1

        if not dry_run:
            session.commit()

        log('info', f'{prefix} Users created: {", ".join(users_created) if users_created else "none"}')
    finally:
        session.close()


def _step_migrate_settings(status, dry_run, prefix):
    """Map v1 settings to v2 settings table.

    v1 settings (option → value, specialvalue):
      banner       → banner image path (value), strip upload prefix
      music        → banner song path (value), specialvalue='true'/'false'
      mainTitle    → app title (value)
      anniversary  → anniversary date (value)
      relationship_status → status text (value), map to integer
      wedding_date → wedding date (value)
      countdown    → title (value), target date (specialvalue) → migrated as item
    """
    from app.models import Setting, SessionLocal

    v1_settings = read_settings()
    if not v1_settings:
        _warn(prefix, 'No v1 settings found')
        return

    session = SessionLocal()
    try:
        # v2_name → (v1 option name, transform)
        mappings = {
            'title': ('mainTitle', None),
            'relationship_status': ('relationship_status', '_map_relationship_status'),
            'anniversary_date': ('anniversary', None),
            'wedding_date': ('wedding_date', None),
            'banner_image': ('banner', '_strip_upload'),
            'banner_song': ('music', '_strip_upload'),
        }

        migrated = 0
        for v2_name, (v1_option, transform) in mappings.items():
            v1_value = get_v1_setting(v1_settings, v1_option)

            if v1_value is None or v1_value == '':
                continue

            v1_value = str(v1_value)

            # Skip fake banner placeholder
            if v1_option == 'banner' and 'fakeimg.pl' in v1_value:
                log('info', f'{prefix} Skipping placeholder banner image')
                continue

            if transform == '_map_relationship_status':
                mapped = RELATIONSHIP_STATUS_MAP.get(v1_value.lower().strip(), '')
                if mapped:
                    v1_value = mapped
                else:
                    _warn(prefix, f'Unknown relationship status: "{v1_value}"')
                    continue
            elif transform == '_strip_upload':
                v1_value = _strip_upload_prefix(v1_value)

            v2_setting = session.query(Setting).filter(Setting.name == v2_name).first()
            if v2_setting:
                if v2_setting.value and v2_setting.value != '':
                    log('info', f'{prefix} Setting "{v2_name}" already has value, skipping')
                    continue
                log('info', f'{prefix} Setting {v2_name} = "{v1_value}"')
                if not dry_run:
                    v2_setting.value = v1_value
                migrated += 1

        # Set edition to couples
        edition_setting = session.query(Setting).filter(Setting.name == 'sm_edition').first()
        if edition_setting and edition_setting.value != 'couples':
            log('info', f'{prefix} Setting sm_edition = "couples"')
            if not dry_run:
                edition_setting.value = 'couples'
            migrated += 1

        if not dry_run:
            session.commit()

        _summary['settings_migrated'] = migrated
    finally:
        session.close()


def _step_migrate_feed_items(status, dry_run, prefix):
    """Migrate v1 feed items → v2 items (Home, listType=1)."""
    v1_items = read_feed_items()
    if not v1_items:
        log('info', f'{prefix} No v1 feed items found')
        return

    count = _migrate_items_to_v2(
        v1_items, list_type_id=1, default_content_type='image',
        item_type='feed_items', dry_run=dry_run, prefix=prefix,
    )
    _summary['feed_items'] = count


def _step_migrate_bucketlist(status, dry_run, prefix):
    """Migrate v1 bucket list → v2 items (Bucket List, listType=4)."""
    v1_items = read_bucketlist()
    if not v1_items:
        log('info', f'{prefix} No v1 bucket list items found')
        return

    count = _migrate_list_items_to_v2(
        v1_items, list_type_id=4, item_type='bucketlist',
        dry_run=dry_run, prefix=prefix,
    )
    _summary['bucketlist_items'] = count


def _step_migrate_filmlist(status, dry_run, prefix):
    """Migrate v1 film list → v2 items (Movie List, listType=3)."""
    v1_items = read_filmlist()
    if not v1_items:
        log('info', f'{prefix} No v1 film list items found')
        return

    count = _migrate_list_items_to_v2(
        v1_items, list_type_id=3, item_type='filmlist',
        dry_run=dry_run, prefix=prefix,
    )
    _summary['filmlist_items'] = count


def _step_migrate_moments(status, dry_run, prefix):
    """Migrate v1 moments → v2 items (Moments, listType=2)."""
    v1_items = read_moments()
    if not v1_items:
        log('info', f'{prefix} No v1 moments found')
        return

    from app.models import Item, User, SessionLocal

    session = SessionLocal()
    try:
        creator = session.query(User).filter(User.id > 1).first()
        creator_id = creator.id if creator else 1

        migrated = 0
        for row in v1_items:
            title = get_row_value(row, 'title', 'Title', 'name', 'Name', 'description')
            content = get_row_value(row, 'content', 'Content', 'description', 'Description', 'text') or ''
            moment_date = get_row_value(row, 'date', 'Date', 'moment_date', 'eventDate', 'event_date')
            date_created = get_row_value(row, 'date_added', 'dateCreated', 'created_at', 'createdAt', 'dateAdded')

            if moment_date:
                date_created = moment_date

            if not title:
                continue

            log('info', f'{prefix} Moment: "{title}" ({date_created})')

            if dry_run:
                migrated += 1
                continue

            item = Item(
                title=_clean_html(title),
                content=_clean_html(content),
                contentType='text',
                listType=2,
                contentURL='',
                edition='couples',
                createdByUser=creator_id,
            )
            if date_created:
                try:
                    from dateutil.parser import parse as parse_date
                    item.dateCreated = parse_date(str(date_created))
                except Exception:
                    pass

            session.add(item)
            migrated += 1

        if not dry_run:
            session.commit()

        _summary['moments'] = migrated
        log('info', f'{prefix} Moments migrated: {migrated}')
    finally:
        session.close()


def _step_migrate_countdown(status, dry_run, prefix):
    """Migrate v1 countdown → v2 items (Countdown, listType=5).

    v1 has countdown as a setting: option='countdown', value=title, specialvalue=target_date.
    """
    from app.models import Item, User, SessionLocal
    from app.db_queries import get_list_type_by_title

    # v1 countdown is a setting, not a table
    full_settings = read_settings_full()
    countdown_setting = full_settings.get('countdown', {})
    title = countdown_setting.get('value', '')
    target_date = countdown_setting.get('specialvalue', '')

    if not title or title == 'Countdown':
        log('info', f'{prefix} No v1 countdown configured (title="{title}")')
        # Still empty/default, skip
        if not title or title == 'Countdown':
            _summary['countdowns'] = 0
            return

    countdown_lt = get_list_type_by_title('Countdown')
    if not countdown_lt:
        _warn(prefix, 'Countdown list type not found in v2, skipping')
        return

    session = SessionLocal()
    try:
        creator = session.query(User).filter(User.id > 1).first()
        creator_id = creator.id if creator else 1

        log('info', f'{prefix} Countdown: "{title}" (target: {target_date})')

        if dry_run:
            _summary['countdowns'] = 1
            return

        item = Item(
            title=str(title),
            content='',
            contentType='countdown',
            listType=countdown_lt.id,
            contentURL='',
            edition='couples',
            createdByUser=creator_id,
        )
        if target_date:
            try:
                from dateutil.parser import parse as parse_date
                item.dateCreated = parse_date(str(target_date))
            except Exception:
                _warn(prefix, f'Could not parse countdown date: {target_date}')

        session.add(item)
        session.commit()

        _summary['countdowns'] = 1
        log('info', f'{prefix} Countdown migrated')
    finally:
        session.close()


def _step_post_migration(status, dry_run, prefix):
    """Mark setup complete and set migration_review_complete to False (gate)."""
    from app.models import Setting, SessionLocal

    session = SessionLocal()
    try:
        # Mark setup as complete (bypass setup page)
        setup = session.query(Setting).filter(Setting.name == 'setup_complete').first()
        if setup:
            log('info', f'{prefix} Setting setup_complete = True')
            if not dry_run:
                setup.value = 'True'

        # Set migration_review_complete to False (gate for /migration-complete)
        review = session.query(Setting).filter(Setting.name == 'migration_review_complete').first()
        if review:
            log('info', f'{prefix} Setting migration_review_complete = False (redirect gate active)')
            if not dry_run:
                review.value = 'False'
        else:
            # Create it if missing (older DB without this setting)
            log('info', f'{prefix} Creating migration_review_complete setting')
            if not dry_run:
                session.add(Setting(name='migration_review_complete', value='False', icon='', edition='all', category='', type='text'))

        if not dry_run:
            session.commit()
    finally:
        session.close()

    log('info', f'{prefix} Post-migration steps done')


# ==================== Helper Functions ====================


def _clean_html(text):
    """Convert HTML line breaks to newlines and strip remaining HTML tags."""
    import re
    if not text:
        return ''
    s = str(text)
    # <br>, <br/>, <br /> → newline
    s = re.sub(r'<br\s*/?>', '\n', s, flags=re.IGNORECASE)
    # Strip remaining HTML tags
    s = re.sub(r'<[^>]+>', '', s)
    return s.strip()


def _get_v1_setting_specialvalue(option_name):
    """Get the specialvalue for a v1 setting option (e.g. userA birthday, countdown date)."""
    full = read_settings_full()
    entry = full.get(option_name, {})
    return entry.get('specialvalue', '') or ''


def _migrate_items_to_v2(v1_items, list_type_id, default_content_type, item_type, dry_run, prefix):
    """Migrate v1 content items (feed_items) to v2 items table. Returns count."""
    from app.models import Item, User, SessionLocal

    session = SessionLocal()
    try:
        creator = session.query(User).filter(User.id > 1).first()
        creator_id = creator.id if creator else 1

        migrated = 0
        for row in v1_items:
            title = get_row_value(row, 'title', 'Title', 'name', 'Name')
            content = get_row_value(row, 'content', 'Content', 'description', 'Description', 'text') or ''
            content_type = get_row_value(row, 'contentType', 'content_type', 'type', 'Type', 'mediaType')
            content_url = get_row_value(row, 'contentURL', 'content_url', 'url', 'URL', 'media_url', 'mediaUrl', 'file', 'filename')
            date_created = get_row_value(row, 'date_added', 'dateCreated', 'created_at', 'createdAt', 'dateAdded', 'date')

            v2_content_type = _map_content_type(content_type) if content_type else default_content_type
            v2_content_url = _transform_content_url(str(content_url)) if content_url else ''

            log('info', f'{prefix} {item_type}: "{title}" type={v2_content_type} url={v2_content_url}')

            if dry_run:
                migrated += 1
                continue

            item = Item(
                title=_clean_html(title),
                content=_clean_html(content),
                contentType=v2_content_type,
                listType=list_type_id,
                contentURL=v2_content_url,
                edition='couples',
                createdByUser=creator_id,
            )
            if date_created:
                try:
                    from dateutil.parser import parse as parse_date
                    item.dateCreated = parse_date(str(date_created))
                except Exception:
                    pass

            session.add(item)
            migrated += 1

        if not dry_run:
            session.commit()

        log('info', f'{prefix} {item_type}: {migrated} items migrated')
        return migrated
    finally:
        session.close()


def _migrate_list_items_to_v2(v1_items, list_type_id, item_type, dry_run, prefix):
    """Migrate v1 checklist items (bucketlist/filmlist) to v2 items table. Returns count."""
    from app.models import Item, User, SessionLocal

    session = SessionLocal()
    try:
        creator = session.query(User).filter(User.id > 1).first()
        creator_id = creator.id if creator else 1

        migrated = 0
        for row in v1_items:
            title = get_row_value(row, 'title', 'Title', 'name', 'Name')
            checked = get_row_value(row, 'checked', 'Checked', 'done', 'Done', 'completed', 'is_checked')
            date_created = get_row_value(row, 'date_added', 'dateCreated', 'created_at', 'createdAt', 'dateAdded')

            if not title:
                continue

            v2_content = '1' if (checked and str(checked) in ('1', 'True', 'true', 'yes')) else '0'

            log('info', f'{prefix} {item_type}: "{title}" checked={v2_content}')

            if dry_run:
                migrated += 1
                continue

            item = Item(
                title=str(title),
                content=v2_content,
                contentType='list',
                listType=list_type_id,
                contentURL='',
                edition='couples',
                createdByUser=creator_id,
            )
            if date_created:
                try:
                    from dateutil.parser import parse as parse_date
                    item.dateCreated = parse_date(str(date_created))
                except Exception:
                    pass

            session.add(item)
            migrated += 1

        if not dry_run:
            session.commit()

        log('info', f'{prefix} {item_type}: {migrated} items migrated')
        return migrated
    finally:
        session.close()
