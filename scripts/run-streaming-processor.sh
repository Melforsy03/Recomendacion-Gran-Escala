#!/bin/bash
# Script para ejecutar el procesador de ratings streaming
# Fase 8: Sistema de Recomendación de Películas a Gran Escala

set -e

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

function print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

function print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

function print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info "Procesador de Ratings Streaming - Fase 8"
echo ""

# 1. Verificar que Kafka esté corriendo
print_info "Verificando servicios..."
if ! docker ps | grep -q kafka; then
    print_error "Kafka no está corriendo"
    echo "   Ejecuta: docker compose up -d kafka"
    exit 1
fi
print_success "Kafka está corriendo"

if ! docker ps | grep -q spark-master; then
    print_error "Spark no está corriendo"
    echo "   Ejecuta: docker compose up -d spark-master spark-worker"
    exit 1
fi
print_success "Spark está corriendo"

# 2. Verificar topics
print_info "Verificando topics de Kafka..."

if ! docker exec kafka kafka-topics --list --bootstrap-server localhost:9092 2>/dev/null | grep -q "^ratings$"; then
    print_error "Topic 'ratings' no existe"
    echo "   Ejecuta: ./scripts/recsys-utils.sh kafka-create ratings 6 1"
    exit 1
fi
print_success "Topic 'ratings' existe"

if ! docker exec kafka kafka-topics --list --bootstrap-server localhost:9092 2>/dev/null | grep -q "^metrics$"; then
    print_info "Creando topic 'metrics'..."
    docker exec kafka kafka-topics --create \
        --topic metrics \
        --bootstrap-server localhost:9092 \
        --partitions 3 \
        --replication-factor 1 \
        --if-not-exists 2>/dev/null
    print_success "Topic 'metrics' creado"
else
    print_success "Topic 'metrics' existe"
fi

# 3. Verificar metadata en HDFS
print_info "Verificando metadata en HDFS..."
if ! docker exec namenode hadoop fs -test -d /data/content_features/movies_features 2>/dev/null; then
    print_error "Movies features no encontrados en HDFS"
    echo "   Ejecuta primero la Fase 4 (feature engineering)"
    exit 1
fi
print_success "Metadata disponible en HDFS"

# 4. Crear directorios en HDFS
print_info "Creando directorios de salida en HDFS..."
docker exec namenode hadoop fs -mkdir -p /streams/ratings/raw 2>/dev/null || true
docker exec namenode hadoop fs -mkdir -p /streams/ratings/agg/tumbling 2>/dev/null || true
docker exec namenode hadoop fs -mkdir -p /streams/ratings/agg/sliding 2>/dev/null || true
docker exec namenode hadoop fs -mkdir -p /checkpoints/ratings_stream/processor 2>/dev/null || true
print_success "Directorios creados"

# 5. Copiar script a shared
print_info "Copiando script a directorio compartido..."
mkdir -p "$ROOT_DIR/shared/streaming"
cp "$ROOT_DIR/movies/src/streaming/ratings_stream_processor.py" "$ROOT_DIR/shared/streaming/"
print_success "Script copiado"

# 6. Verificar que haya datos en topic ratings
print_info "Verificando datos en topic 'ratings'..."
OFFSET_COUNT=$(docker exec kafka kafka-run-class kafka.tools.GetOffsetShell \
    --broker-list localhost:9092 \
    --topic ratings 2>/dev/null | awk -F: '{sum += $NF} END {print sum}')

if [ "$OFFSET_COUNT" -eq 0 ]; then
    print_error "Topic 'ratings' está vacío"
    echo "   Ejecuta primero el generador: ./scripts/run-synthetic-ratings.sh"
    exit 1
fi
print_success "Topic 'ratings' tiene $OFFSET_COUNT mensajes"

# 7. Ejecutar procesador
echo ""
echo "========================================================================"
echo "EJECUTANDO PROCESADOR DE RATINGS STREAMING"
echo "========================================================================"
echo "Input topic:   ratings"
echo "Output topic:  metrics"
echo "Watermark:     10 minutos"
echo "Windows:       Tumbling 1min + Sliding 5min/1min"
echo "Presiona Ctrl+C para detener"
echo "========================================================================"
echo ""

docker exec spark-master spark-submit \
    --master spark://spark-master:7077 \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1 \
    --conf spark.sql.shuffle.partitions=8 \
    --conf spark.streaming.backpressure.enabled=true \
    --conf spark.streaming.kafka.maxRatePerPartition=100 \
    --conf spark.driver.memory=512m \
    --conf spark.executor.memory=1g \
    --conf spark.executor.cores=2 \
    --conf spark.cores.max=2 \
    --conf spark.scheduler.mode=FAIR \
    --conf spark.scheduler.allocation.file=file:///opt/spark/conf/fairscheduler.xml \
    --conf spark.scheduler.pool=streaming \
    --conf spark.sql.streaming.checkpointLocation=hdfs://namenode:9000/checkpoints/ratings_stream/processor \
    /opt/spark/work-dir/streaming/ratings_stream_processor.py
