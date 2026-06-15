"""Packaged backend runner for the desktop app."""
import os

import uvicorn

from main import app


def main() -> None:
    port = int(os.getenv("FOCUS_TASK_BACKEND_PORT", "8765"))
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level=os.getenv("FOCUS_TASK_BACKEND_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
