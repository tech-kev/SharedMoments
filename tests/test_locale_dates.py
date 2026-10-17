"""Synthetic tests for per-user language and date presentation."""

import json
from datetime import date
from pathlib import Path

import pytest
from flask import session


@pytest.mark.parametrize(
    ("date_format", "expected"),
    [
        ("locale", "17/10/2026"),
        ("dd/MM/yyyy", "17/10/2026"),
        ("MM/dd/yyyy", "10/17/2026"),
        ("dd MMM yyyy", "17 Oct 2026"),
        ("yyyy-MM-dd", "2026-10-17"),
    ],
)
def test_australian_date_formats(app, date_format, expected):
    from app.filters import format_date_dmy, format_string_date_dmy

    with app.test_request_context("/"):
        session["lang"] = "en-AU"
        session["date_format"] = date_format
        assert format_date_dmy(date(2026, 10, 17)) == expected
        assert format_string_date_dmy("2026-10-17") == expected


def test_default_uses_existing_date_presentation(app):
    from app.filters import format_date_dmy, format_string_date_dmy

    with app.test_request_context("/"):
        session["lang"] = "en-US"
        assert format_date_dmy(date(2026, 10, 17)) == "10/17/26"
        assert format_string_date_dmy("2026-10-17") == "10/17/2026"


def test_background_locale_defaults_without_request_context(app):
    from app.translation import _
    from app.filters import format_date_dmy
    with app.app_context():
        assert _("Moments") == "Moments"
        assert format_date_dmy(date(2026, 10, 17)) == "10/17/26"


def test_user_locale_does_not_change_process_locale(app, monkeypatch):
    from app.translation import _, set_locale

    monkeypatch.setenv("LANG", "unchanged")
    with app.test_request_context("/"):
        set_locale(2)
        assert session["lang"] == "en-US"
        assert session["date_format"] == "locale"
        session["lang"] = "de-DE"
        assert _("Moments") == "Momente"
        with app.test_request_context("/"):
            session["lang"] = "en-US"
            assert _("Moments") == "Moments"
        assert _("Moments") == "Momente"
    assert __import__("os").environ["LANG"] == "unchanged"


def test_date_format_can_be_saved_without_affecting_other_users(app, admin_client):
    from app.db_queries import get_user_setting

    response = admin_client.put(
        "/api/v2/user-settings",
        data={"setting": "date_format", "value": "dd/MM/yyyy"},
    )
    assert response.status_code == 200
    assert get_user_setting(2, "date_format").value == "dd/MM/yyyy"
    assert get_user_setting(3, "date_format") is None
    try:
        page = admin_client.get("/user-settings")
        assert page.status_code == 200
        assert b'value="dd/MM/yyyy" selected' in page.data
    finally:
        admin_client.put(
            "/api/v2/user-settings",
            data={"setting": "date_format", "value": "locale"},
        )


def test_invalid_date_format_is_rejected(admin_client):
    response = admin_client.put(
        "/api/v2/user-settings",
        data={"setting": "date_format", "value": "<script>"},
    )
    assert response.status_code == 400


def test_australian_translation_is_complete():
    directory = Path(__file__).resolve().parents[1] / "app" / "translations"
    english = json.loads((directory / "en-US.json").read_text(encoding="utf-8"))
    australian = json.loads((directory / "en-AU.json").read_text(encoding="utf-8"))

    assert [entry["fieldName"] for entry in australian] == [
        entry["fieldName"] for entry in english
    ]
    assert all(entry["languageCode"] == "en-AU" for entry in australian)


def test_australian_language_is_loaded_on_startup(app):
    from app.db_queries import get_supported_languages
    from app.translation import migrateTranslations

    migrateTranslations()
    assert "en-AU" in get_supported_languages()
