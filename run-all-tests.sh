#!/bin/bash

echo "=========================================="
echo "Test Completo del Sistema"
echo "=========================================="
echo ""
echo "Este script ejecutará todos los tests de verificación"
echo ""

# Dar permisos de ejecución
chmod +x test-connectivity.sh test-hdfs.sh test-kafka.sh test-spark-standalone.sh test-spark-kafka.sh

echo "Esperando 30 segundos para que los servicios se estabilicen..."
sleep 30

# Test 1: Conectividad
echo ""
echo "================================================"
bash test-connectivity.sh

# Test 2: HDFS
echo ""
echo "================================================"
bash test-hdfs.sh

# Test 3: Kafka
echo ""
echo "================================================"
bash test-kafka.sh

# Test 4: Spark Standalone
echo ""
echo "================================================"
bash test-spark-standalone.sh

# Test 5: Spark + Kafka Integration
echo ""
echo "================================================"
bash test-spark-kafka.sh

echo ""
echo "=========================================="
echo "Todos los tests completados!"
echo "=========================================="
echo ""
echo "Revisa los resultados arriba para verificar que todos los componentes funcionan correctamente."
echo ""
