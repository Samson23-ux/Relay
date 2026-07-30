from apps.order_service.app.api.repo.cart import CartRepository


class CartService:
    def __init__(self, cart_repo: CartRepository):
        self._cart_repo = cart_repo
