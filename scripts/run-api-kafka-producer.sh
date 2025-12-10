#!/bin/bash
###############################################################################
# Ejecuta el productor -> Kafka (ratings).
# Fuente:
#   - Si pasas <API_URL> o RATINGS_API_URL: llama una API externa.
#   - Si no, usa el dataset local `Dataset/rating.csv` (sin dependencias externas).
# Uso:
#   ./scripts/run-api-kafka-producer.sh <API_URL>
#   RATINGS_API_URL="http://..." ./scripts/run-api-kafka-producer.sh
#   ./scripts/run-api-kafka-producer.sh      # modo dataset local
#
# Requiere: docker compose (kafka corriendo) y dependencias Python instaladas
#           con `pip install -r requirements.txt`.
###############################################################################

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PRODUCER_SCRIPT="$PROJECT_ROOT/movies/src/streaming/api_to_kafka_producer.py"

# Preferir argumento; si no, variable de entorno
API_URL="${1:-${RATINGS_API_URL:-}}"
DATASET_PATH="${RATINGS_LOCAL_PATH:-Dataset/rating.csv}"
BOOTSTRAP="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9093}"
TOPIC="${KAFKA_TOPIC:-ratings}"

if [[ ! -f "$PRODUCER_SCRIPT" ]]; then
    echo -e "${RED}❌ No se encontró el script del productor en $PRODUCER_SCRIPT${NC}"
    exit 1
fi

echo "===============================================================================" 
echo -e "${BLUE}🚀 Productor -> Kafka (ratings)${NC}"
echo "===============================================================================" 
if [[ -n "$API_URL" ]]; then
    echo -e "🌐 API:     ${YELLOW}${API_URL}${NC}"
else
    echo -e "📂 Dataset: ${YELLOW}${DATASET_PATH}${NC} (RATINGS_LOCAL_PATH)${NC}"
fi
echo -e "📡 Kafka:   ${YELLOW}${BOOTSTRAP}${NC}"
echo -e "🎯 Topic:   ${YELLOW}${TOPIC}${NC}"
echo "===============================================================================" 

# Verificar que Kafka esté corriendo
if ! docker ps | grep -q kafka; then
    echo -e "${RED}❌ Kafka no está corriendo${NC}"
    echo -e "${YELLOW}💡 Ejecuta primero: ./scripts/start-system.sh${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Kafka disponible${NC}"

# Asegurar que el topic exista (crea si falta)
if ! docker exec kafka kafka-topics --list --bootstrap-server localhost:9092 2>/dev/null | grep -q "^${TOPIC}$"; then
    echo -e "${YELLOW}ℹ Creando topic '${TOPIC}'...${NC}"
    docker exec kafka kafka-topics --create \
        --topic "${TOPIC}" \
        --bootstrap-server localhost:9092 \
        --partitions 6 \
        --replication-factor 1 \
        --if-not-exists 2>/dev/null || true
fi
echo -e "${GREEN}✅ Topic '${TOPIC}' listo${NC}"

# Verificar dependencias locales de Python
echo -e "${YELLOW}🔍 Verificando dependencias Python (requests, kafka-python, pandas)...${NC}"
if ! python3 - <<'PY' 2>/dev/null; then
import requests  # type: ignore
import kafka  # type: ignore
import pandas  # type: ignore
print("ok")
PY
    echo -e "${RED}❌ Faltan dependencias (requests, kafka-python, pandas).${NC}"
    echo -e "${YELLOW}📦 Instala con:${NC} pip install -r requirements.txt"
    exit 1
fi
echo -e "${GREEN}✅ Dependencias disponibles${NC}"

# Limpieza al salir
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Deteniendo productor API -> Kafka...${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

echo ""
echo -e "${GREEN}▶️  Iniciando productor (Ctrl+C para detener)...${NC}"
echo ""

RATINGS_API_URL="$API_URL" \
RATINGS_LOCAL_PATH="$DATASET_PATH" \
KAFKA_BOOTSTRAP_SERVERS="$BOOTSTRAP" \
KAFKA_TOPIC="$TOPIC" \
python3 "$PRODUCER_SCRIPT"

EXIT_CODE=$?
echo ""
if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}✅ Productor finalizado correctamente${NC}"
else
    echo -e "${RED}❌ Productor finalizado con errores (código: $EXIT_CODE)${NC}"
fi

exit $EXIT_CODE
