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
    .option("startingOffsets", "earliest") \
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

echo "1. Creando topic para streaming..."
docker exec kafka kafka-topics --create \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 3 \
    --topic test-streaming \
    --if-not-exists

echo ""
echo "2. Copiando script de prueba al contenedor..."
docker cp /tmp/test_spark_kafka.py spark-master:/tmp/

echo ""
echo "3. Produciendo mensajes de prueba en Kafka (en background)..."
(sleep 5 && for i in {1..5}; do
    echo "mensaje_test_$i:$(date)" | docker exec -i kafka kafka-console-producer \
        --bootstrap-server localhost:9092 \
        --topic test-streaming \
        --property "parse.key=true" \
        --property "key.separator=:"
    sleep 2
done) &

echo ""
echo "4. Ejecutando Spark Streaming con Kafka..."
docker exec -u root spark-master spark-submit \
    --master spark://spark-master:7077 \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1 \
    /tmp/test_spark_kafka.py

echo ""
echo "✓ Test de integración Spark + Kafka completado"
echo ""
