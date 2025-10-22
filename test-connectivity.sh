#!/bin/bash

echo "=========================================="
echo "Test de Conectividad del Sistema"
echo "=========================================="
echo ""

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para verificar servicios
check_service() {
    local service_name=$1
    local url=$2
    local description=$3
    
    echo -n "Verificando $description... "
    if curl -s -f "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ OK${NC}"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        return 1
    fi
}

# Función para verificar puertos
check_port() {
    local service_name=$1
    local host=$2
    local port=$3
    local description=$4
    
    echo -n "Verificando $description (puerto $port)... "
    if nc -z -w5 "$host" "$port" 2>/dev/null; then
        echo -e "${GREEN}✓ OK${NC}"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        return 1
    fi
}

echo "1. HDFS NameNode"
check_service "namenode" "http://localhost:9870" "HDFS NameNode Web UI"
check_port "namenode" "localhost" "9000" "HDFS NameNode RPC"
echo ""

echo "2. YARN ResourceManager"
check_service "resourcemanager" "http://localhost:8088" "YARN ResourceManager Web UI"
check_port "resourcemanager" "localhost" "8032" "YARN ResourceManager RPC"
echo ""

echo "3. YARN NodeManager"
check_service "nodemanager" "http://localhost:8042" "YARN NodeManager Web UI"
echo ""

echo "4. Spark Master"
check_service "spark-master" "http://localhost:8080" "Spark Master Web UI"
check_port "spark-master" "localhost" "7077" "Spark Master RPC"
echo ""

echo "5. Spark Worker"
check_service "spark-worker" "http://localhost:8081" "Spark Worker Web UI"
echo ""

echo "6. Zookeeper"
check_port "zookeeper" "localhost" "2181" "Zookeeper"
echo ""

echo "7. Kafka"
check_port "kafka" "localhost" "9092" "Kafka Internal"
check_port "kafka" "localhost" "9093" "Kafka External"
echo ""

echo "=========================================="
echo "Resumen de Verificación"
echo "=========================================="
echo ""
echo -e "${YELLOW}Servicios Web UI Disponibles:${NC}"
echo "  - HDFS NameNode:        http://localhost:9870"
echo "  - YARN ResourceManager: http://localhost:8088"
echo "  - YARN NodeManager:     http://localhost:8042"
echo "  - Spark Master:         http://localhost:8080"
echo "  - Spark Worker:         http://localhost:8081"
echo ""
echo -e "${YELLOW}Puertos de Servicios:${NC}"
echo "  - HDFS RPC:             9000"
echo "  - Spark Master:         7077"
echo "  - Kafka Internal:       9092"
echo "  - Kafka External:       9093"
echo "  - Zookeeper:            2181"
echo ""
