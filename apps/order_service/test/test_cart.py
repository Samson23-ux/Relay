import httpx
import pytest
from uuid import uuid7


class TestCreateCart:
    @pytest.mark.asyncio
    async def test_create_cart(
        create_cart: httpx.Response, async_client: httpx.AsyncClient
    ):
        json_res = create_cart.json()

        assert create_cart.status_code == 201
        assert json_res["data"]["item"] == 1

    @pytest.mark.asyncio
    async def test_add_to_cart(
        create_cart: httpx.Response, async_client: httpx.AsyncClient
    ):
        cart_item: dict = {"product_id": uuid7(), "quantity": 5}

        cart_id = create_cart.json()["data"]["id"]
        res: httpx.Response = await async_client.post(
            "/carts", json=cart_item, params={"cart_id": cart_id}
        )

        json_res = res.json()

        assert res.status_code == 201
        assert json_res["data"]["item"] == 2

    @pytest.mark.asyncio
    async def test_item_exists(
        create_cart: httpx.Response, async_client: httpx.AsyncClient
    ):
        cart_item: dict = {
            "product_id": uuid7("019fb28c-2f33-7424-8e7d-7d91e8535857"),
            "quantity": 5,
        }

        cart_id = create_cart.json()["data"]["id"]
        res: httpx.Response = await async_client.post(
            "/carts", json=cart_item, params={"cart_id": cart_id}
        )

        assert res.status_code == 200


class TestGetCart:
    @pytest.mark.asyncio
    async def test_get_cart(
        create_cart: httpx.Response, async_client: httpx.AsyncClient
    ):
        cart_id = create_cart.json()["data"]["id"]
        res: httpx.Response = await async_client.get(f"/carts/{cart_id}")

        json_res = res.json()

        assert res.status_code == 200
        assert json_res["data"]["id"] == cart_id
        assert json_res["data"]["items"] == 1

    @pytest.mark.asyncio
    async def test_cart_not_found(async_client: httpx.AsyncClient):
        res: httpx.Response = await async_client.get(f"/carts/{uuid7()}")
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_get_cart_items(
        create_cart: httpx.Response, async_client: httpx.AsyncClient
    ):
        cart_id = create_cart.json()["data"]["id"]
        res: httpx.Response = await async_client.get(
            f"/carts/{cart_id}", params={"items": True}
        )

        json_res = res.json()

        assert res.status_code == 200
        assert json_res["data"]["quantity"] == 2
        assert json_res["data"]["product"]["name"] == "test_product"
        assert json_res["data"]["product"]["serial"] == "EumHUV41owYwmnzpjVKYng"

    @pytest.mark.asyncio
    async def test_get_carts(
        create_cart: httpx.Response, async_client: httpx.AsyncClient
    ):
        cart_id = create_cart.json()["data"]["id"]
        res: httpx.Response = await async_client.get("/carts")

        json_res = res.json()

        assert res.status_code == 200
        assert len(json_res["data"]) == 1
        assert json_res["data"][0]["id"] == cart_id

    @pytest.mark.asyncio
    async def test_get_carts_with_items(
        create_cart: httpx.Response, async_client: httpx.AsyncClient
    ):
        res: httpx.Response = await async_client.get("/carts", params={"items": True})

        json_res = res.json()

        assert res.status_code == 200
        assert len(json_res["data"]) == 1
        assert json_res["data"][0]["quantity"] == 2
        assert json_res["data"][0]["product"]["name"] == "test_product"
        assert json_res["data"][0]["product"]["serial"] == "EumHUV41owYwmnzpjVKYng"


class TestChangeItemQuantity:
    @pytest.mark.asyncio
    async def test_increment_item(async_client: httpx.AsyncClient):
        prd_id: str = "019fb2a6-6e68-77bb-b9b8-35db4e31ae1b"
        cart_item: dict = {
            "product_id": uuid7(prd_id),
            "quantity": 2,
        }

        create_res: httpx.Response = await async_client.post("/carts", json=cart_item)
        cart_id = create_res.json()["data"]["id"]

        res: httpx.Response = await async_client.patch(
            f"/carts/{cart_id}/products/{prd_id}/increment", params={"quantity": 2}
        )

        assert res.status_code == 200

        res: httpx.Response = await async_client.get(
            f"/carts/{cart_id}", params={"items": True}
        )

        json_res = res.json()

        assert res.status_code == 200
        assert json_res["data"]["quantity"] == 4

    @pytest.mark.asyncio
    async def test_decrement_item(async_client: httpx.AsyncClient):
        prd_id: str = "019fb2a6-6e68-77bb-b9b8-35db4e31ae1b"
        cart_item: dict = {
            "product_id": uuid7(prd_id),
            "quantity": 5,
        }

        create_res: httpx.Response = await async_client.post("/carts", json=cart_item)
        cart_id = create_res.json()["data"]["id"]

        res: httpx.Response = await async_client.patch(
            f"/carts/{cart_id}/products/{prd_id}/decrement", params={"quantity": 2}
        )

        assert res.status_code == 200

        res: httpx.Response = await async_client.get(
            f"/carts/{cart_id}", params={"items": True}
        )

        json_res = res.json()

        assert res.status_code == 200
        assert json_res["data"]["quantity"] == 3


class TestDeleteCart:
    @pytest.mark.asyncio
    async def test_delete_cart(
        create_cart: httpx.Response, async_client: httpx.AsyncClient
    ):
        cart_id = create_cart.json()["data"]["id"]

        res: httpx.Response = await async_client.delete(f"/carts/{cart_id}")
        assert res.status_code == 204

    @pytest.mark.asyncio
    async def test__cart_not_found(async_client: httpx.AsyncClient):
        res: httpx.Response = await async_client.delete(f"/carts/{uuid7()}")
        assert res.status_code == 404
