#!/bin/bash

echo "=========================================="
echo "Test de Spark - Modo Standalone"
echo "=========================================="
echo ""

echo "1. Ejecutando prueba simple de Spark (cálculo de Pi)..."
docker exec spark-master spark-submit \
    --master spark://spark-master:7077 \
    --class org.apache.spark.examples.SparkPi \
    /opt/spark/examples/jars/spark-examples_2.12-3.4.1.jar \
    10

echo ""
echo "✓ Test de Spark Standalone completado"
echo ""
