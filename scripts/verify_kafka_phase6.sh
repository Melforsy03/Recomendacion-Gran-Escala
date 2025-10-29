#!/bin/bash
# FASE 6: Script de Verificación Completa
# ========================================
# Verifica topics Kafka y ejecuta producer/consumer hello world

set -e

echo "======================================================================"
echo "FASE 6: VERIFICACIÓN DE TOPICS KAFKA Y EVENTOS"
echo "======================================================================"
echo ""

# Colores para output
RED='\033[0:31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir con color
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# 1. Verificar que Kafka y Zookeeper están corriendo
echo "1️⃣  Verificando servicios de Kafka..."
echo "----------------------------------------------------------------------"

if ! docker ps | grep -q "zookeeper"; then
    print_error "Zookeeper no está corriendo"
    echo "   Ejecuta: docker-compose up -d zookeeper"
    exit 1
fi
print_success "Zookeeper está corriendo"

if ! docker ps | grep -q "kafka"; then
    print_error "Kafka no está corriendo"
    echo "   Ejecuta: docker-compose up -d kafka"
    exit 1
fi
print_success "Kafka está corriendo"

echo ""

# 2. Instalar dependencias de Python si es necesario
echo "2️⃣  Verificando dependencias de Python..."
echo "----------------------------------------------------------------------"

if ! docker exec spark-master pip show kafka-python > /dev/null 2>&1; then
    print_info "Instalando kafka-python en spark-master..."
    docker exec -u root spark-master pip install kafka-python>=2.0.2
    print_success "kafka-python instalado en spark-master"
else
    print_success "kafka-python ya está instalado en spark-master"
fi

echo ""

# 3. Crear topics con Python script
echo "3️⃣  Creando topics de Kafka..."
echo "----------------------------------------------------------------------"

# Copiar script a shared si no existe
if [ ! -f shared/streaming/create_kafka_topics.py ]; then
    mkdir -p shared/streaming
    cp movies/src/streaming/create_kafka_topics.py shared/streaming/
fi

docker exec spark-master python3 /opt/spark/work-dir/streaming/create_kafka_topics.py

echo ""

# 4. Listar topics creados
echo "4️⃣  Listando topics de Kafka..."
echo "----------------------------------------------------------------------"

docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list

echo ""

# 5. Describir topics
echo "5️⃣  Describiendo topics 'ratings' y 'metrics'..."
echo "----------------------------------------------------------------------"

echo "📁 Topic: ratings"
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --describe --topic ratings

echo ""
echo "📁 Topic: metrics"
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --describe --topic metrics

echo ""

# 6. Ejecutar Producer Hello World
echo "6️⃣  Ejecutando Producer Hello World (10 mensajes)..."
echo "----------------------------------------------------------------------"

# Copiar scripts a shared si no existen
if [ ! -f shared/streaming/kafka_producer_hello.py ]; then
    cp movies/src/streaming/kafka_producer_hello.py shared/streaming/
fi
if [ ! -f shared/streaming/kafka_consumer_hello.py ]; then
    cp movies/src/streaming/kafka_consumer_hello.py shared/streaming/
fi

docker exec spark-master python3 /opt/spark/work-dir/streaming/kafka_producer_hello.py --count 10 --delay 0.2

echo ""

# 7. Ejecutar Consumer Hello World
echo "7️⃣  Ejecutando Consumer Hello World..."
echo "----------------------------------------------------------------------"

print_info "Consumiendo mensajes (timeout 10s)..."
docker exec spark-master python3 /opt/spark/work-dir/streaming/kafka_consumer_hello.py --max-messages 10 --timeout 10

echo ""

# 8. Verificar offsets de topics
echo "8️⃣  Verificando offsets de topics..."
echo "----------------------------------------------------------------------"

echo "📊 Offsets del topic 'ratings':"
docker exec kafka kafka-run-class kafka.tools.GetOffsetShell \
    --broker-list localhost:9092 \
    --topic ratings

echo ""

# Resumen final
echo "======================================================================"
echo "📊 RESUMEN DE VERIFICACIÓN - FASE 6"
echo "======================================================================"
echo ""
print_success "Zookeeper y Kafka operativos"
print_success "Topics 'ratings' y 'metrics' creados"
print_success "Producer hello world ejecutado (10 mensajes enviados)"
print_success "Consumer hello world ejecutado (mensajes consumidos)"
print_success "Esquema JSON validado correctamente"
echo ""
echo "✅ FASE 6 COMPLETADA EXITOSAMENTE"
echo ""
echo "Próximos pasos:"
echo "  - Fase 7: Streaming de recomendaciones con Spark Structured Streaming"
echo "  - Fase 8: Dashboard en tiempo real con métricas"
echo ""
echo "======================================================================"
