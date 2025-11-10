#!/bin/bash
# ============================================================================
# Script de Verificación Fase 9 - Sistema de Analytics y Dashboard
# ============================================================================

echo "=================================================="
echo "  Verificación del Sistema Fase 9"
echo "=================================================="
echo ""

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Contador de verificaciones exitosas
PASSED=0
FAILED=0

# Función para verificar
check() {
    local name="$1"
    local command="$2"
    
    echo -n "Verificando $name... "
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ OK${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        ((FAILED++))
        return 1
    fi
}

echo "=== 1. Verificando Contenedores ==="
check "Dashboard" "docker compose ps dashboard | grep -q healthy"
check "API" "docker compose ps api | grep -q Up"
check "Kafka" "docker compose ps kafka | grep -q Up"
check "Spark Master" "docker compose ps spark-master | grep -q healthy"
check "Spark Worker" "docker compose ps spark-worker | grep -q Up"
check "HDFS Namenode" "docker compose ps namenode | grep -q Up"
echo ""

echo "=== 2. Verificando Endpoints API ==="
check "API Health (/metrics/health)" "curl -sf http://localhost:8000/metrics/health > /dev/null"
check "API Root (/)" "curl -sf http://localhost:8000/ > /dev/null"
check "API Docs (/docs)" "curl -sf http://localhost:8000/docs > /dev/null"
echo ""

echo "=== 3. Verificando Dashboard ==="
check "Dashboard UI (puerto 8501)" "curl -sf http://localhost:8501 > /dev/null"
echo ""

echo "=== 4. Verificando Estructura HDFS ==="
check "Directorio /streams/ratings" "docker compose exec namenode hadoop fs -test -d /streams/ratings/raw"
check "Directorio /outputs" "docker compose exec namenode hadoop fs -test -d /outputs"
echo ""

echo "=== 5. Estado de los Servicios ==="
echo ""
echo "--- Métricas de la API ---"
curl -s http://localhost:8000/metrics/health | jq '.' 2>/dev/null || echo "No disponible"
echo ""

echo "--- Topics de Kafka ---"
docker compose exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list 2>/dev/null | grep -E "(ratings|metrics)" || echo "Topics no encontrados"
echo ""

echo "=== Resumen ==="
echo -e "Verificaciones exitosas: ${GREEN}${PASSED}${NC}"
echo -e "Verificaciones fallidas: ${RED}${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ Todos los componentes están funcionando correctamente${NC}"
    echo ""
    echo "Próximos pasos:"
    echo "  1. Generar datos: ./scripts/run-latent-generator.sh"
    echo "  2. Procesar streaming: ./scripts/run-streaming-processor.sh"
    echo "  3. Ver dashboard: http://localhost:8501"
    exit 0
else
    echo -e "${RED}⚠️  Algunos componentes tienen problemas${NC}"
    echo "Revisa los logs: docker compose logs <servicio>"
    exit 1
fi
