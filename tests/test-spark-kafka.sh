#!/bin/bash

echo "=========================================="
echo "Test de Integración Spark + Kafka"
echo "=========================================="
echo ""

# Crear un script Python para Spark Streaming con Kafka
cat > /tmp/test_spark_kafka.py << 'EOF'
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

print("Inicializando Spark Session...")
spark = SparkSession.builder \
    .appName("TestSparkKafkaIntegration") \
    .master("spark://spark-master:7077") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

print("Configurando Streaming desde Kafka...")

# Leer desde Kafka
df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "test-streaming") \
    .option("startingOffsets", "latest") \
    .load()

# Transformar los datos
messages = df.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)", "timestamp")

# Escribir a consola
query = messages \
    .writeStream \
    .outputMode("append") \
    .format("console") \
    .option("truncate", False) \
    .trigger(processingTime="5 seconds") \
    .start()

print("Esperando mensajes durante 30 segundos...")
query.awaitTermination(30)
query.stop()

spark.stop()
print("Test completado!")
EOF

echo "1. Limpiando y recreando topic para streaming..."
# Eliminar topic existente
docker exec kafka kafka-topics --delete \
    --bootstrap-server localhost:9092 \
    --topic test-streaming 2>/dev/null || true

sleep 2

# Crear topic limpio
docker exec kafka kafka-topics --create \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 3 \
    --topic test-streaming \
    --if-not-exists

echo ""
echo "2. Pre-descargando dependencias (solo primera vez)..."
# Pre-descargar con timeout aumentado y repositorios alternativos
docker exec -u root -e SPARK_SUBMIT_OPTS="-Dsun.net.client.defaultConnectTimeout=180000 -Dsun.net.client.defaultReadTimeout=900000" spark-master bash -c '
    if [ ! -f /root/.ivy2/.packages_downloaded ]; then
        echo "Descargando paquetes Kafka para Spark..."
        spark-submit \
            --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1 \
            --repositories "https://repo.maven.apache.org/maven2,https://repo1.maven.org/maven2,https://maven-central.storage-download.googleapis.com/maven2" \
            --help 2>&1 | head -n 20 || true
        
        # Marcar como descargado
        touch /root/.ivy2/.packages_downloaded
        echo "✓ Paquetes descargados y cacheados"
    else
        echo "✓ Usando paquetes ya descargados"
    fi
'

echo ""
echo "3. Copiando script de prueba al contenedor..."
docker cp /tmp/test_spark_kafka.py spark-master:/tmp/

echo ""
echo "4. Produciendo mensajes de prueba en Kafka (en background)..."
(sleep 5 && for i in {1..5}; do
    echo "mensaje_test_$i:$(date)" | docker exec -i kafka kafka-console-producer \
        --bootstrap-server localhost:9092 \
        --topic test-streaming \
        --property "parse.key=true" \
        --property "key.separator=:"
    sleep 2
done) &

echo ""
echo "5. Ejecutando Spark Streaming con Kafka..."
timeout 1000 docker exec -u root -e SPARK_SUBMIT_OPTS="-Dsun.net.client.defaultConnectTimeout=180000 -Dsun.net.client.defaultReadTimeout=900000" spark-master \
    spark-submit \
    --master spark://spark-master:7077 \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1 \
    --repositories "https://repo.maven.apache.org/maven2,https://repo1.maven.org/maven2,https://maven-central.storage-download.googleapis.com/maven2" \
    /tmp/test_spark_kafka.py || {
    echo "⚠ El test excedió el timeout o falló"
    echo "Esto puede deberse a problemas de red"
    exit 1
}

echo ""
echo "✓ Test de integración Spark + Kafka completado"
echo ""
