"""Tests für den AI-Enhance Endpoint — Auth, Permissions, Validierung."""


def test_enhance_no_auth(client):
    """Ohne JWT → Redirect zum Login."""
    response = client.post('/api/v2/ai/enhance', data={'text': 'test'})
    assert response.status_code == 302


def test_enhance_no_text(admin_client):
    """Leerer Text → Error-Event im SSE-Stream."""
    response = admin_client.post('/api/v2/ai/enhance', data={'text': ''})
    assert response.status_code == 200
    assert 'text/event-stream' in response.content_type
    data = response.get_data(as_text=True)
    assert 'No text provided' in data
    assert '[DONE]' in data


def test_enhance_adult_allowed(adult_client):
    """Adult hat Create+Update Item → darf AI nutzen."""
    response = adult_client.post('/api/v2/ai/enhance', data={'text': 'test'})
    # Sollte kein 403 sein (AI-Provider fehlt, aber Permission ist OK)
    assert response.status_code != 403


def test_enhance_child_allowed(child_client):
    """Child hat Create Item → darf AI nutzen."""
    response = child_client.post('/api/v2/ai/enhance', data={'text': 'test'})
    assert response.status_code != 403
