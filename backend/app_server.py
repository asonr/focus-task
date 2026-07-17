"""Packaged backend runner for the desktop app."""
import os

import uvicorn

from main import app


def main() -> None:
    port = int(os.getenv("FOCUS_TASK_BACKEND_PORT", "8765"))
    uvicorn.run(
        app,
        host=os.getenv("FOCUS_TASK_BACKEND_HOST", "0.0.0.0"),
        port=port,
        log_level=os.getenv("FOCUS_TASK_BACKEND_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
