import httpx
import pytest
from uuid import uuid4
from datetime import datetime, timezone

FAKE_USER = {
    "id": str(uuid4()),
    "email": "user@example.com",
    "type": "email",
    "role": "user",
    "is_active": True,
    "is_verified": True,
    "created_at": str(datetime.now(timezone.utc)),
}


class TestSignUpWithEmail:
    @pytest.mark.asyncio(loop_scope="session")
    async def test_sign_up(self, async_client: httpx.AsyncClient, mock_request_class):
        sign_up_payload: dict = {
            "email": "user@example.com",
            "password": "test_user_password",
        }

        mock_request_class.post.return_value = httpx.Response(
            status_code=201,
            json={
                "message": (
                    "Sign up completed successfully."
                    "Check your email for verification code and instructions"
                )
            },
        )

        res: httpx.Response = await async_client.post(
            "/auth/signup",
            json=sign_up_payload,
        )

        json_res = res.json()

        assert res.status_code == 201
        assert json_res["message"] == (
            "Sign up completed successfully."
            "Check your email for verification code and instructions"
        )

        mock_request_class.post.assert_called_once


    @pytest.mark.asyncio(loop_scope="session")
    async def test_user_exists(
        self, async_client: httpx.AsyncClient, mock_request_class
    ):
        sign_up_payload: dict = {
            "email": "user@example.com",
            "password": "test_user_password",
        }

        mock_request_class.post.return_value = httpx.Response(
            status_code=409,
            json={
                "status": "error",
                "message": "User already exists with the provided email user@example.com",
            },
        )

        res: httpx.Response = await async_client.post(
            "/auth/signup",
            json=sign_up_payload,
            headers={"x-upstream": "relay"},
        )

        json_res = res.json()

        assert res.status_code == 409
        assert (
            json_res["message"]
            == "User already exists with the provided email user@example.com"
        )

        mock_request_class.post.assert_called_once


class TestGetCurrentUser:
    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_current_user(
        self, async_client: httpx.AsyncClient, login: httpx.Response, mock_request_class
    ):
        access_token = login.json()["data"]["access_token"]

        mock_request_class.get.return_value = httpx.Response(
            status_code=200,
            json={"message": "User retrieved successfully", "data": FAKE_USER},
        )

        res: httpx.Response = await async_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        json_res = res.json()

        assert res.status_code == 200
        assert "user@example.com" == json_res["data"]["email"]


class TestUnauthenticatedAndUnauthorized:
    @pytest.mark.asyncio(loop_scope="session")
    async def test_unauthenticated_user(self, async_client: httpx.AsyncClient):
        res: httpx.Response = await async_client.get("/auth/me")

        assert res.status_code == 401
        assert res.json() == "User not authenticated"

    @pytest.mark.asyncio(loop_scope="session")
    async def test_unauthorized_request(
        self, async_client: httpx.AsyncClient, login: httpx.Response
    ):
        access_token = login.json()["data"]["access_token"]

        res: httpx.Response = await async_client.post(
            "/products",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert res.status_code == 403
        assert res.json() == "User not authorized"


class TestUnknownEndpoint:
    @pytest.mark.asyncio(loop_scope="session")
    async def test_unknown_endpoint(self, async_client: httpx.AsyncClient):
        res: httpx.Response = await async_client.get("/users")

        assert res.status_code == 404
        assert res.json() == "Endpoint not found"


class TestRateLimit:
    @pytest.mark.asyncio(loop_scope="session")
    async def test_too_many_requests(self, async_client: httpx.AsyncClient):
        sign_up_payload: dict = {
            "email": "user@example.com",
            "password": "test_user_password",
        }

        for _ in range(11):
            res: httpx.Response = await async_client.post(
                "/auth/signup",
                json=sign_up_payload,
            )

        assert res.status_code == 429
        assert res.json() == "Rate limit exceeded"

class TestCircuitBreaker:
    @pytest.mark.asyncio(loop_scope="session")
    async def test_service_unaivailable(
        self, async_client: httpx.AsyncClient, mock_request_class
    ):
        sign_up_payload: dict = {
            "email": "user@example.com",
            "password": "test_user_password",
        }

        mock_request_class.post.side_effect = [
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(503),
        ]

        for _ in range(5):
            res: httpx.Response = await async_client.post(
                "/auth/signup",
                json=sign_up_payload,
            )

        assert res.status_code == 503
        assert mock_request_class.post.call_count == 5


class TestRetry:
    @pytest.mark.asyncio(loop_scope="session")
    async def test_retry_endpoint(
        self, async_client: httpx.AsyncClient, login: httpx.Response, mock_request_class
    ):
        access_token = login.json()["data"]["access_token"]

        mock_request_class.get.side_effect = [
            httpx.Timeout("request timeout"),
            httpx.ConnectError("connection refused"),
            httpx.Timeout("request timeout"),
            httpx.ConnectError("connection refused"),
        ]

        for _ in range(4):
            res: httpx.Response = await async_client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert res.status_code == 500
        assert mock_request_class.get.call_count == 4
