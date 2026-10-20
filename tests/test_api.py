from app.config import get_settings
from app.main import app


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_txt_success(client):
    response = client.post(
        "/documents",
        files={"file": ("notes.txt", b"hello", "text/plain")},
        data={"title": "Notes"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["size_bytes"] == 5
    assert body["content_type"] == "text/plain"


def test_upload_pdf_success(client):
    response = client.post(
        "/documents",
        files={"file": ("report.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert response.status_code == 201
    assert response.json()["content_type"] == "application/pdf"


def test_upload_saves_file(client, tmp_path):
    response = client.post(
        "/documents",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 201
    assert len(list(tmp_path.iterdir())) == 1


def test_upload_missing_file_422(client):
    response = client.post("/documents")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_upload_wrong_extension_415(client):
    response = client.post(
        "/documents",
        files={"file": ("picture.png", b"image", "image/png")},
    )
    assert response.status_code == 415


def test_upload_fake_pdf_422(client):
    response = client.post(
        "/documents",
        files={"file": ("fake.pdf", b"this is not a PDF", "application/pdf")},
    )
    assert response.status_code == 422


def test_upload_empty_file_422(client):
    response = client.post(
        "/documents",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert response.status_code == 422


def test_upload_too_large_413(client):
    response = client.post(
        "/documents",
        files={"file": ("big.txt", b"a" * (6 * 1024 * 1024), "text/plain")},
    )
    assert response.status_code == 413


def test_unknown_route_json_error(client):
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"

def test_request_id_header_present(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["X-Request-ID"]


def test_custom_request_id_is_echoed(client):
    response = client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert response.headers["X-Request-ID"] == "abc-123"