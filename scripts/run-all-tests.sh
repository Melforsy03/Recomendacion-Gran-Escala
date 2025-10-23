#!/bin/bash
set -e

echo "=========================================="
echo "Test Completo del Sistema"
echo "=========================================="
echo ""
echo "Este script ejecutará todos los tests de verificación"
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

# Dar permisos de ejecución
chmod +x \
  "$ROOT_DIR/tests/test-connectivity.sh" \
  "$ROOT_DIR/tests/test-hdfs.sh" \
  "$ROOT_DIR/tests/test-kafka.sh" \
  "$ROOT_DIR/tests/test-spark-standalone.sh" \
  "$ROOT_DIR/tests/test-spark-kafka.sh"

echo "Esperando 30 segundos para que los servicios se estabilicen..."
sleep 30

# Test 1: Conectividad
echo ""
echo "================================================"
bash "$ROOT_DIR/tests/test-connectivity.sh"

# Test 2: HDFS
echo ""
echo "================================================"
bash "$ROOT_DIR/tests/test-hdfs.sh"

# Test 3: Kafka
echo ""
echo "================================================"
bash "$ROOT_DIR/tests/test-kafka.sh"

# Test 4: Spark Standalone
echo ""
echo "================================================"
bash "$ROOT_DIR/tests/test-spark-standalone.sh"

# Test 5: Spark + Kafka Integration
echo ""
echo "================================================"
bash "$ROOT_DIR/tests/test-spark-kafka.sh"

echo ""
echo "=========================================="
echo "Todos los tests completados!"
echo "=========================================="
echo ""
echo "Revisa los resultados arriba para verificar que todos los componentes funcionan correctamente."
echo ""
