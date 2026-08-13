from __future__ import annotations

from fastapi.testclient import TestClient
from starlette.responses import Response
from starlette.types import Message, Receive, Scope, Send

from insightforge.core.config import Settings
from insightforge.core.middleware import RequestBodyLimitMiddleware
from insightforge.main import create_app


def test_declared_oversized_request_is_rejected_before_body_parsing(test_settings) -> None:
    settings = test_settings.model_copy(
        update={
            "upload_max_bytes": 512 * 1024,
            "request_max_bytes": 1 * 1024 * 1024,
        }
    )
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/auth/login",
            content=b"{}",
            headers={"Content-Length": str(settings.request_max_bytes + 1)},
        )

    assert response.status_code == 413
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.json()["code"] == "request_too_large"


async def test_streamed_oversized_request_is_rejected_without_content_length() -> None:
    received_messages = iter(
        [
            {"type": "http.request", "body": b"123", "more_body": True},
            {"type": "http.request", "body": b"456", "more_body": False},
        ]
    )
    sent_messages: list[Message] = []

    async def receive() -> Message:
        return next(received_messages)

    async def send(message: Message) -> None:
        sent_messages.append(message)

    async def consume_request(scope: Scope, receive: Receive, send: Send) -> None:
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if not message.get("more_body", False):
                break
        await Response(status_code=204)(scope, receive, send)

    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/stream",
        "raw_path": b"/stream",
        "query_string": b"",
        "root_path": "",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    middleware = RequestBodyLimitMiddleware(consume_request, max_bytes=4)

    await middleware(scope, receive, send)

    response_start = next(
        message for message in sent_messages if message["type"] == "http.response.start"
    )
    response_body = b"".join(
        message.get("body", b"")
        for message in sent_messages
        if message["type"] == "http.response.body"
    )
    assert response_start["status"] == 413
    assert b'"code":"request_too_large"' in response_body


def test_production_responses_enable_hsts_and_host_prefixed_csrf_cookie() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        session_cookie_secure=True,
        allowed_origins=["https://app.example.com"],
        csrf_allowed_origins=["https://app.example.com"],
        allowed_hosts=["testserver"],
        csrf_signing_key="deployment-specific-signing-key-with-sufficient-entropy",
    )
    with TestClient(create_app(settings), base_url="https://testserver") as client:
        response = client.get("/api/v1/auth/csrf-token")

    assert response.status_code == 200
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    csrf_cookie = next(
        value
        for value in response.headers.get_list("set-cookie")
        if value.startswith("__Host-insightforge_csrf=")
    )
    assert "Secure" in csrf_cookie
    assert "Path=/" in csrf_cookie
