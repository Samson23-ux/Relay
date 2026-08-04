import httpx
import pytest
from uuid import uuid7


class TestCreateProduct:
    @pytest.mark.asyncio
    async def test_create_product(self, mock_log_task, create_product: httpx.Response):
        assert create_product.status_code == 201
        assert create_product.json()["data"]["name"] == "test_product"
        assert create_product.json()["data"]["serial"] == "EumHUV41owYwmnzpjVKYng"

    @pytest.mark.asyncio
    async def test_invalid_payload(self, async_client: httpx.AsyncClient):
        product_create: dict = {
            "name": "test_product",
            "description": "description",
            "serial": "EumHUV41owYwmnzpjVKYng",
            "price": "50.00",
            "quantity": "15",
        }

        res: httpx.Response = await async_client.post(
            "/products",
            json=product_create,
        )

        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_product_exist(
        self,
        mock_log_task,
        create_product: httpx.Response,
        async_client: httpx.AsyncClient,
    ):
        product_create: dict = {
            "name": "Test_product",
            "description": "This is a fake test product.",
            "serial": "EumHUV41owYwmnzpjVKYng",
            "price": "10.00",
            "quantity": "5",
        }

        res: httpx.Response = await async_client.post(
            "/products",
            json=product_create,
        )

        assert res.status_code == 409


class TestGetProduct:
    @pytest.mark.asyncio
    async def test_get_product(
        self,
        mock_log_task,
        create_product: httpx.Response,
        async_client: httpx.AsyncClient,
    ):
        product_id = create_product.json()["data"]["id"]

        res: httpx.Response = await async_client.get(f"/products/{product_id}")

        json_res = res.json()

        assert res.status_code == 200
        assert json_res["data"]["name"] == "test_product"
        assert json_res["data"]["serial"] == "EumHUV41owYwmnzpjVKYng"

    @pytest.mark.asyncio
    async def test_get_all_product(
        self,
        mock_log_task,
        create_product: httpx.Response,
        async_client: httpx.AsyncClient,
    ):
        res: httpx.Response = await async_client.get("/products/all")

        json_res = res.json()

        assert res.status_code == 200
        assert len(json_res["data"]) == 1
        assert json_res["data"][0]["name"] == "test_product"
        assert json_res["data"][0]["serial"] == "EumHUV41owYwmnzpjVKYng"

    @pytest.mark.asyncio
    async def test_get_products(
        self,
        mock_log_task,
        create_product: httpx.Response,
        async_client: httpx.AsyncClient,
    ):
        res: httpx.Response = await async_client.get("/products")

        json_res = res.json()

        assert res.status_code == 200
        assert len(json_res["data"]) == 1
        assert json_res["data"][0]["name"] == "test_product"
        assert json_res["data"][0]["serial"] == "EumHUV41owYwmnzpjVKYng"

    @pytest.mark.asyncio
    async def test_product_not_found(
        self, mock_log_task, async_client: httpx.AsyncClient
    ):
        product_id = uuid7()

        res: httpx.Response = await async_client.get(f"/products/{product_id}")
        assert res.status_code == 404


class TestUpdateProduct:
    @pytest.mark.asyncio
    async def test_update_product(
        self,
        mock_log_task,
        create_product: httpx.Response,
        async_client: httpx.AsyncClient,
    ):
        product_id = create_product.json()["data"]["id"]
        product_update: dict = {"quantity": 22}

        res: httpx.Response = await async_client.patch(
            f"/products/{product_id}", json=product_update
        )

        json_res = res.json()

        assert res.status_code == 200
        assert json_res["data"]["quantity"] == 22

    @pytest.mark.asyncio
    async def test_product_not_found(
        self, mock_log_task, async_client: httpx.AsyncClient
    ):
        product_id = uuid7()
        product_update: dict = {"quantity": 22}

        res: httpx.Response = await async_client.patch(
            f"/products/{product_id}", json=product_update
        )
        assert res.status_code == 404


class TestDeleteProduct:
    @pytest.mark.asyncio
    async def test_delete_product(
        self,
        mock_log_task,
        create_product: httpx.Response,
        async_client: httpx.AsyncClient,
    ):
        product_id = create_product.json()["data"]["id"]

        res: httpx.Response = await async_client.delete(f"/products/{product_id}")
        assert res.status_code == 204

    @pytest.mark.asyncio
    async def test_product_not_found(self, async_client: httpx.AsyncClient):
        product_id = uuid7()

        res: httpx.Response = await async_client.delete(f"/products/{product_id}")
        assert res.status_code == 404
