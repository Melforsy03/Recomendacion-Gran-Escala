FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copiamos la app, services y routes
COPY app /app/app
COPY services /app/services
COPY routes /app/routes

ENV KAFKA_BOOTSTRAP=kafka:9092 \
    METRICS_TOPIC=metrics \
    API_HOST=0.0.0.0 \
    API_PORT=8000

EXPOSE 8000

CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
