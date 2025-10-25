#!/bin/bash
# =====================================================
# 🎬 START ALL - Big Data Movies Pipeline (Docker + Host)
# Kafka (host) → Producer (Docker) → Spark Streaming → HDFS
# =====================================================

set -e

# ======== CONFIG ========
KAFKA_HOME="$HOME/Escritorio/Big-Data/electivo/kafka_2.13-2.8.1"
TOPIC_NAME="movies"
BROKER="172.17.0.1:9092"
CONTAINER_NAME="movies-project"
SPARK_SCRIPT="/app/scripts/spark_kafka_to_hdfs.py"
PRODUCER_SCRIPT="/app/scripts/movies_producer_kafka.py"
HDFS_CHECK_DIR="/user/movies/bronze/movies"

echo "=========================================="
echo "🚀 INICIANDO PIPELINE BIG DATA MOVIES"
echo "=========================================="
sleep 1

# ======== 1️⃣ ZOOKEEPER + KAFKA ========
echo "🦓 Iniciando Zookeeper..."
nohup $KAFKA_HOME/bin/zookeeper-server-start.sh $KAFKA_HOME/config/zookeeper.properties > /tmp/zookeeper.log 2>&1 &
sleep 5

echo "☕ Iniciando Kafka Broker..."
nohup $KAFKA_HOME/bin/kafka-server-start.sh $KAFKA_HOME/config/server.properties > /tmp/kafka.log 2>&1 &
sleep 8

# ======== 2️⃣ Crear topic si no existe ========
echo "📦 Verificando tópico '$TOPIC_NAME'..."
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server $BROKER --list | grep -q "$TOPIC_NAME"
if [ $? -ne 0 ]; then
  echo "🆕 Creando tópico $TOPIC_NAME..."
  $KAFKA_HOME/bin/kafka-topics.sh --create \
      --topic "$TOPIC_NAME" \
      --bootstrap-server $BROKER \
      --partitions 1 --replication-factor 1
else
  echo "✅ El tópico '$TOPIC_NAME' ya existe."
fi

# ======== 3️⃣ Verificar que el contenedor esté corriendo ========
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo "⚠️ El contenedor '$CONTAINER_NAME' no está corriendo. Levántalo primero:"
  echo "   docker start $CONTAINER_NAME"
  exit 1
fi

# ======== 4️⃣ Iniciar HDFS y YARN dentro del contenedor ========
echo "💾 Iniciando HDFS y YARN dentro de Docker..."
docker exec -d $CONTAINER_NAME bash -c "/opt/hadoop/sbin/start-dfs.sh && /opt/hadoop/sbin/start-yarn.sh"
sleep 10

# ======== 5️⃣ Ejecutar productor Kafka ========
echo "🎥 Ejecutando productor Kafka..."
docker exec -d $CONTAINER_NAME python3 $PRODUCER_SCRIPT
sleep 3

# ======== 6️⃣ Ejecutar Spark Streaming ========
echo "💎 Iniciando Spark Streaming..."
docker exec -d $CONTAINER_NAME python3 $SPARK_SCRIPT
sleep 10

# ======== 7️⃣ Verificar salida en HDFS ========
echo "🔍 Verificando archivos en HDFS..."
docker exec $CONTAINER_NAME hdfs dfs -ls $HDFS_CHECK_DIR || echo "⚠️ Aún no hay archivos en HDFS (espera unos segundos...)"

echo "=========================================="
echo "✅ TODO LEVANTADO CON ÉXITO"
echo "Kafka UI: localhost:9092"
echo "YARN UI : http://localhost:8088"
echo "HDFS UI : http://localhost:9870"
echo "=========================================="
echo "📜 Logs: /tmp/kafka.log, /tmp/zookeeper.log"
