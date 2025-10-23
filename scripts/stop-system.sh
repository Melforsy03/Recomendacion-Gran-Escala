#!/bin/bash
set -e

echo "=========================================="
echo "Deteniendo Sistema de Big Data"
echo "=========================================="
echo ""

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

read -p "¿Deseas eliminar también los volúmenes de datos? (s/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo "Deteniendo servicios y eliminando volúmenes..."
    $DOCKER_COMPOSE -f "$ROOT_DIR/docker-compose.yml" down -v
    echo ""
    echo "✓ Sistema detenido y datos eliminados"
else
    echo "Deteniendo servicios (manteniendo datos)..."
    $DOCKER_COMPOSE -f "$ROOT_DIR/docker-compose.yml" down
    echo ""
    echo "✓ Sistema detenido (datos preservados)"
fi

echo ""
echo "Para volver a iniciar el sistema, ejecuta:"
echo "  $(dirname "$SCRIPT_DIR")/scripts/start-system.sh"
echo ""
