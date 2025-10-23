#!/bin/bash
set -e

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

# Directorio del script y raíz del repositorio
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
find_repo_root() {
  local dir="$SCRIPT_DIR"
  while [[ "$dir" != "/" ]]; do
    if [[ -f "$dir/docker-compose.yml" ]]; then
      echo "$dir"; return
    fi
    dir="$(dirname "$dir")"
  done
  echo "$SCRIPT_DIR"
}
ROOT_DIR="$(find_repo_root)"

# Detectar Docker Compose
if command -v docker compose &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo "❌ Error: Docker Compose no está instalado"
    exit 1
fi

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
    echo "Ejecuta primero: $SCRIPT_DIR/start-system.sh"
    exit 1
fi

echo -e "${GREEN}✓ Todos los contenedores están corriendo${NC}"
echo ""
echo -e "${BLUE}Estados de los contenedores:${NC}"
$DOCKER_COMPOSE -f "$ROOT_DIR/docker-compose.yml" ps

echo ""
echo -e "${BLUE}Uso de recursos:${NC}"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | head -n 10

echo ""
echo -e "${YELLOW}Para más detalles, ejecuta:${NC}"
echo "  - Ver logs: $DOCKER_COMPOSE -f \"$ROOT_DIR/docker-compose.yml\" logs -f"
echo "  - Tests completos: $SCRIPT_DIR/run-all-tests.sh"
echo ""
