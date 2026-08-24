from uuid import UUID


from shared.core.exceptions import AppException


class ProductExistsError(AppException):
    """Product already exists"""

    def __init__(self, name: str):
        self.name = name


class TaskProductNotFoundError(Exception):
    def __init__(self, id: UUID):
        self.id = id


class TaskOutOfStockError(Exception):
    def __init__(self, id: UUID):
        self.id = id


class TaskNotEnoughStockError(Exception):
    def __init__(self, id: UUID):
        self.id = id


class ProductNotFoundError(AppException):
    """Product not found"""

    def __init__(self, id: UUID):
        self.id = id


class ProductsNotFoundError(AppException):
    """Products not found"""

    pass


class OutOfStockError(AppException):
    "Product ran out of stock"

    def __init__(self, id: UUID):
        self.id = id


class NotEnoughStockError(AppException):
    "Product remaining quantity less than required"

    def __init__(self, id: UUID):
        self.id = id
