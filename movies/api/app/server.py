import asyncio
import json
import os
from collections import defaultdict
from typing import Dict, Any, List

import orjson
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from aiokafka import AIOKafkaConsumer


KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9093")
METRICS_TOPIC = os.getenv("METRICS_TOPIC", "metrics")

app = FastAPI(title="Realtime Recs Metrics API")


class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        data = orjson.dumps(message)
        for ws in list(self.active):
            try:
                await ws.send_bytes(data)
            except Exception:
                self.disconnect(ws)


manager = ConnectionManager()


# Estado en memoria con la última métrica por tipo
last_metrics: Dict[str, Dict[str, Any]] = {}


@app.get("/")
async def index():
    # Servimos el HTML del dashboard
    with open(os.path.join(os.path.dirname(__file__), "static", "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/metrics/last")
async def get_last_metrics():
    return last_metrics


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # No esperamos mensajes del cliente, solo mantenemos la conexión
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def consume_metrics():
    consumer = AIOKafkaConsumer(
        METRICS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        key_deserializer=lambda v: v.decode("utf-8") if v else None,
        enable_auto_commit=True,
        auto_offset_reset="latest",
    )
    await consumer.start()
    try:
        async for msg in consumer:
            metric_name = msg.key or "unknown"
            payload = msg.value
            # Normalizamos estructura para el frontend: {metric, ...payload}
            event = {"metric": metric_name, **payload}
            last_metrics[metric_name] = event
            await manager.broadcast(event)
    finally:
        await consumer.stop()


@app.on_event("startup")
async def startup_event():
    # Montamos estáticos
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    # Lanzamos consumidor en background
    asyncio.create_task(consume_metrics())
