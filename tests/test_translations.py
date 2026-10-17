"""Tests für den Translations-Endpoint — GET ohne, PUT mit Permission."""


def test_translations_get_no_auth(client):
    """GET ohne JWT → Redirect."""
    response = client.get('/api/v2/translations/en')
    assert response.status_code == 302


def test_translations_get_adult(adult_client):
    """GET als Adult (ohne Manage Translations) → erlaubt (kein 403)."""
    with adult_client.session_transaction() as sess:
        sess['lang'] = 'en'
    response = adult_client.get('/api/v2/translations/currentLang')
    assert response.status_code != 403


def test_translations_put_adult_forbidden(adult_client):
    """PUT als Adult → 403 (braucht Manage Translations)."""
    response = adult_client.put('/api/v2/translations/en', data={
        'entityType': 'test',
        'entityID': '1',
        'fieldName': 'test_field',
        'translatedText': 'Test',
        'helpText': '',
    })
    assert response.status_code == 403


def test_translations_put_admin_forbidden_by_default(admin_client):
    """The default Admin role intentionally lacks Manage Translations."""
    response = admin_client.put('/api/v2/translations/en', data={
        'entityType': 'test',
        'entityID': '1',
        'fieldName': 'test_field',
        'translatedText': 'Test',
        'helpText': '',
    })
    assert response.status_code == 403
    assert response.json['data']['error_code'] == 403
    assert admin_client.get('/api/v2/translations').status_code == 403


def test_translations_put_admin_allowed_after_explicit_permission_grant(admin_client):
    """A granted permission enables editing without bypassing access controls."""
    from app.models import Permission, Role, RolePermission, SessionLocal, Translation
    from app.translation import load_translation_in_cache

    db = SessionLocal()
    role = db.query(Role).filter_by(roleName='Admin').one()
    permission = db.query(Permission).filter_by(permissionName='Manage Translations').one()
    translation_filter = dict(
        entityType='ui', entityID=0, languageCode='en-US', fieldName='Home'
    )
    translation = db.query(Translation).filter_by(**translation_filter).one()
    original_text, original_help = translation.translatedText, translation.helpText

    # Keep the upstream default policy and grant only within this synthetic test.
    assert db.get(RolePermission, (role.id, permission.id)) is None
    try:
        db.add(RolePermission(roleID=role.id, permissionID=permission.id))
        db.commit()

        response = admin_client.put('/api/v2/translations/en-US', data={
            'entityType': 'ui',
            'entityID': '0',
            'fieldName': 'Home',
            'translatedText': 'Synthetic translated home',
            'helpText': '',
        })
        assert response.status_code == 200
        assert response.json['status'] == 'success'

        db.expire_all()
        assert (
            db.query(Translation).filter_by(**translation_filter).one().translatedText
            == 'Synthetic translated home'
        )
        assert admin_client.get('/api/v2/translations').status_code == 200
    finally:
        db.query(Translation).filter_by(**translation_filter).update({
            'translatedText': original_text,
            'helpText': original_help,
        }, synchronize_session=False)
        db.query(RolePermission).filter_by(
            roleID=role.id, permissionID=permission.id
        ).delete(synchronize_session=False)
        db.commit()
        db.close()
        load_translation_in_cache()
