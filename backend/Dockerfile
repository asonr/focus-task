FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FOCUS_TASK_BACKEND_PORT=8765 \
    FOCUS_TASK_DATABASE_URL=sqlite:////data/todo.db

WORKDIR /app

RUN addgroup --system focus-task \
    && adduser --system --ingroup focus-task focus-task \
    && mkdir -p /data \
    && chown -R focus-task:focus-task /data /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER focus-task

EXPOSE 8765

CMD ["python", "app_server.py"]
