from fastapi.testclient import TestClient

from app.main import app


def test_root_serves_built_frontend_when_dist_exists():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "SH-2 Fastening Optimizer" in response.text
