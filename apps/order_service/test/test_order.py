import httpx
import pytest
import pytest_asyncio
from uuid import uuid7
from unittest.mock import patch


@pytest_asyncio.fixture(autouse=True)
async def mock_process_reservation():
    with (
        patch(
            "apps.order_service.app.utils.process_reservation.apply_async"
        ) as prd_mock,
        patch(
            "apps.order_service.app.utils.restore_product_quantity.apply_async"
        ) as restore_mock,
    ):
        prd_mock.return_value.get.return_value = {"span_id": str(uuid7())}
        restore_mock.return_value.get.return_value = {"span_id": str(uuid7())}

        yield

    prd_mock.assert_called()


class TestCreateOrder:
    @pytest.mark.asyncio
    async def test_create_order(self, create_order: httpx.Response):
        json_res = create_order.json()

        assert create_order.status_code == 201
        assert json_res["data"]["status"] == "confirmed"
        assert json_res["data"]["total_price"] == "100.00"
        assert json_res["data"]["user_id"] == "019fbd28-ea23-76ef-b14a-64a857bc11f3"

    @pytest.mark.asyncio
    async def test_cart_not_found(
        self,
        create_order: httpx.Response,
        async_client: httpx.AsyncClient,
    ):
        cart_id = str(uuid7())
        res: httpx.Response = await async_client.post(
            "/orders", params={"cart_id": cart_id}
        )

        assert res.status_code == 404


class TestGetOrder:
    @pytest.mark.asyncio
    async def test_get_order(
        self, create_order: httpx.Response, async_client: httpx.AsyncClient
    ):
        order_id = create_order.json()["data"]["id"]
        res: httpx.Response = await async_client.get(f"/orders/{order_id}")

        json_res = res.json()

        assert res.status_code == 200
        assert json_res["data"]["id"] == order_id
        assert json_res["data"]["status"] == "confirmed"

    @pytest.mark.asyncio
    async def test_order_not_found(
        self, create_order: httpx.Response, async_client: httpx.AsyncClient
    ):
        res: httpx.Response = await async_client.get(f"/orders/{str(uuid7())}")
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_get_order_items(
        self,
        create_order: httpx.Response,
        async_client: httpx.AsyncClient,
    ):
        order_id = create_order.json()["data"]["id"]
        res: httpx.Response = await async_client.get(
            f"/orders/{order_id}", params={"items": True}
        )

        json_res = res.json()

        assert res.status_code == 200
        assert json_res["data"][0]["product"]["name"] == "test_product"
        assert json_res["data"][0]["product"]["serial"] == "EumHUV41owYwmnzpjVKYng"

    @pytest.mark.asyncio
    async def test_get_orders(
        self, create_order: httpx.Response, async_client: httpx.AsyncClient
    ):
        order_id = create_order.json()["data"]["id"]
        res: httpx.Response = await async_client.get("/orders")

        json_res = res.json()

        assert res.status_code == 200
        assert len(json_res["data"]) == 1
        assert json_res["data"][0]["id"] == order_id

    @pytest.mark.asyncio
    async def test_get_orders_with_items(
        self,
        create_order: httpx.Response,
        async_client: httpx.AsyncClient,
    ):
        res: httpx.Response = await async_client.get("/orders", params={"items": True})

        json_res = res.json()

        assert res.status_code == 200
        assert len(json_res["data"]) == 1
        assert json_res["data"][0]["product"]["name"] == "test_product"
        assert json_res["data"][0]["product"]["serial"] == "EumHUV41owYwmnzpjVKYng"


class TestDeleteOrder:
    @pytest.mark.asyncio
    async def test_delete_order(
        self, create_order: httpx.Response, async_client: httpx.AsyncClient
    ):
        order_id = create_order.json()["data"]["id"]

        res: httpx.Response = await async_client.delete(f"/orders/{order_id}")
        assert res.status_code == 204

    @pytest.mark.asyncio
    async def test_order_not_found(
        self, create_order: httpx.Response, async_client: httpx.AsyncClient
    ):
        res: httpx.Response = await async_client.delete(f"/orders/{str(uuid7())}")
        assert res.status_code == 404
