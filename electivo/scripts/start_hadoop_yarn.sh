#!/usr/bin/env bash
set -e

echo "🐳 INICIANDO SERVICIOS HADOOP EN DOCKER..."

# Configurar entorno
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export HADOOP_HOME=/opt/hadoop
export SPARK_HOME=/opt/spark
export HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
export PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$SPARK_HOME/bin:$PATH

# Configurar Spark para SILENCIO TOTAL
export SPARK_LOCAL_IP=127.0.0.1
export SPARK_SUBMIT_OPTS="-Dlog4j.configuration=file:/app/config/log4j2.properties"

echo "🔇 MODO SILENCIOSO: Solo se mostrarán los resultados"

# Iniciar servicios SILENCIOSAMENTE
echo "▶️  Iniciando HDFS..."
hdfs --daemon start namenode > /dev/null 2>&1
sleep 8
hdfs --daemon start datanode > /dev/null 2>&1
sleep 8

echo "▶️  Iniciando YARN..."
yarn --daemon start resourcemanager > /dev/null 2>&1
sleep 5
yarn --daemon start nodemanager > /dev/null 2>&1
sleep 5

# Esperar servicios
echo "⏳ Esperando servicios..."
until hdfs dfsadmin -report 2>/dev/null | grep -q "Live datanodes" && \
      yarn node -list 2>/dev/null | grep -q "Total Nodes"; do
    sleep 5
done

echo "✅ Servicios listos"

# Crear estructura HDFS
hdfs dfs -mkdir -p /user/movies/raw > /dev/null 2>&1
hdfs dfs -mkdir -p /user/movies/processed > /dev/null 2>&1

# Pipeline COMPLETAMENTE SILENCIOSO
echo ""
echo "🚀 EJECUTANDO PIPELINE COMPLETO..."
echo ""

# 1. Producer - SILENCIO TOTAL
echo "📤 EJECUTANDO PRODUCER..."
spark-submit --master yarn --deploy-mode client \
    --conf spark.executor.memory=512m \
    --conf spark.driver.memory=512m \
    --conf spark.ui.enabled=false \
    --conf spark.driver.bindAddress=127.0.0.1 \
    --conf spark.driver.host=127.0.0.1 \
    --conf spark.sql.adaptive.enabled=true \
    --files /app/config/log4j2.properties \
    --conf "spark.driver.extraJavaOptions=-Dlog4j.configuration=log4j2.properties" \
    --conf "spark.executor.extraJavaOptions=-Dlog4j.configuration=log4j2.properties" \
    /app/movies_producer.py 2>/dev/null

# 2. Processor - SILENCIO TOTAL  
echo "🔄 EJECUTANDO PROCESSOR..."
spark-submit --master yarn --deploy-mode client \
    --conf spark.executor.memory=512m \
    --conf spark.ui.enabled=false \
    --conf spark.driver.bindAddress=127.0.0.1 \
    --conf spark.driver.host=127.0.0.1 \
    --conf spark.sql.adaptive.enabled=true \
    --files /app/config/log4j2.properties \
    --conf "spark.driver.extraJavaOptions=-Dlog4j.configuration=log4j2.properties" \
    --conf "spark.executor.extraJavaOptions=-Dlog4j.configuration=log4j2.properties" \
    /app/movies_processor.py 2>/dev/null

# 3. Analysis - SILENCIO TOTAL
echo "📊 EJECUTANDO ANÁLISIS..."
spark-submit --master local[*] \
    --conf spark.executor.memory=512m \
    --conf spark.ui.enabled=false \
    --conf spark.driver.bindAddress=127.0.0.1 \
    --conf spark.driver.host=127.0.0.1 \
    --files /app/config/log4j2.properties \
    --conf "spark.driver.extraJavaOptions=-Dlog4j.configuration=log4j2.properties" \
    /app/movie_analysis.py 2>/dev/null

# Mostrar resumen final
echo ""
echo "🎉 PROYECTO COMPLETADO EN DOCKER!"
echo ""
echo "📍 URLs de monitoreo:"
echo "   HDFS Web UI: http://localhost:9870"
echo "   YARN Web UI: http://localhost:8088"

tail -f /dev/null