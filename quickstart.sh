#!/bin/bash

echo "=========================================="
echo "Guía de Inicio Rápido"
echo "=========================================="
echo ""
echo "Bienvenido al sistema de Big Data para Recomendación en Gran Escala"
echo ""
echo "PASO 1: Iniciar el sistema"
echo "  $ ./start-system.sh"
echo ""
echo "PASO 2: Verificar conectividad"
echo "  $ ./test-connectivity.sh"
echo ""
echo "PASO 3: Ejecutar tests de funcionalidad"
echo "  $ ./run-all-tests.sh"
echo ""
echo "PASO 4: Acceder a las interfaces web"
echo "  - HDFS NameNode:        http://localhost:9870"
echo "  - YARN ResourceManager: http://localhost:8088"
echo "  - Spark Master:         http://localhost:8080"
echo ""
echo "PASO 5: Ejecutar ejemplos"
echo "  $ cd examples"
echo "  $ cat README.md"
echo ""
echo "=========================================="
echo ""
read -p "¿Deseas iniciar el sistema ahora? (s/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Ss]$ ]]; then
    ./start-system.sh
else
    echo "Puedes iniciar el sistema cuando quieras con: ./start-system.sh"
fi
