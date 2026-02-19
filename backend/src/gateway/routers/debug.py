import os
from fastapi import APIRouter
from typing import List

router = APIRouter(prefix="/api/debug", tags=["debug"])

@router.get("/logs")
async def get_logs(lines: int = 100):
    """Read the last N lines of logs."""
    logs = {}
    cwd = os.getcwd()
    logs["cwd"] = cwd

    # Try common log locations
    log_files = ["logs/langgraph.log", "logs/gateway.log", "../logs/langgraph.log", "../logs/gateway.log"]

    for log_file in log_files:
        full_path = os.path.abspath(log_file)
        if os.path.exists(full_path):
            try:
                with open(full_path, "r") as f:
                    content = f.readlines()
                    logs[log_file] = "".join(content[-lines:])
            except Exception as e:
                logs[log_file] = f"Error reading log: {e}"
        else:
            logs[log_file] = f"File not found at {full_path}"

    return logs

@router.get("/env")
async def get_env():
    """Check if critical environment variables are set (masking keys)."""
    return {
        "BLABLADOR_API_KEY_SET": "BLABLADOR_API_KEY" in os.environ,
        "HF_TOKEN_SET": "HF_TOKEN" in os.environ,
        "PORT": os.environ.get("PORT"),
        "DEER_FLOW_CONFIG_PATH": os.environ.get("DEER_FLOW_CONFIG_PATH"),
    }
