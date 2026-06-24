from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_health_endpoint_returns_healthy_status():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_redirects_to_api_docs():
    response = client.get("/", follow_redirects=False)

    assert response.status_code in {307, 308}
    assert response.headers["location"] == "/docs"


def test_favicon_request_does_not_log_not_found():
    response = client.get("/favicon.ico")

    assert response.status_code == 204
