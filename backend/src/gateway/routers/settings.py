from typing import Any

import yaml
from fastapi import APIRouter, HTTPException

from src.config.app_config import AppConfig, reload_app_config

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", summary="Get Application Settings")
async def get_settings():
    """Retrieve the current config.yaml content."""
    try:
        config_path = AppConfig.resolve_config_path()
        with open(config_path) as f:
            return yaml.safe_load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read settings: {e!s}")


@router.put("", summary="Update Application Settings")
async def update_settings(settings: dict[str, Any]):
    """Update the config.yaml content and reload the application configuration."""
    try:
        config_path = AppConfig.resolve_config_path()
        with open(config_path, "w") as f:
            yaml.safe_dump(settings, f, sort_keys=False)
        reload_app_config()
        return {"status": "success", "message": "Settings updated and reloaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {e!s}")
