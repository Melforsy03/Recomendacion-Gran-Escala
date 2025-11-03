#!/bin/bash
###############################################################################
# Script: run-latent-generator.sh
# Descripción: Lanza el generador latente analítico de ratings sintéticos
# Uso: ./scripts/run-latent-generator.sh [THROUGHPUT]
#      THROUGHPUT = ratings por segundo (default: 100)
###############################################################################

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directorio del proyecto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Archivo del generador
GENERATOR_SCRIPT="$PROJECT_ROOT/movies/src/streaming/latent_generator.py"

# Throughput (ratings/segundo)
THROUGHPUT="${1:-100}"

# Validar que el script existe
if [[ ! -f "$GENERATOR_SCRIPT" ]]; then
    echo -e "${RED}❌ Error: No se encuentra $GENERATOR_SCRIPT${NC}"
    exit 1
fi

# Banner
echo "==============================================================================="
echo -e "${BLUE}🚀 GENERADOR LATENTE ANALÍTICO DE RATINGS SINTÉTICOS${NC}"
echo "==============================================================================="
echo -e "📍 Proyecto: $(basename "$PROJECT_ROOT")"
echo -e "🎯 Throughput: ${GREEN}${THROUGHPUT}${NC} ratings/segundo"
echo -e "📝 Script: $(basename "$GENERATOR_SCRIPT")"
echo "==============================================================================="
echo ""

# Verificar que Spark esté disponible
echo -e "${YELLOW}🔍 Verificando disponibilidad de Spark...${NC}"
if ! docker ps | grep -q spark-master; then
    echo -e "${RED}❌ Error: Spark master no está corriendo${NC}"
    echo -e "${YELLOW}💡 Sugerencia: Ejecuta ./scripts/start-system.sh primero${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Spark disponible${NC}"

# Verificar que Kafka esté disponible
echo -e "${YELLOW}🔍 Verificando disponibilidad de Kafka...${NC}"
if ! docker ps | grep -q kafka; then
    echo -e "${RED}❌ Error: Kafka no está corriendo${NC}"
    echo -e "${YELLOW}💡 Sugerencia: Ejecuta ./scripts/start-system.sh primero${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Kafka disponible${NC}"

# Verificar topic 'ratings'
echo -e "${YELLOW}🔍 Verificando topic 'ratings' en Kafka...${NC}"
if docker exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list 2>/dev/null | grep -q "^ratings$"; then
    echo -e "${GREEN}✅ Topic 'ratings' existe${NC}"
else
    echo -e "${YELLOW}⚠️  Topic 'ratings' no existe${NC}"
    echo -e "${YELLOW}💡 Se creará automáticamente al enviar mensajes${NC}"
fi

echo ""
echo "==============================================================================="
echo -e "${GREEN}▶️  INICIANDO GENERADOR...${NC}"
echo "==============================================================================="
echo ""

# Copiar script a contenedor
echo -e "${YELLOW}ℹ Copiando script a spark-master...${NC}"
docker cp "$GENERATOR_SCRIPT" spark-master:/tmp/latent_generator.py

# Ejecutar con spark-submit (CON PAQUETE KAFKA)
docker exec spark-master spark-submit \
    --master spark://spark-master:7077 \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1 \
    --conf spark.sql.shuffle.partitions=10 \
    --conf spark.streaming.backpressure.enabled=true \
    --conf spark.streaming.kafka.maxRatePerPartition=200 \
    /tmp/latent_generator.py "$THROUGHPUT"

# Capturar código de salida
EXIT_CODE=$?

echo ""
echo "==============================================================================="
if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}✅ GENERADOR FINALIZADO CORRECTAMENTE${NC}"
else
    echo -e "${RED}❌ GENERADOR FINALIZADO CON ERRORES (código: $EXIT_CODE)${NC}"
fi
echo "==============================================================================="
echo ""

exit $EXIT_CODE
