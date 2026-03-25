"""Dedicated migration log file alongside standard app logging."""
import logging
import os
from datetime import datetime

_migration_logger = None
_log_file_path = None


def get_migration_logger():
    """Get or create a dedicated migration file logger."""
    global _migration_logger, _log_file_path
    if _migration_logger is not None:
        return _migration_logger

    log_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'migration_data')
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    _log_file_path = os.path.join(log_dir, f'migration_log_{timestamp}.log')

    _migration_logger = logging.getLogger('sharedmoments.migration')
    _migration_logger.setLevel(logging.DEBUG)
    _migration_logger.propagate = False

    if not _migration_logger.handlers:
        fh = logging.FileHandler(_log_file_path)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        _migration_logger.addHandler(fh)

    return _migration_logger


def migration_log(level_str, message):
    """Log to both the standard app logger and the dedicated migration log file."""
    from app.logger import log
    log(level_str, message)

    level_mapping = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL,
    }
    level = level_mapping.get(level_str.lower(), logging.INFO)
    get_migration_logger().log(level, message)


def get_log_file_path():
    """Return the path to the current migration log file."""
    return _log_file_path
