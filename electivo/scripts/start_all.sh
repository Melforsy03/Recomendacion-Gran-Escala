#!/bin/bash
# =====================================================
# 🎬 START FINAL - Con JAVA_HOME corregido
# =====================================================

set -e

echo "=========================================="
echo "🚀 INICIANDO PIPELINE - JAVA_HOME CORREGIDO"
echo "=========================================="

# ======== CONFIGURACIÓN CORRECTA DE JAVA ========
# 🔥 CORREGIR JAVA_HOME - Buscar la ruta correcta
export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which java))))
echo "✅ JAVA_HOME configurado: $JAVA_HOME"

export HADOOP_HOME=/opt/hadoop
export SPARK_HOME=/opt/spark
export PATH=$JAVA_HOME/bin:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$SPARK_HOME/bin:$PATH

# Configurar Hadoop para usar el Java correcto
echo "export JAVA_HOME=$JAVA_HOME" > $HADOOP_HOME/etc/hadoop/hadoop-env.sh

# ======== 1️⃣ Iniciar HDFS manualmente ========
echo "💾 Iniciando HDFS manualmente..."

# Crear directorios de datos
mkdir -p /opt/hadoop_data/nn /opt/hadoop_data/dn

# Formatear NameNode si es necesario
echo "📋 Formateando NameNode..."
hdfs namenode -format -force

# Iniciar servicios Hadoop manualmente
echo "🚀 Iniciando servicios Hadoop manualmente..."
hdfs --daemon start namenode
sleep 3
hdfs --daemon start datanode  
sleep 3
hdfs --daemon start secondarynamenode
sleep 3
yarn --daemon start resourcemanager
sleep 3
yarn --daemon start nodemanager
sleep 5

# Esperar a HDFS
echo "🕒 Esperando HDFS..."
for i in {1..20}; do
    if hdfs dfsadmin -report 2>/dev/null | grep -q "Live datanodes"; then
        echo "✅ HDFS listo"
        break
    fi
    echo "⏳ Intento $i/20..."
    sleep 2
done

# Crear directorios en HDFS
echo "📁 Creando directorios HDFS..."
hdfs dfs -mkdir -p /user/movies/bronze 2>/dev/null || true
hdfs dfs -mkdir -p /user/movies/checkpoints 2>/dev/null || true

# ======== 2️⃣ Iniciar Kafka ========
echo "🔧 Iniciando Kafka..."
/app/scripts/start_kafka_local.sh
sleep 10

# ======== 3️⃣ Verificar servicios ========
echo "🔍 Verificando servicios..."
echo "--- Java Version ---"
java -version
echo "--- Procesos Java ---"
jps
echo "--- HDFS ---"
hdfs dfsadmin -report 2>/dev/null | head -3 || echo "HDFS iniciando..."

# ======== 4️⃣ Iniciar Spark Streaming ========
echo "💎 Iniciando Spark Streaming..."
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 /app/scripts/spark_kafka_to_hdfs.py &
SPARK_PID=$!
echo "Spark PID: $SPARK_PID"
sleep 20

# ======== 5️⃣ Ejecutar Productor ========
echo "🎥 Ejecutando productor Kafka..."
python3 /app/scripts/movies_producer_kafka.py &
PRODUCER_PID=$!
echo "Producer PID: $PRODUCER_PID"
sleep 5

echo "=========================================="
echo "✅ PIPELINE INICIADO"
echo "HDFS: http://localhost:9870"
echo "YARN: http://localhost:8088" 
echo "Spark: http://localhost:4040"
echo "=========================================="

# ======== 6️⃣ Mantener contenedor vivo ========
cleanup() {
    echo "🛑 Deteniendo servicios..."
    kill $SPARK_PID $PRODUCER_PID 2>/dev/null || true
    /opt/kafka_2.13-2.8.1/bin/kafka-server-stop.sh 2>/dev/null || true
    /opt/kafka_2.13-2.8.1/bin/zookeeper-server-stop.sh 2>/dev/null || true
    
    # Detener Hadoop manualmente
    yarn --daemon stop nodemanager 2>/dev/null || true
    yarn --daemon stop resourcemanager 2>/dev/null || true
    hdfs --daemon stop secondarynamenode 2>/dev/null || true
    hdfs --daemon stop datanode 2>/dev/null || true
    hdfs --daemon stop namenode 2>/dev/null || true
    
    exit 0
}

trap cleanup SIGINT SIGTERM

# Monitoreo
echo "📊 Iniciando monitoreo..."
while true; do
    echo "--- Estado $(date) ---"
    echo "HDFS: $(hdfs dfsadmin -report 2>/dev/null | grep 'Live datanodes' | head -1 || echo 'Verificando...')"
    echo "Kafka: $(netstat -tln | grep -q ':9092' && echo '✅ Activo' || echo '❌ Inactivo')"
    echo "Spark: $(kill -0 $SPARK_PID 2>/dev/null && echo '✅ Activo' || echo '❌ Detenido')"
    
    sleep 30
done