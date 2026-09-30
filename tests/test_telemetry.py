"""Check status recording and route labels without starting an exporter."""
import asyncio

import pytest

from app import telemetry


@pytest.mark.parametrize("status", [200, 404, 500])
def test_outcome_is_recorded_with_the_route_template(monkeypatch, status):
    calls = []

    class Counter:
        def add(self, value, attributes):
            calls.append((value, attributes.copy()))

    monkeypatch.setattr(telemetry, "counter", Counter())

    async def endpoint(scope, receive, send):
        if status == 500:
            raise ValueError("synthetic failure")
        await send({"type": "http.response.start", "status": status, "headers": []})

    async def send(message):
        pass

    scope = {"type": "http", "path": "/api/orders/synthetic-id", "method": "GET"}
    request = telemetry.TelemetryMiddleware(endpoint)(scope, None, send)
    if status == 500:
        with pytest.raises(ValueError):
            asyncio.run(request)
    else:
        asyncio.run(request)
    assert calls == [(1, {"http.route": "/api/orders/{order_id}",
                          "http.request.method": "GET", "http.response.status_code": status})]
