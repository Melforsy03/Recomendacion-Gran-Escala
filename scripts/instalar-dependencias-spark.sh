#!/bin/bash
###############################################################################
# Script: instalar-dependencias-spark.sh
# Descripción: Instala dependencias de Python en contenedores Spark corriendo
# Uso: ./scripts/instalar-dependencias-spark.sh
###############################################################################

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Directorio del proyecto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"

echo "==============================================================================="
echo -e "${BLUE}📦 INSTALACIÓN DE DEPENDENCIAS PYTHON EN SPARK${NC}"
echo "==============================================================================="
echo ""

# Verificar que requirements.txt existe
if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
    echo -e "${RED}❌ Error: No se encuentra $REQUIREMENTS_FILE${NC}"
    exit 1
fi

# Verificar que los contenedores están corriendo
echo -e "${YELLOW}🔍 Verificando contenedores Spark...${NC}"

if ! docker ps --format "{{.Names}}" | grep -q "^spark-master$"; then
    echo -e "${RED}❌ Error: spark-master no está corriendo${NC}"
    echo -e "${YELLOW}💡 Inicia el sistema: ./scripts/start-system.sh${NC}"
    exit 1
fi
echo -e "${GREEN}✅ spark-master está corriendo${NC}"

if ! docker ps --format "{{.Names}}" | grep -q "^spark-worker$"; then
    echo -e "${RED}❌ Error: spark-worker no está corriendo${NC}"
    echo -e "${YELLOW}💡 Inicia el sistema: ./scripts/start-system.sh${NC}"
    exit 1
fi
echo -e "${GREEN}✅ spark-worker está corriendo${NC}"

echo ""
echo "==============================================================================="
echo -e "${YELLOW}📦 Instalando dependencias en spark-master...${NC}"
echo "==============================================================================="
echo ""

# Copiar requirements al contenedor master
docker cp "$REQUIREMENTS_FILE" spark-master:/tmp/requirements_temp.txt

# Instalar en master
docker exec spark-master bash -c "pip install --quiet -r /tmp/requirements_temp.txt && rm /tmp/requirements_temp.txt"

if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}✅ Dependencias instaladas en spark-master${NC}"
else
    echo -e "${RED}❌ Error instalando dependencias en spark-master${NC}"
    exit 1
fi

echo ""
echo "==============================================================================="
echo -e "${YELLOW}📦 Instalando dependencias en spark-worker...${NC}"
echo "==============================================================================="
echo ""

# Copiar requirements al contenedor worker
docker cp "$REQUIREMENTS_FILE" spark-worker:/tmp/requirements_temp.txt

# Instalar en worker
docker exec spark-worker bash -c "pip install --quiet -r /tmp/requirements_temp.txt && rm /tmp/requirements_temp.txt"

if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}✅ Dependencias instaladas en spark-worker${NC}"
else
    echo -e "${RED}❌ Error instalando dependencias en spark-worker${NC}"
    exit 1
fi

echo ""
echo "==============================================================================="
echo -e "${YELLOW}🔍 Verificando instalación...${NC}"
echo "==============================================================================="
echo ""

# Verificar numpy en master
echo -e "${CYAN}Verificando numpy en spark-master:${NC}"
NUMPY_VERSION=$(docker exec spark-master python3 -c "import numpy; print(numpy.__version__)" 2>/dev/null)
if [[ -n "$NUMPY_VERSION" ]]; then
    echo -e "${GREEN}✅ numpy ${NUMPY_VERSION} instalado${NC}"
else
    echo -e "${RED}❌ numpy no encontrado${NC}"
fi

# Verificar pandas en master
echo -e "${CYAN}Verificando pandas en spark-master:${NC}"
PANDAS_VERSION=$(docker exec spark-master python3 -c "import pandas; print(pandas.__version__)" 2>/dev/null)
if [[ -n "$PANDAS_VERSION" ]]; then
    echo -e "${GREEN}✅ pandas ${PANDAS_VERSION} instalado${NC}"
else
    echo -e "${RED}❌ pandas no encontrado${NC}"
fi

# Verificar kafka-python en master
echo -e "${CYAN}Verificando kafka-python en spark-master:${NC}"
KAFKA_VERSION=$(docker exec spark-master python3 -c "import kafka; print(kafka.__version__)" 2>/dev/null)
if [[ -n "$KAFKA_VERSION" ]]; then
    echo -e "${GREEN}✅ kafka-python ${KAFKA_VERSION} instalado${NC}"
else
    echo -e "${RED}❌ kafka-python no encontrado${NC}"
fi

echo ""
echo "==============================================================================="
echo -e "${GREEN}✅ INSTALACIÓN COMPLETADA${NC}"
echo "==============================================================================="
echo ""
echo -e "${BLUE}📋 Dependencias principales instaladas:${NC}"
echo -e "   • numpy (computación científica)"
echo -e "   • pandas (análisis de datos)"
echo -e "   • kafka-python (streaming)"
echo -e "   • python-dateutil, pytz (manejo de fechas)"
echo ""
echo -e "${BLUE}💡 Próximos pasos:${NC}"
echo -e "   1. Generar datos: ${YELLOW}./scripts/run-latent-generator.sh 100${NC}"
echo -e "   2. Procesar streaming: ${YELLOW}./scripts/run-streaming-processor.sh${NC}"
echo ""
echo "==============================================================================="
