#!/bin/bash
set -e

echo "=========================================="
echo "Guía de Inicio Rápido"
echo "=========================================="
echo ""
echo "Bienvenido al sistema de Big Data para Recomendación en Gran Escala"
echo ""

# Directorio del script
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"

echo "PASO 1: Iniciar el sistema"
echo "  $ $SCRIPT_DIR/start-system.sh"
echo ""
echo "PASO 2: Verificar conectividad"
echo "  $ $(dirname "$SCRIPT_DIR")/tests/test-connectivity.sh"
echo ""
echo "PASO 3: Ejecutar tests de funcionalidad"
echo "  $ $SCRIPT_DIR/run-all-tests.sh"
echo ""
echo "PASO 4: Acceder a las interfaces web"
echo "  - HDFS NameNode:        http://localhost:9870"
echo "  - YARN ResourceManager: http://localhost:8088"
echo "  - Spark Master:         http://localhost:8080"
echo ""
echo "PASO 5: Ejecutar ejemplos"
echo "  $ cd $(dirname "$SCRIPT_DIR")/examples"
echo "  $ cat README.md"
echo ""
echo "=========================================="
echo ""
read -p "¿Deseas iniciar el sistema ahora? (s/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Ss]$ ]]; then
    "$SCRIPT_DIR/start-system.sh"
else
    echo "Puedes iniciar el sistema cuando quieras con: $SCRIPT_DIR/start-system.sh"
fi
