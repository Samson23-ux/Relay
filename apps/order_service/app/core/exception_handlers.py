from fastapi import FastAPI


from shared.schemas.response import ErrorResponse
from shared.core.exceptions import create_exception_handler
from apps.order_service.app.core.exceptions import (
    CartNotFoundError,
    CartsNotFoundError,
    CartItemNotFoundError,
)


class OrderExceptionHandler:
    def __init__(self, app: FastAPI):
        self._app = app

    def add_handlers(self):
        self._app.add_exception_handler(
            exc_class_or_status_code=CartNotFoundError,
            handler=create_exception_handler(
                status_code=404,
                initial_detail=ErrorResponse(message="Cart not found with id {id}"),
            ),
        )

        self._app.add_exception_handler(
            exc_class_or_status_code=CartItemNotFoundError,
            handler=create_exception_handler(
                status_code=404,
                initial_detail=ErrorResponse(
                    message="Cart item not found with cart id {cart_id} and product id {product_id}"
                ),
            ),
        )

        self._app.add_exception_handler(
            exc_class_or_status_code=CartsNotFoundError,
            handler=create_exception_handler(
                status_code=404,
                initial_detail=ErrorResponse(message="Carts not found!"),
            ),
        )
