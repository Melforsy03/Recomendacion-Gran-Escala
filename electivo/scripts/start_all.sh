#!/bin/bash
set -e

# ======================================================
# 🔧 CONFIGURACIÓN DE ENTORNO
# ======================================================
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH
export KAFKA_HOME=/app/kafka_2.13-2.8.1
export PATH=$KAFKA_HOME/bin:$PATH
export HADOOP_HOME=/opt/hadoop
export PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH
# Verificar si el JAR ya existe
if [ ! -f "/opt/spark/jars/commons-pool2-2.11.1.jar" ]; then
    echo "📥 Descargando commons-pool2..."
    wget -O /tmp/commons-pool2-2.11.1.jar \
        https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar
    
    # Mover al directorio de Spark
    mv /tmp/commons-pool2-2.11.1.jar /opt/spark/jars/
    echo "✅ commons-pool2 instalado en /opt/spark/jars/"
else
    echo "✅ commons-pool2 ya está instalado"
fi

# Verificar la instalación
if [ -f "/opt/spark/jars/commons-pool2-2.11.1.jar" ]; then
    echo "🎯 commons-pool2 verificado correctamente"
else
    echo "❌ Error instalando commons-pool2"
    exit 1
fi
echo "🕒 Esperando HDFS..."
sleep 8

echo "📂 Verificando si el NameNode está formateado..."
if [ ! -d "/opt/hadoop/dfs/name" ] || [ -z "$(ls -A /opt/hadoop/dfs/name 2>/dev/null)" ]; then
  echo "⚙️ Formateando NameNode..."
  hdfs namenode -format -force
else
  echo "✅ NameNode ya formateado."
fi

echo "🚀 Iniciando HDFS sin SSH..."
$HADOOP_HOME/bin/hdfs --daemon start namenode
$HADOOP_HOME/bin/hdfs --daemon start datanode
$HADOOP_HOME/bin/hdfs --daemon start secondarynamenode
$HADOOP_HOME/bin/yarn --daemon start resourcemanager
$HADOOP_HOME/bin/yarn --daemon start nodemanager

echo "📁 Creando directorios HDFS..."
hdfs dfs -mkdir -p /user/movies/bronze/movies || true
hdfs dfs -mkdir -p /user/movies/checkpoints || true
hdfs dfs -mkdir -p /tmp || true
echo "✅ HDFS listo"

# ======================================================
# ⚡ KAFKA
# ======================================================
echo "🔧 Iniciando Kafka..."
$KAFKA_HOME/bin/zookeeper-server-start.sh -daemon $KAFKA_HOME/config/zookeeper.properties
sleep 5
$KAFKA_HOME/bin/kafka-server-start.sh -daemon $KAFKA_HOME/config/server.properties
sleep 10

echo "📦 Asegurando tópico 'movies'..."
$KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list | grep -q "^movies$" || \
  $KAFKA_HOME/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --topic movies --partitions 1 --replication-factor 1

echo "🎬 Kafka operativo"

# ======================================================
# 🎥 PRODUCTOR (INICIAR PRIMERO Y ESPERAR)
# ======================================================
echo "🎥 Ejecutando productor Kafka en BACKGROUND..."
python3 /app/scripts/movies_producer_kafka.py &

echo "🕒 Esperando a que el productor cargue datos..."
sleep 30  # Dar tiempo al producer para cargar datasets

# ======================================================
# 🥉 SPARK BRONZE
# ======================================================
echo "🥉 Iniciando Spark Streaming BRONZE..."
/opt/spark/bin/spark-submit /app/scripts/spark_kafka_to_hdfs.py &

echo "🕒 Esperando a que BRONZE procese datos iniciales..."
sleep 45

# ======================================================
# 💎 SPARK GOLD
# ======================================================
echo "💎 Iniciando Spark Streaming GOLD..."
/opt/spark/bin/spark-submit /app/scripts/spark_streaming_gold.py &

echo "🕒 Esperando a que GOLD se inicialice..."
sleep 20

# ======================================================
# 📊 DASHBOARD
# ======================================================
echo "📊 Iniciando Dashboard..."
python3 /app/scripts/dashboard.py &

# ======================================================
# ✅ ESTADO FINAL
# ======================================================
echo "==========================================="
echo "✅ PIPELINE COMPLETO EN EJECUCIÓN"
echo "HDFS UI:   http://localhost:9870"
echo "YARN UI:   http://localhost:8088"
echo "Spark UI:  http://localhost:4040"
echo "Dashboard: http://localhost:8050"
echo "==========================================="

# Verificar que los datos están fluyendo
echo "🔍 Verificando flujo de datos..."
sleep 10

# Verificar datos en Kafka
echo "📊 Verificando datos en Kafka..."
timeout 10s $KAFKA_HOME/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic movies --max-messages 3 --timeout-ms 5000 || echo "⚠️ Esperando datos en Kafka..."

# Verificar datos en HDFS
echo "📁 Verificando datos en HDFS..."
hdfs dfs -ls /user/movies/bronze/movies || echo "⚠️ Esperando datos en HDFS..."

tail -f /dev/null