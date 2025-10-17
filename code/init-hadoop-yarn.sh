#!/bin/bash

echo "🚀 Inicializando Hadoop HDFS + YARN..."

# Esperar a que los servicios estén listos
echo "⏳ Esperando a HDFS y YARN..."
sleep 45

# Crear directorios en HDFS
echo "📁 Creando estructura de directorios HDFS..."
docker compose exec hadoop-namenode hdfs dfs -mkdir -p /data
docker compose exec hadoop-namenode hdfs dfs -mkdir -p /results
docker compose exec hadoop-namenode hdfs dfs -mkdir -p /results/mapreduce
docker compose exec hadoop-namenode hdfs dfs -mkdir -p /spark-logs
docker compose exec hadoop-namenode hdfs dfs -mkdir -p /tmp
docker compose exec hadoop-namenode hdfs dfs -mkdir -p /user
docker compose exec hadoop-namenode hdfs dfs -mkdir -p /user/root

# Subir datos iniciales a HDFS
echo "📤 Subiendo datos a HDFS..."
docker compose exec hadoop-namenode hdfs dfs -put /data/movies.json /data/ 2>/dev/null || echo "⚠️ movies.json ya existe"

# Configurar permisos
docker compose exec hadoop-namenode hdfs dfs -chmod -R 755 /data
docker compose exec hadoop-namenode hdfs dfs -chmod -R 755 /results

# Verificar HDFS
echo "🔍 Verificando HDFS..."
docker compose exec hadoop-namenode hdfs dfs -ls -R /

# Verificar YARN
echo "🔍 Verificando YARN..."
docker compose exec resourcemanager yarn node -list

echo "✅ Hadoop HDFS + YARN inicializado correctamente"
echo ""
echo "🌐 URLs DEL SISTEMA:"
echo "   🗄️  HDFS Web UI: http://localhost:9870"
echo "   🔄 YARN Web UI: http://localhost:8088"
echo "   ⚡ Spark Master: http://localhost:8080"
echo "   📊 Dashboard: http://localhost:8050"
echo ""
echo "🚀 Comandos útiles:"
echo "   Ver nodos YARN: docker compose exec resourcemanager yarn node -list"
echo "   Ver aplicaciones: docker compose exec resourcemanager yarn application -list"
echo "   Ejecutar MapReduce: docker compose exec mapreduce-processor python mapreduce_processor.py"