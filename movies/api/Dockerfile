FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copiamos la app
COPY app /app/app

ENV KAFKA_BOOTSTRAP=kafka:9092 \
    METRICS_TOPIC=metrics \
    API_HOST=0.0.0.0 \
    API_PORT=8000

EXPOSE 8000

CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
