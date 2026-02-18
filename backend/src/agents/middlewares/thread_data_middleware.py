import os
import logging
from pathlib import Path
from typing import NotRequired, override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langgraph.runtime import Runtime

from src.agents.thread_state import ThreadDataState
from src.sandbox.consts import THREAD_DATA_BASE_DIR

logger = logging.getLogger(__name__)

class ThreadDataMiddlewareState(AgentState):
    """Compatible with the `ThreadState` schema."""

    thread_data: NotRequired[ThreadDataState | None]


class ThreadDataMiddleware(AgentMiddleware[ThreadDataMiddlewareState]):
    """Create thread data directories for each thread execution."""

    state_schema = ThreadDataMiddlewareState

    def __init__(self, base_dir: str | None = None, lazy_init: bool = True):
        super().__init__()
        self._base_dir = base_dir or os.getcwd()
        self._lazy_init = lazy_init

    def _get_thread_paths(self, thread_id: str) -> dict[str, str]:
        thread_dir = Path(self._base_dir) / THREAD_DATA_BASE_DIR / thread_id / "user-data"
        return {
            "workspace_path": str(thread_dir / "workspace"),
            "uploads_path": str(thread_dir / "uploads"),
            "outputs_path": str(thread_dir / "outputs"),
        }

    def _create_thread_directories(self, thread_id: str) -> dict[str, str]:
        paths = self._get_thread_paths(thread_id)
        for path in paths.values():
            os.makedirs(path, exist_ok=True)
        return paths

    @override
    def before_agent(self, state: ThreadDataMiddlewareState, runtime: Runtime) -> dict | None:
        # Try multiple ways to get the thread_id
        thread_id = None

        # 1. Try runtime.context
        if hasattr(runtime, "context") and runtime.context:
            thread_id = runtime.context.get("thread_id")

        # 2. Try runtime.config
        if thread_id is None and hasattr(runtime, "config") and runtime.config:
            thread_id = runtime.config.get("configurable", {}).get("thread_id")

        if thread_id is None:
            logger.warning(f"Thread ID not found in context or config. Runtime keys: {dir(runtime)}")
            # Fallback to a default to prevent crash during deployment testing
            thread_id = "default-thread"

        if self._lazy_init:
            paths = self._get_thread_paths(thread_id)
        else:
            paths = self._create_thread_directories(thread_id)

        return {
            "thread_data": {
                **paths,
            }
        }
