"""Deleting an account must not transfer old sessions or shared history."""
from datetime import datetime, timedelta, timezone
import jwt
from sqlalchemy import create_engine

from app.models import Item, Role, SessionLocal, User, UserRole


def test_additive_tombstone_column_on_existing_database(tmp_path):
    from app.models import _ensure_deleted_user_column
    db = create_engine(f'sqlite:///{tmp_path / "legacy.db"}')
    with db.begin() as conn:
        conn.exec_driver_sql('CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT)')
    _ensure_deleted_user_column(db)
    _ensure_deleted_user_column(db)
    with db.connect() as conn:
        assert 'deletedAt' in {
            row[1] for row in conn.exec_driver_sql('PRAGMA table_info(users)')
        }
    db.dispose()


def test_deleted_user_cannot_reauthenticate_or_be_reassigned(
        app, admin_client):
    from app.db_queries import get_items_by_type, get_user_by_email
    db = SessionLocal()
    try:
        former = User(firstName='Synthetic', lastName='Former',
                      email='former-synthetic@example.invalid')
        former.hash_password('test-only')
        db.add(former)
        db.flush()
        old_id = former.id
        role = db.query(Role).filter_by(roleName='Adult').one()
        db.add(UserRole(userID=old_id, roleID=role.id))
        item = Item(title='Shared synthetic family memory', contentType='text',
                    listType=1, edition='all', createdByUser=old_id)
        db.add(item)
        db.commit()
        item_id = item.id
    finally:
        db.close()
    client = app.test_client()
    token = jwt.encode(
        {'user_id': old_id, 'exp': datetime.now(timezone.utc) + timedelta(days=1)},
        app.config['SECRET_KEY'], algorithm='HS256')
    client.set_cookie('jwt_token', token)
    assert client.get('/home').status_code == 200
    try:
        assert admin_client.delete(f'/api/v2/admin/users/{old_id}').status_code == 200
        assert client.get('/home').status_code == 302
        assert get_user_by_email('former-synthetic@example.invalid') is None
        reset_token = jwt.encode({
            'user_id': old_id, 'purpose': 'password_reset',
            'exp': datetime.now(timezone.utc) + timedelta(minutes=10)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        assert b'invalid' in client.get(f'/reset-password/{reset_token}').data.lower()
        db = SessionLocal()
        try:
            tombstone = db.get(User, old_id)
            assert tombstone.deletedAt is not None
            assert tombstone.email is None and tombstone.passwordHash is None
            assert tombstone.firstName == 'Former member'
            newcomer = User(firstName='New', email='new-synthetic@example.invalid')
            newcomer.hash_password('test-only')
            db.add(newcomer)
            db.flush()
            assert newcomer.id != old_id
            db.rollback()
        finally:
            db.close()
        found = [(memory, author) for memory, author in get_items_by_type(1)
                 if memory.id == item_id]
        assert len(found) == 1 and found[0][1].firstName == 'Former member'
    finally:
        db = SessionLocal()
        try:
            db.query(Item).filter_by(id=item_id).delete()
            db.query(UserRole).filter_by(userID=old_id).delete()
            db.query(User).filter_by(id=old_id).delete()
            db.commit()
        finally:
            db.close()
