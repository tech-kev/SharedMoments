"""Demo mode utilities — isolated SQLite instances per demo visitor."""

import os
import shutil
import threading
import uuid
from datetime import datetime, timedelta

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from config import Config
from app.logger import log

DEMO_DB_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'database')
DEMO_DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'demo_data')
DEMO_TEMPLATE_DB = os.path.join(DEMO_DATA_DIR, 'demo_template.db')
DEMO_ASSETS_DIR = os.path.join(DEMO_DATA_DIR, 'demo_assets')
UPLOADS_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
_assets_copied = False

# Thread-safe engine cache: {demo_id: (engine, created_at)}
_engine_cache = {}
_cache_lock = threading.Lock()


def get_demo_engine(demo_id):
    """Get or create an engine for a demo session (thread-safe)."""
    with _cache_lock:
        if demo_id in _engine_cache:
            return _engine_cache[demo_id][0]

    db_path = os.path.join(DEMO_DB_DIR, f'demo_{demo_id}.db')
    if not os.path.exists(db_path):
        return None

    eng = create_engine(f'sqlite:///{db_path}')

    @event.listens_for(eng, 'connect')
    def _set_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute('PRAGMA busy_timeout=5000')
        cursor.close()

    with _cache_lock:
        _engine_cache[demo_id] = (eng, datetime.utcnow())

    return eng


def _ensure_demo_assets():
    """Copy demo assets (images, profiles) to uploads dir once per process."""
    global _assets_copied
    if _assets_copied or not os.path.isdir(DEMO_ASSETS_DIR):
        return
    for subfolder in ('images', 'profiles'):
        src = os.path.join(DEMO_ASSETS_DIR, subfolder)
        dst = os.path.join(UPLOADS_DIR, subfolder)
        if not os.path.isdir(src):
            continue
        os.makedirs(dst, exist_ok=True)
        for fname in os.listdir(src):
            dst_file = os.path.join(dst, fname)
            if not os.path.exists(dst_file):
                shutil.copy2(os.path.join(src, fname), dst_file)
    _assets_copied = True
    log('info', 'Demo assets copied to uploads')


def create_demo_session():
    """Copy template DB and ensure demo assets, return new demo_id."""
    if not os.path.exists(DEMO_TEMPLATE_DB):
        raise FileNotFoundError(f'Demo template DB not found: {DEMO_TEMPLATE_DB}')

    _ensure_demo_assets()

    demo_id = uuid.uuid4().hex[:12]
    db_path = os.path.join(DEMO_DB_DIR, f'demo_{demo_id}.db')
    shutil.copy2(DEMO_TEMPLATE_DB, db_path)
    log('info', f'Created demo session {demo_id}')
    return demo_id


def bind_demo_session(demo_id):
    """Bind demo engine to current request via flask.g."""
    from flask import g

    eng = get_demo_engine(demo_id)
    if eng is None:
        return False

    g._demo_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    return True


def cleanup_demo_sessions():
    """Delete expired demo DBs and dispose their engines."""
    timeout = Config.DEMO_SESSION_TIMEOUT
    cutoff = datetime.utcnow() - timedelta(minutes=timeout)
    removed = 0

    for filename in os.listdir(DEMO_DB_DIR):
        if not filename.startswith('demo_') or not filename.endswith('.db'):
            continue
        if filename == 'demo_template.db':
            continue

        db_path = os.path.join(DEMO_DB_DIR, filename)
        mtime = datetime.utcfromtimestamp(os.path.getmtime(db_path))
        if mtime > cutoff:
            continue

        demo_id = filename[len('demo_'):-len('.db')]

        # Dispose engine if cached
        with _cache_lock:
            entry = _engine_cache.pop(demo_id, None)
        if entry:
            try:
                entry[0].dispose()
            except Exception:
                pass

        try:
            os.remove(db_path)
            removed += 1
        except OSError as e:
            log('warning', f'Failed to remove demo DB {filename}: {e}')

    if removed:
        log('info', f'Cleaned up {removed} expired demo session(s)')
