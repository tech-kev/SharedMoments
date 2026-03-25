"""
Shared test fixtures for the SharedMoments test suite.
"""
import os
import tempfile
import pytest
import jwt as pyjwt
from datetime import datetime, timedelta, timezone

# Temp-DB-Datei erstellen — alle Engines teilen dieselbe Datei-DB
_test_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_test_db.close()
os.environ['DATABASE_URL'] = f'sqlite:///{_test_db.name}'

# Secret Key für JWT — muss VOR App-Import gesetzt sein
os.environ['SECRET_KEY'] = 'test-secret-key-that-is-long-enough-for-hmac'

# AI-Keys entfernen damit Tests nicht echte APIs aufrufen
os.environ.pop('OPENAI_API_KEY', None)
os.environ.pop('ANTHROPIC_API_KEY', None)
os.environ.pop('OLLAMA_BASE_URL', None)


@pytest.fixture(scope='session')
def app():
    """Flask-App mit Test-Datenbank."""
    from app import app as flask_app
    from app.models import Base, engine, SessionLocal
    from app.db_queries import init_db

    flask_app.config['TESTING'] = True
    flask_app.config['SECRET_KEY'] = 'test-secret-key-that-is-long-enough-for-hmac'

    with flask_app.app_context():
        Base.metadata.create_all(engine)
        init_db()

        # Setup als abgeschlossen markieren (sonst Redirect zu /setup)
        from app.models import Setting
        session = SessionLocal()
        try:
            setting = session.query(Setting).filter_by(name='setup_complete').first()
            setting.value = 'True'
            session.commit()
        finally:
            session.close()

        _create_test_users()
        yield flask_app
        Base.metadata.drop_all(engine)

    # Temp-DB aufräumen
    try:
        os.unlink(_test_db.name)
    except OSError:
        pass


@pytest.fixture()
def client(app):
    """Unauthentifizierter Test-Client."""
    return app.test_client()


@pytest.fixture()
def admin_client(app):
    """Test-Client mit Admin-JWT (alle Permissions)."""
    return _make_auth_client(app, user_id=2)


@pytest.fixture()
def adult_client(app):
    """Test-Client mit Adult-JWT (Create/Read/Update/Delete Item)."""
    return _make_auth_client(app, user_id=3)


@pytest.fixture()
def child_client(app):
    """Test-Client mit Child-JWT (nur Create + Read Item)."""
    return _make_auth_client(app, user_id=4)


def _make_auth_client(app, user_id):
    """Erstellt einen Test-Client mit gültigem JWT-Cookie."""
    client = app.test_client()
    token = pyjwt.encode(
        {'user_id': user_id, 'exp': datetime.now(timezone.utc) + timedelta(hours=1)},
        app.config['SECRET_KEY'],
        algorithm='HS256',
    )
    client.set_cookie('jwt_token', token)
    return client


def _create_test_users():
    """Erstellt Admin-, Adult- und Child-User und weist Rollen zu."""
    from app.models import User, Role, UserRole, SessionLocal

    session = SessionLocal()
    try:
        admin_role = session.query(Role).filter_by(roleName='Admin').first()
        adult_role = session.query(Role).filter_by(roleName='Adult').first()
        child_role = session.query(Role).filter_by(roleName='Child').first()

        admin_user = User(email='admin@test.com', firstName='Admin', lastName='Test')
        admin_user.hash_password('testpass')
        session.add(admin_user)
        session.flush()

        adult_user = User(email='adult@test.com', firstName='Adult', lastName='Test')
        adult_user.hash_password('testpass')
        session.add(adult_user)
        session.flush()

        child_user = User(email='child@test.com', firstName='Child', lastName='Test')
        child_user.hash_password('testpass')
        session.add(child_user)
        session.flush()

        session.add(UserRole(userID=admin_user.id, roleID=admin_role.id))
        session.add(UserRole(userID=adult_user.id, roleID=adult_role.id))
        session.add(UserRole(userID=child_user.id, roleID=child_role.id))

        session.commit()
    finally:
        session.close()
