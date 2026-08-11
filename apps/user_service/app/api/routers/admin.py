from pathlib import Path
from fastapi import APIRouter, Request


from gateway.app.schemas.config import Config
from gateway.app.core.load_config import load_config

router = APIRouter()


@router.patch(
    "/admin/config/reload",
    status_code=200,
    description="Reload config file (Admin only)",
)
async def reload_config(request: Request):
    path = Path(__file__).parent / "core" / "config.yml"

    raw_config = load_config(path)
    request.app.state.config = Config.model_validate(raw_config)
