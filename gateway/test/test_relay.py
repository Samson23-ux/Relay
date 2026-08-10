import respx
import httpx
import pytest
import secrets
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone


from apps.user_service.app.core.security import Security


def get_security_mock():
    payload: dict = {
        "sub": "randomfakeid",
        "name": "test_user",
        "email": "user@example.com",
    }

    refresh_token_payload: dict = {
        "email": "user@example.com",
        "user_type": "google",
        "refresh_token_id": str(uuid4()),
        "refresh_token": secrets.token_urlsafe(32),
        "refresh_token_expire_time": (datetime.now() + timedelta(days=1)).isoformat(),
    }

    token: dict = {"userinfo": payload}
    access_token: str = secrets.token_urlsafe(32)

    security = MagicMock(
        spec=Security()
    )  # pass an instance of the Security class to register instance attributes

    security.oauth.google.authorize_redirect = AsyncMock(return_value=None)
    security.oauth.google.authorize_access_token = AsyncMock(return_value=token)
    security.prepare_tokens = AsyncMock(
        return_value=(access_token, refresh_token_payload)
    )

    return security


FAKE_USER = {
    "id": uuid4(),
    "email": "user@example.com",
    "type": "email",
    "role": "user",
    "is_active": True,
    "is_verified": True,
    "created_at": datetime.now(timezone.utc),
}


class TestSignUpWithEmail:
    @pytest.mark.asyncio
    async def test_sign_up(self, async_client: httpx.AsyncClient):
        sign_up_payload: dict = {
            "email": "user@example.com",
            "password": "test_user_password",
        }

        route = respx.post("http://user-service@:8001/api/v1/auth/signup").mock(
            return_value=httpx.Response(
                status_code=201,
                json={
                    "message": (
                        "Sign up completed successfully."
                        "Check your email for verification code and instructions"
                    )
                },
            )
        )

        res: httpx.Response = await async_client.post(
            "/auth/signup",
            json=sign_up_payload,
        )

        json_res = res.json()
        req = route.calls[0].request

        assert route.called
        assert "x-trace-id" in req.headers
        assert req.headers["x-upstream"] == "user_service"

        assert res.status_code == 201
        assert json_res["message"] == (
            "Sign up completed successfully."
            "Check your email for verification code and instructions"
        )

    @pytest.mark.asyncio
    async def test_user_exists(self, async_client: httpx.AsyncClient):
        sign_up_payload: dict = {
            "email": "user@example.com",
            "password": "test_user_password",
        }

        route = respx.post("http://user-service@:8001/api/v1/auth/signup").mock(
            return_value=httpx.Response(
                status_code=409,
                json={
                    "status": "error",
                    "message": "User already exists with the provided email user@example.com",
                },
            )
        )

        res: httpx.Response = await async_client.post(
            "/auth/signup",
            json=sign_up_payload,
            headers={"x-upstream": "relay"},
        )

        assert route.called
        assert res.status_code == 409


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_get_current_user(
        self, async_client: httpx.AsyncClient, login: httpx.Response
    ):
        access_token = login.json()["data"]["access_token"]

        route = respx.get("http://user-service@:8001/api/v1/auth/me").mock(
            return_value=httpx.Response(
                status_code=200,
                json={"message": "User retrieved successfully", "data": FAKE_USER},
            )
        )

        res: httpx.Response = await async_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        json_res = res.json()
        req = route.calls[0].request

        assert res.status_code == 200
        assert "user@example.com" == json_res["data"]["email"]

        assert route.called
        assert req.headers["x-user-type"] == "email"
        assert req.headers["x-upstream"] == "user_service"
        assert req.headers["x-user-email"] == "user@example.com"


class TestUnauthenticatedAndUnauthorized:
    @pytest.mark.asyncio
    async def test_unauthenticated_user(self, async_client: httpx.AsyncClient):
        res: httpx.Response = await async_client.get("/auth/me")

        assert res.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthorized_request(
        self, async_client: httpx.AsyncClient, login: httpx.Response
    ):
        access_token = login.json()["data"]["access_token"]

        res: httpx.Response = await async_client.get(
            "/carts",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert res.status_code == 403


class TestUnknownEndpoint:
    @pytest.mark.asyncio
    async def test_unknown_endpoint(self, async_client: httpx.AsyncClient):
        res: httpx.Response = await async_client.get("/users")

        assert res.status_code == 404


class TestRateLimit:
    @pytest.mark.asyncio
    async def test_too_many_requests(self, async_client: httpx.AsyncClient):
        sign_up_payload: dict = {
            "email": "user@example.com",
            "password": "test_user_password",
        }

        route = respx.post("http://user-service@:8001/api/v1/auth/signup")

        route.side_effect = [
            httpx.Response(201),
            httpx.Response(201),
            httpx.Response(201),
            httpx.Response(201),
            httpx.Response(201),
            httpx.Response(201),
            httpx.Response(201),
            httpx.Response(201),
            httpx.Response(201),
            httpx.Response(201),
            httpx.Response(429),
        ]

        for _ in range(11):
            res: httpx.Response = await async_client.post(
                "/auth/signup",
                json=sign_up_payload,
            )

        assert res.status_code == 429
        assert route.call_count == 11


class TestCircuitBreaker:
    @pytest.mark.asyncio
    async def test_service_unaivailable(self, async_client: httpx.AsyncClient):
        sign_up_payload: dict = {
            "email": "user@example.com",
            "password": "test_user_password",
        }

        route = respx.post("http://user-service@:8001/api/v1/auth/signup")

        route.side_effect = [
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(503),
        ]

        for _ in range(6):
            res: httpx.Response = await async_client.post(
                "/auth/signup",
                json=sign_up_payload,
            )

        assert res.status_code == 503
        assert route.call_count == 6


class TestRetry:
    @pytest.mark.asyncio
    async def test_retry_endpoint(
        self, async_client: httpx.AsyncClient, login: httpx.Response
    ):
        access_token = login.json()["data"]["access_token"]

        route = respx.get("http://user-service@:8001/api/v1/auth/me")

        route.side_effect = [
            httpx.Timeout("request timeout"),
            httpx.ConnectError("connection refused"),
            httpx.Timeout("request timeout"),
            httpx.ConnectError("connection refused"),
        ]

        res: httpx.Response = await async_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert res.status_code == 500
        assert route.call_count == 4
