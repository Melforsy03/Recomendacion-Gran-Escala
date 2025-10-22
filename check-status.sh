#!/bin/bash

echo "=========================================="
echo "Verificación Rápida del Sistema"
echo "=========================================="
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Verificando estado de contenedores...${NC}"
echo ""

# Verificar si los contenedores están corriendo
containers=("namenode" "datanode" "resourcemanager" "nodemanager" "spark-master" "spark-worker" "zookeeper" "kafka")

all_running=true
for container in "${containers[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo -e "  ${GREEN}✓${NC} $container está corriendo"
    else
        echo -e "  ${RED}✗${NC} $container NO está corriendo"
        all_running=false
    fi
done

echo ""

if [ "$all_running" = false ]; then
    echo -e "${RED}⚠ Algunos contenedores no están corriendo${NC}"
    echo ""
    echo "Ejecuta primero: ./start-system.sh"
    exit 1
fi

echo -e "${GREEN}✓ Todos los contenedores están corriendo${NC}"
echo ""
echo -e "${BLUE}Estados de los contenedores:${NC}"
docker-compose ps

echo ""
echo -e "${BLUE}Uso de recursos:${NC}"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | head -n 10

echo ""
echo -e "${YELLOW}Para más detalles, ejecuta:${NC}"
echo "  - Ver logs: docker-compose logs -f"
echo "  - Tests completos: ./run-all-tests.sh"
echo ""
