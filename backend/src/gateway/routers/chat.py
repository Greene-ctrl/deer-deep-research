import json
import logging
import uuid
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

LANGGRAPH_URL = "http://127.0.0.1:2024"

class ChatRequest(BaseModel):
    message: str = Field(..., description="Message to send to the agent")
    thread_id: Optional[str] = Field(None, description="Thread ID to continue a conversation")
    stream: bool = Field(True, description="Whether to stream the response")
    model_name: Optional[str] = Field(None, description="Model to use")
    thinking_enabled: bool = Field(True, description="Enable thinking mode")
    is_plan_mode: bool = Field(False, description="Enable plan mode")
    subagent_enabled: bool = Field(False, description="Enable subagent delegation")

async def get_assistant_id(client: httpx.AsyncClient) -> str:
    """Find the assistant ID for 'lead_agent'."""
    try:
        resp = await client.post(f"{LANGGRAPH_URL}/assistants/search", json={"limit": 10})
        resp.raise_for_status()
        assistants = resp.json()

        for asst in assistants:
            if asst.get("graph_id") == "lead_agent" or asst.get("name") == "lead_agent":
                return asst["assistant_id"]

        # If no assistants exist, create one from graph_id
        resp = await client.post(f"{LANGGRAPH_URL}/assistants", json={"graph_id": "lead_agent", "name": "lead_agent"})
        resp.raise_for_status()
        asst = resp.json()
        return asst["assistant_id"]
    except Exception as e:
        logger.error(f"Error finding/creating assistant: {e}")
        return str(e)

@router.post("", summary="Chat with DeerFlow Agent")
async def chat(chat_req: ChatRequest):
    thread_id = chat_req.thread_id

    # 1. Thread and Assistant preparation
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if not thread_id:
                resp = await client.post(f"{LANGGRAPH_URL}/threads", json={})
                resp.raise_for_status()
                thread_id = resp.json()["thread_id"]
                logger.info(f"Created thread: {thread_id}")

            assistant_id = await get_assistant_id(client)
    except Exception as e:
        logger.error(f"Preparation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Preparation failed: {e!s}")

    # Validate assistant_id
    try:
        uuid.UUID(assistant_id)
    except:
        raise HTTPException(status_code=500, detail=f"Invalid assistant_id found: {assistant_id}")

    # 2. Prepare Payload
    configurable = {
        "thread_id": thread_id,
        "model_name": chat_req.model_name,
        "thinking_enabled": chat_req.thinking_enabled,
        "is_plan_mode": chat_req.is_plan_mode,
        "subagent_enabled": chat_req.subagent_enabled,
    }
    configurable = {k: v for k, v in configurable.items() if v is not None}

    payload = {
        "assistant_id": assistant_id,
        "input": {"messages": [{"role": "user", "content": chat_req.message}]},
        "config": {"configurable": configurable},
    }

    # 3. Handle Streaming or Waiting
    if chat_req.stream:
        payload["stream_mode"] = ["values"]

        async def event_generator():
            # Create a dedicated client for the stream
            async with httpx.AsyncClient(timeout=600) as stream_client:
                try:
                    async with stream_client.stream(
                        "POST",
                        f"{LANGGRAPH_URL}/threads/{thread_id}/runs/stream",
                        json=payload,
                    ) as response:
                        if response.status_code != 200:
                            err_body = await response.aread()
                            logger.error(f"LangGraph stream error {response.status_code}: {err_body.decode()}")
                            yield f"data: {json.dumps({'error': f'LangGraph error {response.status_code}'})}\n\n"
                            return

                        async for line in response.aiter_lines():
                            if line:
                                yield f"{line}\n"
                except Exception as e:
                    logger.error(f"Streaming error: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    else:
        try:
            async with httpx.AsyncClient(timeout=600) as wait_client:
                resp = await wait_client.post(
                    f"{LANGGRAPH_URL}/threads/{thread_id}/runs/wait",
                    json=payload,
                )
                if resp.status_code != 200:
                    logger.error(f"LangGraph wait error {resp.status_code}: {resp.text}")
                    raise HTTPException(status_code=resp.status_code, detail=f"LangGraph error {resp.status_code}")

                return {**resp.json(), "thread_id": thread_id}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            raise HTTPException(status_code=500, detail=f"Chat failed: {e!s}")

@router.get("/{thread_id}/history", summary="Get Chat History")
async def get_chat_history(thread_id: str):
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(f"{LANGGRAPH_URL}/threads/{thread_id}/history")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {e!s}")

@router.get("/threads", summary="List Chat Threads")
async def list_threads(limit: int = 10, offset: int = 0):
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(f"{LANGGRAPH_URL}/threads/search", json={"limit": limit, "offset": offset})
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list threads: {e!s}")
