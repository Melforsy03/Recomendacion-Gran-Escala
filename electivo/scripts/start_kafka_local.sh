#!/bin/bash
# ==========================================
# 🟢 Start local Kafka + Zookeeper + Topic
# ==========================================
# Directorio donde tienes Kafka instalado localmente
KAFKA_HOME="$HOME/Escritorio/Big-Data/electivo/kafka_2.13-2.8.1"
TOPIC_NAME="movies"
BROKER="localhost:9092"

# ================================
# 1️⃣ Start Zookeeper (background)
# ================================
echo "🚀 Starting Zookeeper..."
nohup $KAFKA_HOME/bin/zookeeper-server-start.sh $KAFKA_HOME/config/zookeeper.properties > /tmp/zookeeper.log 2>&1 &
sleep 5

# =============================
# 2️⃣ Start Kafka broker (bg)
# =============================
echo "⚡ Starting Kafka broker..."
nohup $KAFKA_HOME/bin/kafka-server-start.sh $KAFKA_HOME/config/server.properties > /tmp/kafka.log 2>&1 &
sleep 8

# ========================================
# 3️⃣ Create topic if not already existing
# ========================================
echo "📦 Ensuring topic '$TOPIC_NAME' exists..."
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server $BROKER --list | grep -q "$TOPIC_NAME"
if [ $? -ne 0 ]; then
  echo "🆕 Creating topic $TOPIC_NAME..."
  $KAFKA_HOME/bin/kafka-topics.sh --create --topic "$TOPIC_NAME" \
      --bootstrap-server $BROKER \
      --partitions 1 --replication-factor 1
else
  echo "✅ Topic $TOPIC_NAME already exists."
fi

echo "🎬 Kafka local setup complete!"
echo "Logs → /tmp/zookeeper.log and /tmp/kafka.log"
