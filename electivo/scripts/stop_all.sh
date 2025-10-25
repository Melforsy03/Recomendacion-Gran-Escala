#!/bin/bash
echo "🛑 Deteniendo todos los servicios..."

# Detener Kafka + Zookeeper en host
pkill -f kafka.Kafka
pkill -f zookeeper

# Detener procesos Spark y Kafka producer dentro del contenedor
docker exec -it movies-project pkill -f spark_kafka_to_hdfs.py || true
docker exec -it movies-project pkill -f movies_producer_kafka.py || true

# Detener HDFS y YARN dentro del contenedor
docker exec -it movies-project bash -c "/opt/hadoop/sbin/stop-yarn.sh && /opt/hadoop/sbin/stop-dfs.sh" || true

# Limpiar logs temporales
rm -rf /tmp/kafka-logs /tmp/zookeeper

echo "✅ Todo detenido correctamente."
