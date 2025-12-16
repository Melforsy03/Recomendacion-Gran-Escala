"""
Ratings Ingest Routes
======================

Endpoint para ingest de ratings vía HTTP. Acepta:
- POST /ratings/  -> body: lista de objetos o objeto único

Publica los registros en Kafka usando el service `ratings_producer`.
"""
from typing import List, Dict, Any
import logging
from fastapi import APIRouter, HTTPException, Request

from services.ratings_producer import enqueue_ratings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.post("/", status_code=202)
async def ingest_ratings(request: Request):
    """Ingesta un payload JSON (lista o dict) y lo publica en Kafka."""
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Payload inválido: {e}")
        raise HTTPException(status_code=400, detail="JSON inválido")

    # Normalizar a lista
    if isinstance(payload, dict):
        # Intentar reconocer envolturas comunes
        for key in ("data", "items", "results"):
            if key in payload and isinstance(payload[key], list):
                payload = payload[key]
                break
        else:
            payload = [payload]

    if not isinstance(payload, list):
        raise HTTPException(status_code=400, detail="Se requiere una lista o un objeto JSON")

    # Validar forma mínima
    normalized = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        if not all(k in item for k in ("userId", "movieId", "rating")):
            continue
        # timestamp opcional
        if "timestamp" not in item:
            import time
            item["timestamp"] = int(time.time() * 1000)
        normalized.append(item)

    if not normalized:
        raise HTTPException(status_code=400, detail="No hay registros válidos para publicar")

    try:
        # Encolar para publicación asíncrona (respuesta rápida 202)
        enq = await enqueue_ratings(normalized)
        if enq < len(normalized):
            # Cola llena: informar parcialmente aceptados
            logger.warning("Cola llena: aceptados=%s, rechazados=%s", enq, len(normalized) - enq)
            return {"status": "partial", "accepted": enq, "rejected": len(normalized) - enq}
    except Exception as e:
        logger.error(f"Error encolando para Kafka: {e}")
        # Si el publicador aún no está listo devolvemos 503 apropiado
        raise HTTPException(status_code=503, detail="Ratings backend no disponible")

    return {"status": "accepted", "count": len(normalized)}
