from fastapi import FastAPI


from shared.core.shared_config import get_global_settings

GlOBAL_SETTINGS = get_global_settings()


app = FastAPI(
    title=GlOBAL_SETTINGS.API_TITLE,
    description=GlOBAL_SETTINGS.API_DESCRIPTION,
    version=GlOBAL_SETTINGS.API_VERSION,
)
