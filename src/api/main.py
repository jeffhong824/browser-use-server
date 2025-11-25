"""FastAPI main application with WebSocket support for real-time browser automation."""
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pydantic import BaseModel

from src.ai.browser_agent import BrowserAgentService

# Load environment variables from .env file
load_dotenv()


# Global session storage (in production, use Redis or database)
active_sessions: Dict[str, BrowserAgentService] = {}


class TaskRequest(BaseModel):
    """Request model for browser automation task."""

    task: str
    model: str = "gpt-4o"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    logger.info("🚀 Browser Use SaaS Service starting...")
    logger.info(f"📁 Working directory: {os.getcwd()}")

    # Load environment variables
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.warning("⚠️  OPENAI_API_KEY not set in environment")

    yield

    # Shutdown
    logger.info("🛑 Browser Use SaaS Service shutting down...")
    # Cleanup active sessions if needed
    active_sessions.clear()


app = FastAPI(
    title="Browser Use SaaS",
    description="AI-powered browser automation service with real-time updates",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount static files (if directory exists)
try:
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
except Exception:
    pass  # Static directory not required


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web interface."""
    html_file = os.path.join(
        os.path.dirname(__file__), "..", "templates", "index.html"
    )
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Browser Use SaaS</h1><p>Frontend not found</p>")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "browser-use-saas",
        "version": "0.1.0",
    }


@app.get("/api/v1/screenshots/{session_id}/{filename:path}")
async def get_screenshot(session_id: str, filename: str):
    """
    Get screenshot file for a session.
    
    Args:
        session_id: Session identifier
        filename: Screenshot filename
    """
    screenshots_dir = Path(os.getenv("SCREENSHOTS_DIR", "/app/screenshots"))
    screenshot_path = screenshots_dir / filename
    
    logger.info(f"📸 Screenshot request: session_id={session_id}, filename={filename}")
    logger.info(f"📸 Screenshot path: {screenshot_path}, exists={screenshot_path.exists()}")
    
    if not screenshot_path.exists():
        logger.error(f"📸 Screenshot not found: {screenshot_path}")
        raise HTTPException(status_code=404, detail=f"Screenshot not found: {filename}")
    
    # Security check: ensure the resolved path is within screenshots_dir
    try:
        resolved_screenshot_path = screenshot_path.resolve()
        resolved_screenshots_dir = screenshots_dir.resolve()
        if not str(resolved_screenshot_path).startswith(str(resolved_screenshots_dir)):
            logger.error(f"📸 Security check failed: {resolved_screenshot_path} not in {resolved_screenshots_dir}")
            raise HTTPException(status_code=403, detail="Invalid screenshot path")
    except Exception as e:
        logger.error(f"📸 Path resolution error: {e}")
        raise HTTPException(status_code=403, detail="Invalid screenshot path")
    
    logger.info(f"📸 Serving screenshot: {screenshot_path}")
    return FileResponse(
        path=str(screenshot_path),
        media_type="image/png",
        filename=filename,
        headers={
            "Content-Type": "image/png",
        },
    )


@app.get("/api/v1/videos/{session_id}/{filename:path}")
async def get_video(session_id: str, filename: str):
    """
    Get video file for a session.
    
    Args:
        session_id: Session identifier
        filename: Video filename
    """
    video_dir = Path(os.getenv("VIDEO_DIR", "./recordings"))
    video_path = video_dir / filename
    
    logger.info(f"📹 Video request: session_id={session_id}, filename={filename}")
    logger.info(f"📹 Video path: {video_path}, exists={video_path.exists()}")
    
    if not video_path.exists():
        # Try to find the video file by matching pattern
        video_files = list(video_dir.glob("*.mp4"))
        if video_files:
            # Get the most recently modified video file
            video_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            video_path = video_files[0]
            logger.info(f"📹 Using most recent video: {video_path}")
        else:
            logger.error(f"📹 No video files found in {video_dir}")
            raise HTTPException(status_code=404, detail=f"Video not found: {filename}")
    
    # Security check: ensure the resolved path is within video_dir
    try:
        resolved_video_path = video_path.resolve()
        resolved_video_dir = video_dir.resolve()
        if not str(resolved_video_path).startswith(str(resolved_video_dir)):
            logger.error(f"📹 Security check failed: {resolved_video_path} not in {resolved_video_dir}")
            raise HTTPException(status_code=403, detail="Invalid video path")
    except Exception as e:
        logger.error(f"📹 Path resolution error: {e}")
        raise HTTPException(status_code=403, detail="Invalid video path")
    
    logger.info(f"📹 Serving video: {video_path}")
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=filename,
        headers={
            "Accept-Ranges": "bytes",
            "Content-Type": "video/mp4",
        },
    )


@app.post("/v1/tasks")
async def create_task(request: TaskRequest):
    """
    Create a new browser automation task.

    Returns session_id for WebSocket connection.
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise HTTPException(
            status_code=500, detail="OPENAI_API_KEY not configured"
        )

    session_id = str(uuid.uuid4())

    # Get configuration from environment
    headless_env = os.getenv("BROWSER_HEADLESS", "true").lower()
    headless = headless_env == "true"
    demo_mode = os.getenv("BROWSER_DEMO_MODE", "false").lower() == "true"
    
    # In Docker/headless mode, demo_mode doesn't work and causes startup issues
    # Disable demo_mode if headless is True to avoid conflicts
    if headless and demo_mode:
        logger.warning("⚠️  demo_mode is disabled because headless=True (demo_mode requires visible browser)")
        demo_mode = False
    
    # Enable video recording (default: True for playback)
    record_video = os.getenv("RECORD_VIDEO", "true").lower() == "true"
    # Use absolute path for video directory in container
    video_dir = os.getenv("VIDEO_DIR", "/app/recordings")
    
    # Enable screenshot capture (default: True)
    capture_screenshots = os.getenv("CAPTURE_SCREENSHOTS", "true").lower() == "true"
    screenshots_dir = os.getenv("SCREENSHOTS_DIR", "/app/screenshots")
    
    # Log configuration for debugging
    logger.info(f"🔧 Browser config: headless={headless}, demo_mode={demo_mode}, record_video={record_video}, video_dir={video_dir}, capture_screenshots={capture_screenshots}, screenshots_dir={screenshots_dir}")

    window_width = int(os.getenv("BROWSER_WINDOW_WIDTH", "1280"))
    window_height = int(os.getenv("BROWSER_WINDOW_HEIGHT", "720"))
    window_size = {"width": window_width, "height": window_height}

    # Create agent service
    agent_service = BrowserAgentService(
        openai_api_key=openai_api_key,
        model=request.model or os.getenv("LLM_MODEL", "gpt-4o"),
        headless=headless,
        demo_mode=demo_mode,
        window_size=window_size,
        record_video=record_video,
        video_dir=video_dir,
        capture_screenshots=capture_screenshots,
        screenshots_dir=screenshots_dir,
    )

    active_sessions[session_id] = agent_service

    return {
        "status": "ok",
        "session_id": session_id,
        "message": "Task created. Connect via WebSocket to start execution.",
    }


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time task execution updates.

    Client should send: {"action": "start", "task": "..."}
    Server will send: {"type": "status|complete|error", "message": "...", "data": {...}}
    """
    await websocket.accept()
    logger.info(f"📡 WebSocket connection established: {session_id}")

    try:
        # Get agent service for this session
        agent_service = active_sessions.get(session_id)
        if not agent_service:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "Session not found. Please create a task first.",
                    "data": {"session_id": session_id},
                }
            )
            await websocket.close()
            return

        # Wait for start message
        message = await websocket.receive_json()
        if message.get("action") != "start":
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "Invalid action. Expected 'start'.",
                    "data": {},
                }
            )
            await websocket.close()
            return

        task = message.get("task", "")
        if not task:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "Task is required.",
                    "data": {},
                }
            )
            await websocket.close()
            return

        # Run task and stream updates (includes step callbacks)
        async for update in agent_service.run_task(task, session_id):
            await websocket.send_json(update)

            # Close connection on completion or error
            if update["type"] in ["complete", "error"]:
                break

    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": f"Internal error: {str(e)}",
                    "data": {"session_id": session_id},
                }
            )
        except Exception:
            pass
    finally:
        # Cleanup
        if session_id in active_sessions:
            del active_sessions[session_id]
        logger.info(f"🧹 Session cleaned up: {session_id}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("API_PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)

