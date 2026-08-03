from uuid import UUID


from shared.core.exceptions import AppException


class CartNotFoundError(AppException):
    """Cart not found"""

    def __init__(self, id: UUID):
        self.id = id


class OrderNotFoundError(AppException):
    """Order not found"""

    def __init__(self, id: UUID):
        self.id = id


class CartItemNotFoundError(AppException):
    """Cart item not found"""

    def __init__(self, cart_id: UUID, product_id: UUID):
        self.cart_id = cart_id
        self.product_id = product_id


class CartsNotFoundError(AppException):
    """Carts not found"""

    pass


class OrdersNotFoundError(AppException):
    """Orders not found"""

    pass
