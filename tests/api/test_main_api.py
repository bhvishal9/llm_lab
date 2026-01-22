from fastapi.testclient import TestClient


class TestMainApi:
    def test_health_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_echo_roundtrip(self, client: TestClient) -> None:
        payload = {"name": "Vishal"}
        response = client.post("/echo", json=payload)
        assert response.status_code == 200
        assert response.json() == payload

    def test_echo_invalid_body_returns_422(self, client: TestClient) -> None:
        # Missing required field "name"
        response = client.post("/echo", json={})
        assert response.status_code == 422
