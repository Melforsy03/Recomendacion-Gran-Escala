#!/bin/bash
# Script para ejecutar el generador de ratings sintéticos
# Fase 7: Sistema de Recomendación de Películas a Gran Escala

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

# Throughput por defecto
ROWS_PER_SECOND="${1:-50}"

print_info "Generador de Ratings Sintéticos - Fase 7"
echo ""

# 1. Verificar que Kafka esté corriendo
print_info "Verificando servicios..."
if ! docker ps | grep -q kafka; then
    print_error "Kafka no está corriendo"
    echo "   Ejecuta: docker compose up -d kafka"
    exit 1
fi
print_success "Kafka está corriendo"

# 2. Verificar topic 'ratings'
print_info "Verificando topic 'ratings'..."
if ! docker exec kafka kafka-topics --list --bootstrap-server localhost:9092 2>/dev/null | grep -q "^ratings$"; then
    print_error "Topic 'ratings' no existe"
    echo "   Ejecuta: ./scripts/recsys-utils.sh kafka-create ratings 6 1"
    exit 1
fi
print_success "Topic 'ratings' existe"

# 3. Verificar datos en HDFS
print_info "Verificando metadata en HDFS..."
if ! docker exec namenode hadoop fs -test -d /data/content_features/movies_features 2>/dev/null; then
    print_error "Movies features no encontrados en HDFS"
    echo "   Ejecuta primero la Fase 4 (feature engineering)"
    exit 1
fi
print_success "Metadata disponible en HDFS"

# 4. Instalar dependencias Python (numpy para Dirichlet)
print_info "Verificando dependencias Python..."
if ! docker exec spark-master python3 -c "import numpy" 2>/dev/null; then
    print_info "Instalando numpy..."
    docker exec -u root spark-master pip install -q numpy
    print_success "Numpy instalado"
else
    print_success "Numpy ya instalado"
fi

# 5. Copiar script a shared
print_info "Copiando script a directorio compartido..."
mkdir -p "$ROOT_DIR/shared/streaming"
cp "$ROOT_DIR/movies/src/streaming/synthetic_ratings_generator.py" "$ROOT_DIR/shared/streaming/"
print_success "Script copiado"

# 6. Ejecutar generador
echo ""
echo "========================================================================"
echo "EJECUTANDO GENERADOR DE RATINGS SINTÉTICOS"
echo "========================================================================"
echo "Throughput: ${ROWS_PER_SECOND} ratings/segundo"
echo "Topic Kafka: ratings"
echo "Presiona Ctrl+C para detener"
echo "========================================================================"
echo ""

docker exec spark-master spark-submit \
    --master spark://spark-master:7077 \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1 \
    --conf spark.sql.shuffle.partitions=20 \
    --conf spark.streaming.backpressure.enabled=true \
    --conf spark.streaming.kafka.maxRatePerPartition=100 \
    /opt/spark/work-dir/streaming/synthetic_ratings_generator.py \
    "$ROWS_PER_SECOND"
