import httpx
import pytest
import secrets
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock, MagicMock


from apps.user_service.app.main import app
from apps.user_service.app.deps import get_security
from apps.user_service.app.core.security import Security


@pytest_asyncio.fixture(autouse=True)
async def mock_log_task():
    with (
        patch("apps.user_service.app.api.services.auth.save_log.apply_async"),
        patch("apps.user_service.app.api.services.user.save_log.apply_async"),
        patch("apps.user_service.app.api.services.email.save_log.apply_async"),
    ):
        yield


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


class TestSignUpWithEmail:
    @pytest.mark.asyncio
    async def test_sign_up(self, create_user: httpx.Response):
        json_res = create_user.json()

        assert create_user.status_code == 201
        assert json_res["message"] == (
            "Sign up completed successfully."
            "Check your email for verification code and instructions"
        )

    @pytest.mark.asyncio
    async def test_user_exists(self, async_client: httpx.AsyncClient, verify_user):
        sign_up_payload: dict = {
            "email": "user@example.com",
            "password": "test_user_password",
        }

        res: httpx.Response = await async_client.post(
            "/auth/signup", json=sign_up_payload
        )

        assert res.status_code == 409

    @pytest.mark.asyncio
    async def test_invalid_email(self, async_client: httpx.AsyncClient):
        sign_up_payload: dict = {
            "email": "invalid_user_email",
            "password": "test_user_password",
        }

        res: httpx.Response = await async_client.post(
            "/auth/signup", json=sign_up_payload
        )

        assert res.status_code == 422


class TestLogin:
    @pytest.mark.asyncio
    async def test_login(self, async_client: httpx.AsyncClient, login: httpx.Response):
        json_res = login.json()

        assert login.status_code == 201
        assert "access_token" in json_res["data"]

    @pytest.mark.asyncio
    async def test_user_not_verified(
        self, async_client: httpx.AsyncClient, create_user: httpx.Response
    ):
        login_payload: dict = {
            "email": "user@example.com",
            "password": "test_user_password",
        }

        res: httpx.Response = await async_client.post(
            "/auth/login",
            json=login_payload,
        )

        assert res.status_code == 400

    @pytest.mark.asyncio
    async def test_wrong_email_login(
        self, async_client: httpx.AsyncClient, verify_user
    ):
        login_payload: dict = {
            "email": "user@example123.com",
            "password": "test_user_password",
        }

        res: httpx.Response = await async_client.post(
            "/auth/login",
            json=login_payload,
        )

        assert res.status_code == 400


class TestSignUpWithGoogle:
    @pytest.mark.asyncio
    async def test_sign_in_google(self, async_client: httpx.AsyncClient):
        app.dependency_overrides[get_security] = lambda: get_security_mock()

        url_path: str = "apps.user_service.app.api.routers.user.Request.url_for"
        with patch(url_path, new_callable=AsyncMock) as url_patch:
            res: httpx.Response = await async_client.get("/auth/google")

        assert res.status_code == 302

        url_patch.assert_called_once()

    @pytest.mark.asyncio
    async def test_google_callback(self, async_client: httpx.AsyncClient):
        app.dependency_overrides[get_security] = lambda: get_security_mock()

        res: httpx.Response = await async_client.get("/auth/google/callback")

        json_res = res.json()

        assert res.status_code == 200
        assert "access_token" in json_res["data"]


class TestAuthToken:
    @pytest.mark.asyncio
    async def test_get_access_token(
        self, async_client: httpx.AsyncClient, login: httpx.Response
    ):
        res = await async_client.post(
            "/auth/refresh",
        )
        json_res = res.json()

        assert res.status_code == 201
        assert "access_token" in json_res["data"]

    @pytest.mark.asyncio
    async def test_unauthorized_get_access_token(
        self, async_client: httpx.AsyncClient, verify_user
    ):
        res = await async_client.post(
            "/auth/refresh",
        )

        assert res.status_code == 401


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_get_current_user(self, async_client: httpx.AsyncClient, verify_user):
        res: httpx.Response = await async_client.get(
            "/auth/me",
            headers={
                "X-USER-TYPE": "email",
                "X-USER-EMAIL": "user@example.com",
            },
        )

        json_res = res.json()

        assert res.status_code == 200
        assert "user@example.com" == json_res["data"]["email"]


class TestResendOtp:
    @pytest.mark.asyncio
    async def test_resend_otp_token(
        self, async_client: httpx.AsyncClient, create_user: httpx.Response
    ):
        path: str = (
            "apps.user_service.app.api.services.auth.send_verification_email.apply_async"
        )

        resend_otp_payload: dict = {
            "email": "user@example.com",
        }

        with patch(path) as email_patch:
            res: httpx.Response = await async_client.post(
                "/auth/verify/resend",
                json=resend_otp_payload,
            )

        json_res = res.json()

        email_patch.assert_called_once()

        assert res.status_code == 201
        assert json_res["status"] == "success"

    @pytest.mark.asyncio
    async def test_invalid_email_otp_token(
        self, async_client: httpx.AsyncClient, create_user: httpx.Response
    ):
        resend_otp_payload: dict = {
            "email": "user@example123.com",
        }

        res: httpx.Response = await async_client.post(
            "/auth/verify/resend",
            json=resend_otp_payload,
        )

        assert res.status_code == 400


class TestLogout:
    @pytest.mark.asyncio
    async def test_logout(self, async_client: httpx.AsyncClient, login):
        res = await async_client.post(
            "/auth/logout",
            headers={
                "X-USER-TYPE": "email",
                "X-USER-EMAIL": "user@example.com",
            },
        )

        assert res.status_code == 201


class TestDeleteAccount:
    @pytest.mark.asyncio
    async def test_delete_account(self, async_client: httpx.AsyncClient, login):
        res = await async_client.delete(
            "/auth",
            headers={
                "X-USER-TYPE": "email",
                "X-USER-EMAIL": "user@example.com",
            },
        )

        assert res.status_code == 204

        login_payload: dict = {
            "email": "user@example.com",
            "password": "test_user_password",
        }

        res: httpx.Response = await async_client.post(
            "/auth/login",
            json=login_payload,
        )

        assert res.status_code == 400
