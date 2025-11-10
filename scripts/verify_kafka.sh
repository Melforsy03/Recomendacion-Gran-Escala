#!/bin/bash
# Script para verificar y diagnosticar el estado de Kafka

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

function print_header() {
    echo ""
    echo -e "${BLUE}=========================================="
    echo "$1"
    echo -e "==========================================${NC}"
}

function print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

function print_error() {
    echo -e "${RED}✗${NC} $1"
}

function print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

print_header "Verificación de Kafka"

# 1. Verificar que el contenedor existe y está corriendo
echo ""
echo "1. Estado del contenedor Kafka:"
if docker ps --format "{{.Names}}" | grep -q "^kafka$"; then
    KAFKA_STATUS=$(docker inspect -f '{{.State.Status}}' kafka)
    KAFKA_UPTIME=$(docker inspect -f '{{.State.StartedAt}}' kafka)
    print_success "Contenedor 'kafka' está corriendo"
    echo "   Estado: $KAFKA_STATUS"
    echo "   Iniciado: $KAFKA_UPTIME"
else
    print_error "Contenedor 'kafka' no está corriendo"
    exit 1
fi

# 2. Verificar Zookeeper (dependencia de Kafka)
echo ""
echo "2. Estado de Zookeeper:"
if docker ps --format "{{.Names}}" | grep -q "^zookeeper$"; then
    print_success "Contenedor 'zookeeper' está corriendo"
    
    # Verificar conectividad Kafka -> Zookeeper
    echo "   Verificando conectividad Kafka -> Zookeeper..."
    if docker exec kafka nc -z zookeeper 2181 2>/dev/null; then
        print_success "Kafka puede conectarse a Zookeeper:2181"
    else
        print_error "Kafka NO puede conectarse a Zookeeper:2181"
    fi
else
    print_error "Contenedor 'zookeeper' no está corriendo"
fi

# 3. Verificar puerto 9092 (Kafka broker)
echo ""
echo "3. Puertos de Kafka:"
if nc -z localhost 9092 2>/dev/null || timeout 2 bash -c "</dev/tcp/localhost/9092" 2>/dev/null; then
    print_success "Puerto 9092 (interno) está escuchando"
else
    print_error "Puerto 9092 (interno) NO está escuchando"
fi

if nc -z localhost 29092 2>/dev/null || timeout 2 bash -c "</dev/tcp/localhost/29092" 2>/dev/null; then
    print_success "Puerto 29092 (externo) está escuchando"
else
    print_error "Puerto 29092 (externo) NO está escuchando"
fi

# 4. Verificar logs de Kafka
echo ""
echo "4. Análisis de logs de Kafka:"
if docker logs kafka 2>&1 | grep -q "started (kafka.server.KafkaServer)"; then
    print_success "Kafka Server ha iniciado correctamente"
else
    print_error "Kafka Server NO ha completado el inicio"
    echo ""
    echo "Últimos 20 logs:"
    docker logs kafka --tail 20
fi

# Verificar errores comunes
echo ""
echo "   Verificando errores comunes..."
if docker logs kafka 2>&1 | grep -qi "error"; then
    ERROR_COUNT=$(docker logs kafka 2>&1 | grep -ci "error")
    print_info "Encontrados $ERROR_COUNT mensajes de error en logs"
    echo ""
    echo "Últimos errores:"
    docker logs kafka 2>&1 | grep -i "error" | tail -5
else
    print_success "No se encontraron errores en los logs"
fi

# 5. Verificar API de Kafka
echo ""
echo "5. Verificación de API de Kafka:"
if timeout 5 docker exec kafka kafka-broker-api-versions.sh --bootstrap-server localhost:9092 > /dev/null 2>&1; then
    print_success "API de Kafka responde correctamente"
else
    print_error "API de Kafka NO responde (puede estar iniciando aún)"
fi

# 6. Listar topics
echo ""
echo "6. Topics de Kafka:"
if timeout 5 docker exec kafka kafka-topics --list --bootstrap-server localhost:9092 2>/dev/null; then
    print_success "Se pudieron listar los topics"
else
    print_error "No se pudieron listar los topics"
fi

# 7. Información del broker
echo ""
echo "7. Información del Broker:"
docker exec kafka bash -c 'cat /opt/kafka/config/server.properties | grep -E "^(broker.id|listeners|advertised.listeners|zookeeper.connect)" | grep -v "#"' || true

# 8. Métricas JMX (si están disponibles)
echo ""
echo "8. Estado de procesos Java en Kafka:"
if docker exec kafka pgrep -f kafka.Kafka >/dev/null 2>&1; then
    KAFKA_PID=$(docker exec kafka pgrep -f kafka.Kafka)
    print_success "Proceso Kafka corriendo (PID: $KAFKA_PID)"
    
    # Uso de memoria
    echo "   Uso de memoria del proceso:"
    docker exec kafka ps aux | grep -E "PID|$KAFKA_PID" | grep -v grep || true
else
    print_error "Proceso Kafka NO está corriendo"
fi

# Resumen final
print_header "Resumen"
echo ""
if docker logs kafka 2>&1 | grep -q "started (kafka.server.KafkaServer)" && \
   docker exec kafka pgrep -f kafka.Kafka >/dev/null 2>&1; then
    print_success "Kafka está funcionando correctamente"
    echo ""
    echo "Comandos útiles:"
    echo "  - Ver logs en tiempo real:  docker logs kafka -f"
    echo "  - Crear topic:              ./scripts/recsys-utils.sh kafka-create <nombre>"
    echo "  - Listar topics:            ./scripts/recsys-utils.sh kafka-topics"
    echo "  - Consumir mensajes:        ./scripts/recsys-utils.sh kafka-consume <topic>"
else
    print_error "Kafka tiene problemas. Revisa los logs arriba."
    echo ""
    echo "Comandos de diagnóstico:"
    echo "  - Ver todos los logs:       docker logs kafka"
    echo "  - Reiniciar Kafka:          docker restart kafka"
    echo "  - Verificar Zookeeper:      docker exec zookeeper zkServer.sh status"
fi
echo ""
