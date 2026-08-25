from fastapi import APIRouter


from apps.order_service.app.api.routers import cart, order

router = APIRouter()
router.include_router(cart.router, tags=["Cart"])
router.include_router(order.router, tags=["Order"])
