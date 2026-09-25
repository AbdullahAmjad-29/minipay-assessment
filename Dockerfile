FROM python:3.12-slim

WORKDIR /app

# Dependencies first — this layer only rebuilds when requirements.txt changes
COPY app/requirements.txt .
RUN pip install --no-cache-dir --default-timeout=120 --retries 10 -r requirements.txt

# Now the actual application code
COPY app/ ./app/

# Run as a non-root user, not the container default (root)
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
