"""Focus Task backend — FastAPI entry point."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routers import auth, tasks, users

app = FastAPI(title="Focus Task API", version="1.0.0")

CORS_ORIGINS = [
    "tauri://localhost",
    "http://tauri.localhost",
    "https://tauri.localhost",
]

# Allow any origin on port 1420 (dev server) — covers localhost and LAN IPs
CORS_ORIGIN_REGEX = r"http://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2[0-9]|3[01])\.\d+\.\d+|192\.168\.\d+\.\d+):1420"

extra_origins = os.getenv("FOCUS_TASK_CORS_ORIGINS", "")
if extra_origins.strip():
    CORS_ORIGINS.extend(origin.strip() for origin in extra_origins.split(",") if origin.strip())

# CORS — allow Tauri, localhost, and LAN access
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(users.router)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}
