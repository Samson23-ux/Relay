from uuid import UUID


from shared.core.exceptions import AppException


class ProductExistsError(AppException):
    """Product already exists"""

    def __init__(self, name: str):
        self.name = name


class ProductNotFoundError(AppException):
    """Product not found"""

    def __init__(self, id: UUID):
        self.id = id


class ProductsNotFoundError(AppException):
    """Products not found"""

    pass
