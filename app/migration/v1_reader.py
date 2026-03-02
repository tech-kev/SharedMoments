"""Read data from v1 SharedMoments MySQL database."""
import os
from app.logger import log


def v1_configured():
    """Check if v1 MySQL environment variables are set."""
    return bool(os.environ.get('MIGRATION_V1_MYSQL_HOST'))


def get_v1_connection():
    """Create a connection to the v1 MySQL database."""
    import mysql.connector
    return mysql.connector.connect(
        host=os.environ.get('MIGRATION_V1_MYSQL_HOST', 'localhost'),
        port=int(os.environ.get('MIGRATION_V1_MYSQL_PORT', '3306')),
        user=os.environ.get('MIGRATION_V1_MYSQL_USER', 'root'),
        password=os.environ.get('MIGRATION_V1_MYSQL_PASS', ''),
        database=os.environ.get('MIGRATION_V1_MYSQL_DB', 'sharedmoments'),
        charset='utf8mb4',
        use_unicode=True,
    )


def test_connection():
    """Test if we can connect to the v1 MySQL database."""
    try:
        conn = get_v1_connection()
        conn.close()
        return True
    except Exception as e:
        log('error', f'[Migration] Cannot connect to v1 MySQL: {e}')
        return False


def _read_table(table_name):
    """Read all rows from a table as list of dicts."""
    conn = get_v1_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(f"SELECT * FROM `{table_name}`")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def _table_exists(table_name):
    """Check if a table exists in the v1 database."""
    conn = get_v1_connection()
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES LIKE %s", (table_name,))
    exists = cursor.fetchone() is not None
    cursor.close()
    conn.close()
    return exists


def _get_columns(table_name):
    """Get column info for a table."""
    conn = get_v1_connection()
    cursor = conn.cursor()
    cursor.execute(f"DESCRIBE `{table_name}`")
    columns = [(row[0], row[1]) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return columns


def discover_schema():
    """Discover and return the v1 database schema."""
    conn = get_v1_connection()
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()

    schema = {}
    for table in tables:
        columns = _get_columns(table)
        rows = _read_table(table)
        schema[table] = {
            'columns': columns,
            'row_count': len(rows),
        }
    return schema


def read_settings():
    """Read v1 settings as a dict {option: value}."""
    for table in ('settings', 'Settings'):
        if _table_exists(table):
            rows = _read_table(table)
            if not rows:
                return {}
            # Auto-detect column names for key/value
            sample = rows[0]
            key_col = None
            val_col = None
            for col in sample.keys():
                cl = col.lower()
                if cl in ('setting_name', 'name', 'key', 'settingname', 'option'):
                    key_col = col
                elif cl in ('setting_value', 'value', 'val', 'settingvalue'):
                    val_col = col
            if key_col and val_col:
                return {row[key_col]: row[val_col] for row in rows}
            # Fallback: first two string-like columns
            cols = list(sample.keys())
            if len(cols) >= 2:
                return {row[cols[0]]: row[cols[1]] for row in rows}
    return {}


def read_settings_full():
    """Read v1 settings as a dict {option: {value, specialvalue}}.

    v1 settings table: id, option, value, specialvalue, dateCreated, dateModified
    """
    for table in ('settings', 'Settings'):
        if _table_exists(table):
            rows = _read_table(table)
            if not rows:
                return {}
            result = {}
            for row in rows:
                option = row.get('option', '')
                if not option:
                    continue
                result[option] = {
                    'value': row.get('value', ''),
                    'specialvalue': row.get('specialvalue', ''),
                }
            return result
    return {}


def read_feed_items():
    """Read v1 feed items (main content)."""
    for table in ('feed_items',):
        if _table_exists(table):
            return _read_table(table)
    return []


def read_bucketlist():
    """Read v1 bucket list items."""
    for table in ('bucketlist_items',):
        if _table_exists(table):
            return _read_table(table)
    return []


def read_filmlist():
    """Read v1 film/movie list items."""
    for table in ('filmlist_items',):
        if _table_exists(table):
            return _read_table(table)
    return []


def read_moments():
    """Read v1 moments/timeline items."""
    for table in ('moments_items',):
        if _table_exists(table):
            return _read_table(table)
    return []


def read_countdown():
    """Read v1 countdown items."""
    for table in ('countdown', 'countdowns', 'Countdown'):
        if _table_exists(table):
            return _read_table(table)
    return []


def get_v1_setting(settings_dict, *possible_keys):
    """Get a setting value by trying multiple possible key names."""
    for key in possible_keys:
        if key in settings_dict:
            return settings_dict[key]
        # Try case-insensitive
        for k, v in settings_dict.items():
            if isinstance(k, str) and k.lower() == key.lower():
                return v
    return None


def get_row_value(row, *possible_columns):
    """Get a value from a row dict by trying multiple possible column names."""
    for col in possible_columns:
        if col in row:
            return row[col]
        for k in row.keys():
            if isinstance(k, str) and k.lower() == col.lower():
                return row[k]
    return None
