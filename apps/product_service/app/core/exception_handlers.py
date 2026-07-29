from fastapi import FastAPI


from shared.core.exceptions import create_exception_handler
from apps.product_service.app.core.exceptions import ProductExistsError, ProductNotFoundError, ProductsNotFoundError


class ProductExceptionHandler:
    def __init__(self, app: FastAPI):
        self._app = app

    def add_handlers(self):
        self._app.add_exception_handler(
            exc_class_or_status_code=ProductExistsError,
            handler=create_exception_handler(
                status_code=409,
                initial_detail={
                    "status": "error",
                    "message": "Product with name {name} already exists",
                },
            ),
        )

        self._app.add_exception_handler(
            exc_class_or_status_code=ProductNotFoundError,
            handler=create_exception_handler(
                status_code=404,
                initial_detail={
                    "status": "error",
                    "message": "Product not found with id {id}",
                },
            ),
        )

        self._app.add_exception_handler(
            exc_class_or_status_code=ProductsNotFoundError,
            handler=create_exception_handler(
                status_code=404,
                initial_detail={
                    "status": "error",
                    "message": "Products not found!",
                },
            ),
        )
