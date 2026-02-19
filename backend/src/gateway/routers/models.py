from fastapi import APIRouter
from src.config import get_app_config

router = APIRouter(prefix="/api/models", tags=["models"])

@router.get("", summary="List Available Models")
async def list_models():
    """Returns a list of all configured models."""
    config = get_app_config()
    return {
        "models": [
            {
                "name": m.name,
                "display_name": m.display_name,
                "supports_vision": m.supports_vision
            }
            for m in config.models
        ]
    }
