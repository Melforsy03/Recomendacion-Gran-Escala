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

# Función de limpieza para detener procesos al cerrar el script
cleanup() {
    echo ""
    echo "==============================================================================="
    echo -e "${YELLOW}🛑 Interrupción detectada. Deteniendo procesos en spark-master...${NC}"
    # Intentar matar el proceso por nombre
    docker exec spark-master pkill -f "latent_generator.py" 2>/dev/null || true
    echo -e "${GREEN}✅ Limpieza completada.${NC}"
    echo "==============================================================================="
    exit 0
}
trap cleanup SIGINT SIGTERM

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

# Verificar estado del checkpoint
echo -e "${YELLOW}🔍 Verificando checkpoint...${NC}"
if docker exec namenode hadoop fs -test -d /checkpoints/latent_ratings 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Checkpoint existente detectado en /checkpoints/latent_ratings${NC}"
    echo -e "${YELLOW}💡 Si hay errores, ejecuta: ./scripts/clean-checkpoints.sh latent${NC}"
else
    echo -e "${GREEN}✅ No hay checkpoint previo (inicio limpio)${NC}"
fi

echo ""
echo "==============================================================================="
echo -e "${GREEN}▶️  INICIANDO GENERADOR...${NC}"
echo "==============================================================================="
echo ""

# Verificar dependencias de Python
echo -e "${YELLOW}🔍 Verificando dependencias de Python...${NC}"
DEPS_CHECK=$(docker exec spark-master bash -c "python3 -c 'import numpy, pandas, kafka' 2>&1")
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Error: Dependencias de Python no disponibles${NC}"
    echo -e "${YELLOW}💡 Intentando reinstalar dependencias...${NC}"
    docker exec spark-master bash -c "
        PYTHON_VERSION=\$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        SITE_PACKAGES=/opt/spark-python-libs/lib/python\${PYTHON_VERSION}/site-packages
        mkdir -p \${SITE_PACKAGES}
        pip install --no-warn-script-location --target=\${SITE_PACKAGES} --trusted-host pypi.org --trusted-host files.pythonhosted.org -r /tmp/requirements.txt
    "
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Error: No se pudieron instalar las dependencias${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✅ Dependencias de Python disponibles${NC}"

# Copiar script a contenedor
echo -e "${YELLOW}ℹ Copiando script a spark-master...${NC}"
docker cp "$GENERATOR_SCRIPT" spark-master:/tmp/latent_generator.py

# Obtener versión de Python y configurar PYTHONPATH
PYTHON_VERSION=$(docker exec spark-master python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
PYTHON_LIBS_PATH="/opt/spark-python-libs/lib/python${PYTHON_VERSION}/site-packages"

echo -e "${YELLOW}ℹ Configurando PYTHONPATH: ${PYTHON_LIBS_PATH}${NC}"

# Ejecutar con spark-submit (CON PAQUETE KAFKA Y RECURSOS LIMITADOS)
docker exec spark-master bash -c "
export PYTHONPATH=${PYTHON_LIBS_PATH}:\$PYTHONPATH
spark-submit \
    --master spark://spark-master:7077 \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1 \
    --conf spark.sql.shuffle.partitions=8 \
    --conf spark.streaming.backpressure.enabled=true \
    --conf spark.streaming.kafka.maxRatePerPartition=200 \
    --conf spark.driver.memory=512m \
    --conf spark.executor.memory=512m \
    --conf spark.executor.cores=1 \
    --conf spark.cores.max=1 \
    --conf spark.scheduler.mode=FAIR \
    --conf spark.scheduler.allocation.file=file:///opt/spark/conf/fairscheduler.xml \
    --conf spark.scheduler.pool=generator \
    --conf spark.executorEnv.PYTHONPATH=${PYTHON_LIBS_PATH} \
    /tmp/latent_generator.py $THROUGHPUT
"

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
