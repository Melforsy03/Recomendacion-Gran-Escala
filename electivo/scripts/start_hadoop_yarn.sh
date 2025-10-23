#!/usr/bin/env bash
set -e

echo "🐳 INICIANDO SERVICIOS HADOOP EN DOCKER..."

# Configurar entorno
ln -sf /usr/lib/jvm/java-11-openjdk-amd64 /usr/lib/jvm/java-8-openjdk-amd64 2>/dev/null || true

export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export HADOOP_HOME=/opt/hadoop
export HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
export PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH

# SOLUCIÓN: No matar procesos, solo verificar
echo "🔍 Verificando procesos existentes..."
jps

# Iniciar HDFS
echo "▶️  Iniciando HDFS..."
hdfs --daemon start namenode
echo "   ✅ NameNode iniciado"
sleep 8

hdfs --daemon start datanode
echo "   ✅ DataNode iniciado"
sleep 8

# Iniciar YARN
echo "▶️  Iniciando YARN..."
yarn --daemon start resourcemanager
echo "   ✅ ResourceManager iniciado"
sleep 5

yarn --daemon start nodemanager
echo "   ✅ NodeManager iniciado"
sleep 5

# Verificar servicios
echo "📊 ESTADO DE SERVICIOS:"
jps

# Esperar a que los servicios estén completamente listos
echo "⏳ ESPERANDO INICIALIZACIÓN COMPLETA..."
for i in {1..20}; do
    if hdfs dfsadmin -report 2>/dev/null | grep -q "Live datanodes" && \
       yarn node -list 2>/dev/null | grep -q "Total Nodes"; then
        echo "✅ TODOS LOS SERVICIOS LISTOS!"
        break
    fi
    echo "   Esperando servicios... ($i/20)"
    sleep 5
done

# Mostrar información final
echo ""
echo "🎉 HADOOP Y YARN INICIADOS CORRECTAMENTE"
echo "📍 HDFS UI: http://localhost:9870"
echo "📍 YARN UI: http://localhost:8088"
echo "📍 DataNode: http://localhost:9864"
echo ""
echo "📊 ESTADO FINAL:"
jps
echo ""
hdfs dfsadmin -report
echo ""
yarn node -list

# EJECUTAR EL RESTO DEL PROYECTO DESDE AQUÍ
echo ""
echo "🚀 EJECUTANDO PIPELINE DEL PROYECTO..."
echo ""

# Crear estructura HDFS
echo "📁 CREANDO ESTRUCTURA HDFS..."
hdfs dfs -mkdir -p /user/movies/raw 2>/dev/null || true
hdfs dfs -mkdir -p /user/movies/processed 2>/dev/null || true
hdfs dfs -chmod -R 777 /user/movies 2>/dev/null || true

echo "✅ Estructura HDFS creada"


# Ejecutar el pipeline completo
echo "🎯 EJECUTANDO PROYECTO COMPLETO..."
cd /app

# Producer
echo "📤 EJECUTANDO PRODUCER..."
spark-submit --master yarn --deploy-mode client \
    --conf spark.executor.memory=512m \
    --conf spark.driver.memory=512m \
    movies_producer.py

# Processor
echo "🔄 EJECUTANDO PROCESSOR..."
spark-submit --master yarn --deploy-mode client \
    --conf spark.executor.memory=512m \
    movies_processor.py

# Analysis
echo "📊 EJECUTANDO ANÁLISIS..."
if [ -f "/app/movie_analysis.py" ]; then
    spark-submit --master yarn --deploy-mode client \
        --conf spark.executor.memory=512m \
        /app/movie_analysis.py
elif [ -f "/app/movie_analysis.py" ]; then
    spark-submit --master yarn --deploy-mode client \
        --conf spark.executor.memory=512m \
        /app/movie_analysis.py
else
    echo "❌ ERROR: No se encuentra movie_analysis.py"
    exit 1
fi

echo ""
echo "🎉 PROYECTO COMPLETADO EN DOCKER!"
echo ""
echo "📍 URLs de monitoreo:"
echo "   HDFS Web UI: http://localhost:9870"
echo "   YARN Web UI: http://localhost:8088"
echo ""
echo "📊 Archivos en HDFS:"
hdfs dfs -ls -R /user/movies

# Mantener el contenedor activo
echo ""
echo "🐳 Contenedor activo. Presiona Ctrl+C para detener."
tail -f /dev/null