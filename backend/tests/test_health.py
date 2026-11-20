import asyncio

import httpx

from app.main import app


def test_health_reports_not_ready_until_index_exists():
    async def request_health():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/api/health")

    response = asyncio.run(request_health())

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "index_ready": False}
