from apps.product_service.app.api.schemas.product import ProductItem
from apps.order_service.app.api.schemas.cart_item import CartItemResponse
from apps.order_service.app.api.schemas.order_item import OrderItemResponse


def get_items_response(obj: str, obj_items: list[tuple]):
    items = []
    for obj_item in obj_items:
        product = ProductItem(
            id=obj_item[0],
            name=obj_item[1],
            description=obj_item[2],
            serial=obj_item[3],
        )

        if obj == "cart":
            item = CartItemResponse(
                product=product,
                quantity=obj_item[4],
                price=obj_item[5],
                total_price=obj_item[6],
                created_at=obj_item[7],
            )
        elif obj == "order":
            item = OrderItemResponse(
                product=product,
                quantity=obj_item[4],
                price=obj_item[5],
                total_price=obj_item[6],
                created_at=obj_item[7],
            )

        items.append(item)
    return items
