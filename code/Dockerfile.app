FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-app.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements-app.txt

# Instalar pyarrow con soporte HDFS
RUN pip install pyarrow==14.0.1

COPY . .