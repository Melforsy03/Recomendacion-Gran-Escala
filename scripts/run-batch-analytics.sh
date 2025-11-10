#!/bin/bash
###############################################################################
# Script: run-batch-analytics.sh
# Descripción: Ejecuta análisis batch sobre datos de streaming en HDFS
# Uso: ./scripts/run-batch-analytics.sh
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

# Archivo del procesador
ANALYTICS_SCRIPT="$PROJECT_ROOT/movies/src/analytics/batch_analytics.py"

# Validar que el script existe
if [[ ! -f "$ANALYTICS_SCRIPT" ]]; then
    echo -e "${RED}❌ Error: No se encuentra $ANALYTICS_SCRIPT${NC}"
    exit 1
fi

# Banner
echo "==============================================================================="
echo -e "${BLUE}📊 ANÁLISIS BATCH SOBRE DATOS EN HDFS${NC}"
echo "==============================================================================="
echo -e "📍 Proyecto: $(basename "$PROJECT_ROOT")"
echo -e "📝 Script: $(basename "$ANALYTICS_SCRIPT")"
echo -e "🎯 Análisis:"
echo -e "   • Distribución de ratings (global y por género)"
echo -e "   • Top-N películas por periodo (día/hora)"
echo -e "   • Películas trending (delta de ranking)"
echo "==============================================================================="
echo ""

# ==========================================
# Verificaciones
# ==========================================

echo -e "${YELLOW}🔍 Verificando prerequisitos...${NC}"

# Verificar que Spark esté disponible
if ! docker ps | grep -q spark-master; then
    echo -e "${RED}❌ Error: Spark master no está corriendo${NC}"
    echo -e "${YELLOW}💡 Sugerencia: Ejecuta ./scripts/start-system.sh primero${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Spark disponible${NC}"

# Verificar que HDFS esté disponible
if ! docker ps | grep -q namenode; then
    echo -e "${RED}❌ Error: HDFS namenode no está corriendo${NC}"
    echo -e "${YELLOW}💡 Sugerencia: Ejecuta ./scripts/start-system.sh primero${NC}"
    exit 1
fi
echo -e "${GREEN}✅ HDFS disponible${NC}"

# Verificar que existan datos de streaming
echo -e "${YELLOW}🔍 Verificando datos de streaming en HDFS...${NC}"
if ! docker exec namenode hadoop fs -test -d /streams/ratings/raw 2>/dev/null; then
    echo -e "${RED}❌ Error: No se encuentran datos de streaming en /streams/ratings/raw${NC}"
    echo -e "${YELLOW}💡 Sugerencia: Ejecuta primero:${NC}"
    echo -e "   1. ./scripts/run-latent-generator.sh 100"
    echo -e "   2. ./scripts/run-streaming-processor.sh"
    exit 1
fi
echo -e "${GREEN}✅ Datos de streaming disponibles${NC}"

# Verificar metadata de películas
echo -e "${YELLOW}🔍 Verificando metadata de películas...${NC}"
if ! docker exec namenode hadoop fs -test -d /data/content_features/movies_features 2>/dev/null; then
    echo -e "${RED}❌ Error: No se encuentra metadata de películas${NC}"
    echo -e "${YELLOW}💡 Sugerencia: Ejecuta la Fase 4 (feature engineering)${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Metadata disponible${NC}"

# Crear directorio de outputs si no existe
echo -e "${YELLOW}🔍 Preparando directorio de outputs...${NC}"
docker exec namenode hadoop fs -mkdir -p /outputs/analytics 2>/dev/null || true
echo -e "${GREEN}✅ Directorio de outputs preparado${NC}"

echo ""
echo "==============================================================================="
echo -e "${GREEN}▶️  INICIANDO ANÁLISIS BATCH...${NC}"
echo "==============================================================================="
echo ""

# Copiar script a contenedor
echo -e "${YELLOW}ℹ Copiando script a spark-master...${NC}"
docker cp "$ANALYTICS_SCRIPT" spark-master:/tmp/batch_analytics.py

# Ejecutar con spark-submit
echo -e "${YELLOW}ℹ Ejecutando análisis batch...${NC}"
echo ""

docker exec spark-master spark-submit \
    --master spark://spark-master:7077 \
    --conf spark.sql.adaptive.enabled=true \
    --conf spark.sql.adaptive.coalescePartitions.enabled=true \
    --conf spark.sql.shuffle.partitions=20 \
    --conf spark.driver.memory=512m \
    --conf spark.executor.memory=1g \
    --conf spark.executor.cores=1 \
    --conf spark.cores.max=1 \
    --conf spark.scheduler.mode=FAIR \
    --conf spark.scheduler.allocation.file=file:///opt/spark/conf/fairscheduler.xml \
    --conf spark.scheduler.pool=batch \
    /tmp/batch_analytics.py

# Capturar código de salida
EXIT_CODE=$?

echo ""
echo "==============================================================================="
if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}✅ ANÁLISIS BATCH COMPLETADO CORRECTAMENTE${NC}"
    echo "==============================================================================="
    echo ""
    echo -e "${BLUE}📁 Resultados disponibles en HDFS:${NC}"
    echo ""
    
    # Mostrar estructura de outputs
    docker exec namenode hadoop fs -ls -R /outputs/analytics 2>/dev/null || true
    
    echo ""
    echo -e "${BLUE}📊 Acceso a resultados:${NC}"
    echo ""
    echo "# Ver distribución global:"
    echo "docker exec namenode hadoop fs -cat /outputs/analytics/distributions/global/*.parquet | head"
    echo ""
    echo "# Ver películas trending:"
    echo "docker exec namenode hadoop fs -cat /outputs/analytics/trending/trending_movies/*.parquet | head"
    echo ""
    echo "# Listar todos los outputs:"
    echo "docker exec namenode hadoop fs -ls -R /outputs/analytics"
    
else
    echo -e "${RED}❌ ANÁLISIS BATCH FINALIZADO CON ERRORES (código: $EXIT_CODE)${NC}"
    echo "==============================================================================="
fi
echo ""

exit $EXIT_CODE
