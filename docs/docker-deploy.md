# Docker Deployment

Focus Task supports two Docker deployment modes:

- API only: run the FastAPI backend for the Tauri desktop app.
- Web + API: run the browser UI behind Nginx and the FastAPI backend together.

## Quick start

```bash
cp .env.docker.example .env
```

Edit `.env` and set a long random `FOCUS_TASK_SECRET_KEY`.
For the default local compose file, an empty database bootstraps:

```text
FOCUS_TASK_BOOTSTRAP_ADMIN_USERNAME=admin
FOCUS_TASK_BOOTSTRAP_ADMIN_PASSWORD=admin123
```

Change the password after first login from `Settings -> User Management`.

```bash
docker compose up -d --build
```

Open the web UI:

```text
http://localhost:8080
```

The API is available at:

```text
http://localhost:8765
```

## API only

Use this when the Tauri desktop app should connect to a Docker-hosted backend.

```bash
docker compose up -d --build focus-task-api
```

Then point the desktop/web build to:

```text
http://SERVER_IP:8765
```

For a Tauri desktop build, set `VITE_API_BASE` before building the app if you want it to use a remote backend instead of the bundled local backend.

## Data persistence

The SQLite database is stored in the Docker volume:

```text
focus-task-data:/data/todo.db
```

Back it up with:

```bash
docker compose exec focus-task-api python - <<'PY'
import shutil
shutil.copyfile('/data/todo.db', '/data/todo.backup.db')
print('/data/todo.backup.db')
PY
```

## Configuration

Common environment variables:

```text
FOCUS_TASK_SECRET_KEY
FOCUS_TASK_TOKEN_EXPIRE_MINUTES
FOCUS_TASK_PASSWORD_MIN_LENGTH
FOCUS_TASK_BOOTSTRAP_ADMIN_USERNAME
FOCUS_TASK_BOOTSTRAP_ADMIN_PASSWORD
FOCUS_TASK_API_PORT
FOCUS_TASK_WEB_PORT
FOCUS_TASK_CORS_ORIGINS
```

`FOCUS_TASK_CORS_ORIGINS` is only needed when browsers call the API directly from another origin. The bundled web container proxies `/api` through Nginx, so it normally does not need extra CORS configuration.

## Health checks

The backend exposes:

```text
GET /api/health
```

Check it with:

```bash
curl http://localhost:8765/api/health
```

Expected response:

```json
{"status":"ok"}
```

## Stop services

```bash
docker compose down
```

Keep data by leaving the volume in place. To delete all Docker data:

```bash
docker compose down -v
```

## GitHub Actions images

The repository includes a GitHub Actions workflow:

```text
.github/workflows/docker.yml
```

It builds and publishes two images to GitHub Container Registry:

```text
ghcr.io/OWNER/REPO/focus-task-api:latest
ghcr.io/OWNER/REPO/focus-task-web:latest
```

The workflow runs on:

- push to `main`
- version tags like `v1.0.0`
- pull requests to `main` for build verification
- manual `workflow_dispatch`

Pull requests build images but do not push them.

### Production compose

Use `docker-compose.prod.yml` on a server when you want to pull prebuilt images instead of building from source.

```bash
cp .env.prod.example .env
```

Edit `.env`:

```text
FOCUS_TASK_SECRET_KEY=your-long-random-secret
FOCUS_TASK_BOOTSTRAP_ADMIN_USERNAME=admin
FOCUS_TASK_BOOTSTRAP_ADMIN_PASSWORD=your-strong-initial-admin-password
FOCUS_TASK_API_IMAGE=ghcr.io/OWNER/REPO/focus-task-api:latest
FOCUS_TASK_WEB_IMAGE=ghcr.io/OWNER/REPO/focus-task-web:latest
```

The bootstrap admin is created only when the `users` table is empty. Existing databases are never overwritten.

Then start:

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

To update after a new image is published:

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### GHCR package visibility

GitHub Container Registry packages may be private by default depending on repository settings. If the server cannot pull images, either:

- make the packages public in GitHub package settings, or
- run `docker login ghcr.io` on the server with a GitHub token that has package read permission.
