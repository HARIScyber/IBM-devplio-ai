FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY demo ./demo
ENV PYTHONPATH=/app/backend STORAGE_DIR=/app/backend/storage DATABASE_PATH=/app/backend/devpilot.db
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
