#!/bin/bash

echo "=========================================="
echo "Test de Funcionalidad Kafka"
echo "=========================================="
echo ""

TOPIC_NAME="test-topic"

echo "1. Creando topic de prueba en Kafka..."
docker exec kafka kafka-topics --create \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 3 \
    --topic $TOPIC_NAME

echo ""
echo "2. Listando topics..."
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

echo ""
echo "3. Describiendo el topic..."
docker exec kafka kafka-topics --describe \
    --bootstrap-server localhost:9092 \
    --topic $TOPIC_NAME

echo ""
echo "4. Produciendo mensajes de prueba..."
echo -e "mensaje1\nmensaje2\nmensaje3" | docker exec -i kafka kafka-console-producer \
    --bootstrap-server localhost:9092 \
    --topic $TOPIC_NAME

echo ""
echo "5. Consumiendo mensajes (primeros 3)..."
docker exec kafka kafka-console-consumer \
    --bootstrap-server localhost:9092 \
    --topic $TOPIC_NAME \
    --from-beginning \
    --max-messages 3 \
    --timeout-ms 5000

echo ""
echo "✓ Test de Kafka completado"
echo ""
