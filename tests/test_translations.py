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


def test_translations_put_admin_allowed(admin_client):
    """PUT als Admin → erlaubt."""
    response = admin_client.put('/api/v2/translations/en', data={
        'entityType': 'test',
        'entityID': '1',
        'fieldName': 'test_field',
        'translatedText': 'Test',
        'helpText': '',
    })
    assert response.status_code != 403
