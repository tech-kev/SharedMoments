"""HEIC/HEIF regression checks using generated images, never personal media."""

import importlib
from datetime import datetime
from io import BytesIO

import pytest
from PIL import Image


@pytest.mark.parametrize("extension", ["heic", "heif"])
def test_preserve_original_and_serve_jpeg_preview(admin_client, monkeypatch, tmp_path, extension):
    api = importlib.import_module("app.routes.api")
    images = tmp_path / "images"
    images.mkdir()
    monkeypatch.setattr(api, "_get_upload_folder", lambda ext: str(images))
    monkeypatch.setattr(api, "__file__", str(tmp_path / "app" / "routes" / "api.py"))

    original = BytesIO()
    Image.new("RGB", (32, 24), (25, 130, 210)).save(original, format="HEIF")
    original_bytes = original.getvalue()

    response = admin_client.post(
        "/api/v2/upload",
        data={"file": (BytesIO(original_bytes), f"sample.{extension}")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    filename = response.json["data"]["filename"]
    repeated = admin_client.post(
        "/api/v2/upload",
        data={"file": (BytesIO(original_bytes), f"sample.{extension}")},
        content_type="multipart/form-data",
    )
    assert repeated.status_code == 200
    assert repeated.json["data"]["filename"] != filename

    # Keep original encoded bytes available to download (no EXIF loss or recompression).
    assert (images / filename).read_bytes() == original_bytes
    assert admin_client.get(f"/api/v2/media/{filename}").data == original_bytes
    preview = admin_client.get(f"/api/v2/media/thumb/{filename}")
    assert preview.status_code == 200
    assert preview.mimetype == "image/jpeg"
    with Image.open(BytesIO(preview.data)) as decoded:
        assert decoded.size == (32, 24)

    # Cache is reused rather than rewriting image data on every view.
    api._ensure_heif_preview(filename)
    preview_path = tmp_path / "app" / "uploads" / "thumbs" / f"heif-{filename}.jpg"
    before = preview_path.stat().st_mtime_ns
    assert admin_client.get(f"/api/v2/media/thumb/{filename}").status_code == 200
    assert preview_path.stat().st_mtime_ns == before

    from app.utils import generate_lqip
    placeholder, width, height = generate_lqip(images / filename)
    assert placeholder.startswith("data:image/jpeg;base64,")
    assert (width, height) == (32, 24)

    from app.db_queries import create_item, create_item_share, delete_item

    item_id = create_item("Synthetic image", "Test only", "image", 1, filename, 2, datetime(2026, 1, 1))
    try:
        token = create_item_share(item_id, 2)["token"]
        shared = admin_client.get(f"/s/{token}/media/thumb/{filename}")
        assert shared.status_code == 200
        assert shared.mimetype == "image/jpeg"
        page = admin_client.get(f"/s/{token}")
        assert f"/s/{token}/media/thumb/{filename}".encode() in page.data
        assert admin_client.get(f"/s/invalid/media/thumb/{filename}").status_code == 404
    finally:
        delete_item(item_id)


def test_missing_heic_preview_does_not_create_files(admin_client):
    assert admin_client.get("/api/v2/media/thumb/absent.heic").status_code == 404


def test_non_heic_formats_are_unaffected(admin_client):
    assert admin_client.get("/api/v2/media/thumb/absent.mp4").status_code == 404
