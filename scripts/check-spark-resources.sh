#!/bin/bash
###############################################################################
# Script: check-spark-resources.sh
# Descripción: Verifica recursos disponibles en Spark Standalone
# Uso: ./scripts/check-spark-resources.sh
###############################################################################

set -euo pipefail

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "==============================================================================="
echo -e "${BLUE}🔍 VERIFICACIÓN DE RECURSOS SPARK${NC}"
echo "==============================================================================="
echo ""

# 1. Verificar que los servicios están corriendo
echo -e "${YELLOW}📦 Verificando servicios...${NC}"
if ! docker ps --format "{{.Names}}" | grep -q "^spark-master$"; then
    echo -e "${RED}❌ spark-master no está corriendo${NC}"
    exit 1
fi
if ! docker ps --format "{{.Names}}" | grep -q "^spark-worker$"; then
    echo -e "${RED}❌ spark-worker no está corriendo${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Servicios corriendo: spark-master, spark-worker${NC}"
echo ""

# 2. Verificar configuración del worker
echo -e "${YELLOW}⚙️  Configuración del Worker:${NC}"
docker exec spark-worker env | grep SPARK_WORKER | while read line; do
    echo "   $line"
done
echo ""

# 3. Verificar workers registrados
echo -e "${YELLOW}🔗 Workers registrados en Master:${NC}"
WORKERS_COUNT=$(docker exec spark-master curl -s http://localhost:8080 2>/dev/null | grep -o "Workers ([0-9]*)" | grep -o "[0-9]*" || echo "0")
if [ "$WORKERS_COUNT" -eq 0 ]; then
    echo -e "${RED}❌ No hay workers registrados${NC}"
    echo -e "${YELLOW}💡 Espera unos segundos o reinicia: docker compose restart spark-worker${NC}"
else
    echo -e "${GREEN}✅ Workers registrados: $WORKERS_COUNT${NC}"
fi
echo ""

# 4. Verificar recursos totales (desde logs del worker al iniciar)
echo -e "${YELLOW}💾 Recursos Disponibles:${NC}"
WORKER_MEMORY=$(docker exec spark-worker env | grep SPARK_WORKER_MEMORY | cut -d= -f2)
WORKER_CORES=$(docker exec spark-worker env | grep SPARK_WORKER_CORES | cut -d= -f2)
echo "   Memoria: $WORKER_MEMORY"
echo "   Cores:   $WORKER_CORES"
echo ""

# 5. Verificar aplicaciones en ejecución
echo -e "${YELLOW}🎯 Aplicaciones Spark:${NC}"
RUNNING_APPS=$(docker exec spark-master ps aux | grep "spark-submit" | grep -v grep | wc -l || echo "0")
if [ "$RUNNING_APPS" -gt 0 ]; then
    echo -e "${GREEN}✅ Aplicaciones corriendo: $RUNNING_APPS${NC}"
    docker exec spark-master ps aux | grep "spark-submit" | grep -v grep | awk '{print "   PID:", $2, "CMD:", $11, $12, $13}'
else
    echo -e "${YELLOW}ℹ  No hay aplicaciones Spark corriendo${NC}"
fi
echo ""

# 6. Recursos Docker
echo -e "${YELLOW}🐳 Uso de Recursos Docker:${NC}"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" spark-master spark-worker 2>/dev/null || true
echo ""

# 7. Resumen de capacidad
echo "==============================================================================="
echo -e "${BLUE}📊 RESUMEN DE CAPACIDAD${NC}"
echo "==============================================================================="
echo ""
echo "Recursos Totales:"
echo "  • Memoria: $WORKER_MEMORY"
echo "  • Cores:   $WORKER_CORES"
echo ""
echo "Configuración Recomendada por Job:"
echo "  • Streaming Processor:"
echo "    --conf spark.executor.memory=1g"
echo "    --conf spark.executor.cores=2"
echo "    --conf spark.cores.max=2"
echo ""
echo "  • Batch Analytics:"
echo "    --conf spark.executor.memory=1g"
echo "    --conf spark.executor.cores=2"
echo "    --conf spark.cores.max=2"
echo ""
echo "Jobs Simultáneos Permitidos: 2"
echo ""
echo "Acceso a UIs:"
echo "  • Spark Master: http://localhost:8080"
echo "  • Spark Worker: http://localhost:8081"
echo "  • Aplicación:   http://localhost:4040 (cuando hay job corriendo)"
echo ""
echo "==============================================================================="
