import httpx
import pytest
import pytest_asyncio
from uuid import UUID, uuid7
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


from apps.order_service.app.main import app
from shared.repo.redis import RedisRepository
from apps.order_service.app.deps import get_cart_item_service
from apps.product_service.app.api.schemas.product import ProductItem
from apps.order_service.app.api.repo.cart_item import CartItemRepository
from apps.order_service.app.api.services.cart_item import CartItemService
from apps.order_service.app.api.schemas.cart_item import CartItemResponse

product = {
    "id": "019fb2f7-2003-74d1-91fb-79bcb506c77f",
    "name": "test_product",
    "description": "This is a fake test product.",
    "serial": "EumHUV41owYwmnzpjVKYng",
    "price": "50.00",
    "quantity": 50,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "updated_at": datetime.now(timezone.utc).isoformat(),
}


@pytest_asyncio.fixture(autouse=True)
async def mock_get_product():
    with patch(
        "apps.order_service.app.api.services.cart.get_product.apply_async"
    ) as prd_mock:
        prd_mock.return_value = {"span_id": str(uuid7()), "data": product}

        yield

    prd_mock.assert_called()


class TestCreateCart:
    @pytest.mark.asyncio
    async def test_create_cart(
        self,
        create_cart: httpx.Response,
        async_client: httpx.AsyncClient,
    ):
        json_res = create_cart.json()

        assert create_cart.status_code == 201
        assert json_res["data"]["items"] == 1

    @pytest.mark.asyncio
    async def test_add_to_cart(
        self,
        create_cart: httpx.Response,
        async_client: httpx.AsyncClient,
    ):
        cart_item: dict = {
            "product_id": "019fbd53-b8da-75fc-904e-b1d70c2e2c6e",
            "quantity": 5,
        }

        cart_id = create_cart.json()["data"]["id"]
        res: httpx.Response = await async_client.post(
            "/carts", json=cart_item, params={"cart_id": cart_id}
        )

        json_res = res.json()

        assert res.status_code == 201
        assert json_res["data"]["items"] == 2

    @pytest.mark.asyncio
    async def test_item_exists(
        self,
        create_cart: httpx.Response,
        async_client: httpx.AsyncClient,
    ):
        cart_item: dict = {
            "product_id": str(UUID("019fb2f7-2003-74d1-91fb-79bcb506c77f")),
            "quantity": 5,
        }

        cart_id = create_cart.json()["data"]["id"]
        res: httpx.Response = await async_client.post(
            "/carts", json=cart_item, params={"cart_id": cart_id}
        )

        assert res.status_code == 201


