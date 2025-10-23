#!/bin/bash

echo "=========================================="
echo "Test de Funcionalidad HDFS"
echo "=========================================="
echo ""

# Crear archivo de prueba
echo "Este es un archivo de prueba para HDFS" > /tmp/test-hdfs.txt

echo "1. Creando directorio de prueba en HDFS..."
docker exec namenode hadoop fs -mkdir -p /test

echo ""
echo "2. Subiendo archivo de prueba a HDFS..."
docker exec -i namenode hadoop fs -put - /test/test-hdfs.txt < /tmp/test-hdfs.txt

echo ""
echo "3. Listando archivos en HDFS..."
docker exec namenode hadoop fs -ls /test

echo ""
echo "4. Leyendo archivo desde HDFS..."
docker exec namenode hadoop fs -cat /test/test-hdfs.txt

echo ""
echo "5. Obteniendo estadísticas de HDFS..."
docker exec namenode hadoop fs -df -h

echo ""
echo "✓ Test de HDFS completado"
echo ""
