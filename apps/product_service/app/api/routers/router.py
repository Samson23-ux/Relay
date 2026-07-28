from fastapi import APIRouter


from shared.core.shared_config import get_global_settings

GlOBAL_SETTINGS = get_global_settings()


router = APIRouter(prefix=GlOBAL_SETTINGS.API_PREFIX)
