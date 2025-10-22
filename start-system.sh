#!/bin/bash

echo "=========================================="
echo "Iniciando Sistema de Big Data"
echo "=========================================="
echo ""

# Verificar que Docker está corriendo
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker no está corriendo. Por favor inicia Docker primero."
    exit 1
fi

echo "✓ Docker está corriendo"
echo ""

# Detectar versión de Docker Compose
if command -v docker compose &> /dev/null; then
    # Docker Compose v2 (integrado)
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    # Docker Compose v1 (standalone)
    DOCKER_COMPOSE="docker-compose"
else
    echo "❌ Error: Docker Compose no está instalado"
    exit 1
fi

echo "✓ docker-compose está instalado"
echo ""

# Detener servicios existentes si los hay
echo "Deteniendo servicios existentes (si los hay)..."
$DOCKER_COMPOSE down 2>/dev/null

echo ""
echo "Iniciando servicios..."
$DOCKER_COMPOSE up -d

echo ""
echo "Esperando que los servicios se inicialicen..."
echo "Esto puede tomar 1-2 minutos..."

# Esperar a que NameNode esté listo
echo -n "Esperando HDFS NameNode"
for i in {1..60}; do
    if curl -s -f http://localhost:9870 > /dev/null 2>&1; then
        echo " ✓"
        break
    fi
    echo -n "."
    sleep 2
done

# Esperar a que YARN ResourceManager esté listo
echo -n "Esperando YARN ResourceManager"
for i in {1..60}; do
    if curl -s -f http://localhost:8088 > /dev/null 2>&1; then
        echo " ✓"
        break
    fi
    echo -n "."
    sleep 2
done

# Esperar a que Spark Master esté listo
echo -n "Esperando Spark Master"
for i in {1..60}; do
    if curl -s -f http://localhost:8080 > /dev/null 2>&1; then
        echo " ✓"
        break
    fi
    echo -n "."
    sleep 2
done

# Esperar a que Kafka esté listo
echo -n "Esperando Kafka"
for i in {1..60}; do
    if docker exec kafka kafka-broker-api-versions.sh --bootstrap-server localhost:9092 > /dev/null 2>&1; then
        echo " ✓"
        break
    fi
    echo -n "."
    sleep 2
done

echo ""
echo "=========================================="
echo "✓ Sistema iniciado correctamente!"
echo "=========================================="
echo ""
echo "Interfaces Web Disponibles:"
echo "  - HDFS NameNode:        http://localhost:9870"
echo "  - YARN ResourceManager: http://localhost:8088"
echo "  - YARN NodeManager:     http://localhost:8042"
echo "  - Spark Master:         http://localhost:8080"
echo "  - Spark Worker:         http://localhost:8081"
echo ""
echo "Para verificar el estado de los servicios, ejecuta:"
echo "  ./test-connectivity.sh"
echo ""
echo "Para ejecutar todos los tests de funcionalidad:"
echo "  ./run-all-tests.sh"
echo ""
echo "Para ver los logs de los servicios:"
echo "  docker-compose logs -f"
echo ""
