import logging
import os

_logger = None


def _get_logger():
    global _logger
    if _logger is not None:
        return _logger

    _logger = logging.getLogger('sharedmoments')
    _logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers on reloads
    if not _logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        _logger.addHandler(console_handler)

        # File handler
        log_folder = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'logs')
        log_filename = 'sharedmoments.log'
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)

        file_handler = logging.FileHandler(os.path.join(log_folder, log_filename))
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        _logger.addHandler(file_handler)

    return _logger


def log(level_str, message):
    level_mapping = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }
    level = level_mapping.get(level_str.lower(), logging.INFO)
    try:
        _get_logger().log(level, message)
    except Exception as e:
        print(f'Logging error: {e}')
