from fastapi import APIRouter


from shared.shared_deps import RequestMetaData
from shared.schemas.response import SuccessResponse
from apps.user_service.app.deps import AdminServiceDep

router = APIRouter()


@router.patch(
    "/admin/config/reload",
    status_code=200,
    description="Reload config file (Admin only)",
)
async def reload_config(
    request_meta: RequestMetaData,
    admin_service: AdminServiceDep,
):
    await admin_service.load_config(request_meta)
    return SuccessResponse(message="Config reloaded successfully")
