"""Tests für das Permission-System — Zugriffskontrolle."""


def test_admin_panel_admin(admin_client):
    """Admin → darf Admin-Panel aufrufen."""
    response = admin_client.get('/admin')
    assert response.status_code != 403


def test_admin_panel_adult(adult_client):
    """Adult → kein Zugang zum Admin-Panel (Redirect oder 403)."""
    response = adult_client.get('/admin')
    # Ohne 'Access Admin Panel' → Redirect zu Home
    assert response.status_code in (302, 403)


def test_unauthenticated_redirect(client):
    """Ohne JWT → Redirect zum Login auf geschützter Seite."""
    response = client.get('/home')
    assert response.status_code == 302
    assert '/login' in response.headers.get('Location', '')
