from fastapi import APIRouter


from apps.product_service.app.api.routers import product

router = APIRouter()
router.include_router(product.router, tags=["Product"])
