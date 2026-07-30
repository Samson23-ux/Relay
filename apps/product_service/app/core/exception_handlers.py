from fastapi import FastAPI


from shared.schemas.response import ErrorResponse
from shared.core.exceptions import create_exception_handler
from apps.product_service.app.core.exceptions import (
    OutOfStockError,
    ProductExistsError,
    NotEnoughStockError,
    ProductNotFoundError,
    ProductsNotFoundError,
)


class ProductExceptionHandler:
    def __init__(self, app: FastAPI):
        self._app = app

    def add_handlers(self):
        self._app.add_exception_handler(
            exc_class_or_status_code=ProductExistsError,
            handler=create_exception_handler(
                status_code=409,
                initial_detail=ErrorResponse(
                    message="Product with name {name} already exists"
                ),
            ),
        )

        self._app.add_exception_handler(
            exc_class_or_status_code=ProductNotFoundError,
            handler=create_exception_handler(
                status_code=404,
                initial_detail=ErrorResponse(message="Product not found with id {id}"),
            ),
        )

        self._app.add_exception_handler(
            exc_class_or_status_code=ProductsNotFoundError,
            handler=create_exception_handler(
                status_code=404,
                initial_detail=ErrorResponse(message="Products not found!"),
            ),
        )

        self._app.add_exception_handler(
            exc_class_or_status_code=OutOfStockError,
            handler=create_exception_handler(
                status_code=400,
                initial_detail=ErrorResponse(
                    message="Product with id {id} out of stock"
                ),
            ),
        )

        self._app.add_exception_handler(
            exc_class_or_status_code=NotEnoughStockError,
            handler=create_exception_handler(
                status_code=400,
                initial_detail=ErrorResponse(
                    message="Product with id {id} quantity not enough"
                ),
            ),
        )