class TestGetCart:
    @pytest.mark.asyncio
    async def test_get_cart(
        self, create_cart: httpx.Response, async_client: httpx.AsyncClient
    ):
        cart_id = create_cart.json()["data"]["id"]
        res: httpx.Response = await async_client.get(f"/carts/{cart_id}")

        json_res = res.json()

        assert res.status_code == 200
        assert json_res["data"]["id"] == cart_id
        assert json_res["data"]["items"] == 1

    @pytest.mark.asyncio
    async def test_cart_not_found(
        self, create_cart: httpx.Response, async_client: httpx.AsyncClient
    ):
        res: httpx.Response = await async_client.get(f"/carts/{str(uuid7())}")
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_get_cart_items(
        self,
        create_cart: httpx.Response,
        async_client: httpx.AsyncClient,
    ):
        cart_id = create_cart.json()["data"]["id"]
        res: httpx.Response = await async_client.get(
            f"/carts/{cart_id}", params={"items": True}
        )

        json_res = res.json()

        assert res.status_code == 200
        assert json_res["data"][0]["quantity"] == 2
        assert json_res["data"][0]["product"]["name"] == "test_product"
        assert json_res["data"][0]["product"]["serial"] == "EumHUV41owYwmnzpjVKYng"

    @pytest.mark.asyncio
    async def test_get_carts(
        self, create_cart: httpx.Response, async_client: httpx.AsyncClient
    ):
        cart_id = create_cart.json()["data"]["id"]
        res: httpx.Response = await async_client.get("/carts")

        json_res = res.json()

        assert res.status_code == 200
        assert len(json_res["data"]) == 1
        assert json_res["data"][0]["id"] == cart_id

    @pytest.mark.asyncio
    async def test_get_carts_with_items(
        self,
        create_cart: httpx.Response,
        async_client: httpx.AsyncClient,
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
    async def test_increment_item(
        self, create_cart: httpx.Response, async_client: httpx.AsyncClient
    ):
        cart_id = create_cart.json()["data"]["id"]
        prd_id: str = "019fb2f7-2003-74d1-91fb-79bcb506c77f"

        res: httpx.Response = await async_client.patch(
            f"/carts/{cart_id}/products/{prd_id}/increment", params={"quantity": 2}
        )

        json_res = res.json()

        assert res.status_code == 200
        assert json_res["data"]["quantity"] == 4

    @pytest.mark.asyncio
    async def test_decrement_item(
        self, create_cart: httpx.Response, async_client: httpx.AsyncClient
    ):
        cart_id = create_cart.json()["data"]["id"]
        prd_id: str = "019fb2f7-2003-74d1-91fb-79bcb506c77f"

        res: httpx.Response = await async_client.patch(
            f"/carts/{cart_id}/products/{prd_id}/decrement", params={"quantity": 1}
        )

        json_res = res.json()

        assert res.status_code == 200
        assert json_res["data"]["quantity"] == 1

    @pytest.mark.asyncio
    async def test_decrement_delete_item(
        self, create_cart: httpx.Response, async_client: httpx.AsyncClient
    ):
        cart_id = create_cart.json()["data"]["id"]
        prd_id: str = "019fb2f7-2003-74d1-91fb-79bcb506c77f"

        res: httpx.Response = await async_client.patch(
            f"/carts/{cart_id}/products/{prd_id}/decrement", params={"quantity": 2}
        )

        json_res = res.json()

        assert res.status_code == 200
        assert not json_res["data"]


class TestRemoveItem:
    @pytest.mark.asyncio
    async def test_remove_item(
        self, create_cart: httpx.Response, async_client: httpx.AsyncClient
    ):
        cart_id = create_cart.json()["data"]["id"]
        prd_id: str = "019fb2f7-2003-74d1-91fb-79bcb506c77f"

        cart_item: dict = {
            "product_id": "019fbd53-b8da-75fc-904e-b1d70c2e2c6e",
            "quantity": 5,
        }

        await async_client.post(
            "/carts", json=cart_item, params={"cart_id": cart_id}
        )

        res: httpx.Response = await async_client.patch(
            f"/carts/{cart_id}/products/{prd_id}/remove"
        )

        json_res = res.json()

        assert res.status_code == 200
        assert json_res["data"]["items"] == 1
        assert json_res["data"]["id"] == cart_id

    @pytest.mark.asyncio
    async def test_remove_item_delete_cart(
        self, create_cart: httpx.Response, async_client: httpx.AsyncClient
    ):
        cart_id = create_cart.json()["data"]["id"]
        prd_id: str = "019fb2f7-2003-74d1-91fb-79bcb506c77f"

        res: httpx.Response = await async_client.patch(
            f"/carts/{cart_id}/products/{prd_id}/remove"
        )

        json_res = res.json()

        assert res.status_code == 200
        assert not json_res["data"]


class TestDeleteCart:
    @pytest.mark.asyncio
    async def test_delete_cart(
        self, create_cart: httpx.Response, async_client: httpx.AsyncClient
    ):
        cart_id = create_cart.json()["data"]["id"]

        res: httpx.Response = await async_client.delete(f"/carts/{cart_id}")
        assert res.status_code == 204

    @pytest.mark.asyncio
    async def test_cart_not_found(
        self, create_cart: httpx.Response, async_client: httpx.AsyncClient
    ):
        res: httpx.Response = await async_client.delete(f"/carts/{str(uuid7())}")
        assert res.status_code == 404
