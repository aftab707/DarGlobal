from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.frontend import FrontendFiles


def test_frontend_serves_files_and_spa_without_masking_api_errors(tmp_path):
    (tmp_path / "index.html").write_text("<h1>Chat</h1>", encoding="utf-8")
    (tmp_path / "app.js").write_text("console.log('app')", encoding="utf-8")
    app = FastAPI()

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    app.mount("/", FrontendFiles(directory=tmp_path, html=True), name="frontend")
    client = TestClient(app)
    assert client.get("/").text == "<h1>Chat</h1>"
    assert client.get("/app.js").text == "console.log('app')"
    assert client.get("/conversation/1").text == "<h1>Chat</h1>"
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/missing").status_code == 404
    assert client.get("/api").status_code == 404
    assert client.get("/missing.js").status_code == 404
    assert client.post("/conversation/1").status_code == 405
