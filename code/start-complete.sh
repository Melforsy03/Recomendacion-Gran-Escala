#!/bin/bash

echo "🚀 INICIANDO SISTEMA BIG DATA COMPLETO (HDFS + YARN + Spark + Kafka)"

# Limpiar
docker compose down

# Crear directorios necesarios
mkdir -p hadoop-data
mkdir -p spark-config
cp movies.json hadoop-data/ 2>/dev/null || echo "⚠️ movies.json ya copiado"

# Construir imágenes
echo "🔨 Construyendo imágenes..."
docker compose build

# Iniciar infraestructura base
echo "🐘 Iniciando Zookeeper..."
docker compose up -d zookeeper
sleep 20

echo "📢 Iniciando Kafka..."
docker compose up -d kafka
sleep 20

echo "🗄️  Iniciando HDFS..."
docker compose up -d hadoop-namenode hadoop-datanode
sleep 30

echo "🔄 Iniciando YARN..."
docker compose up -d hadoop-resourcemanager hadoop-nodemanager
sleep 30

# Inicializar Hadoop
chmod +x init-hadoop-yarn.sh
./init-hadoop-yarn.sh

echo "⚡ Iniciando Spark..."
docker compose up -d spark-master spark-worker spark-history-server
sleep 25

echo "🔴 Iniciando aplicaciones..."
docker compose up -d redis dashboard producer consumer batch-processor mapreduce-processor
sleep 20

echo "📊 Estado final del sistema:"
docker compose ps

echo ""
echo "🎉 SISTEMA BIG DATA COMPLETO INICIADO!"
echo ""
echo "🌐 URLs IMPORTANTES:"
echo "   📊 Dashboard: http://localhost:8050"
echo "   🗄️  HDFS: http://localhost:9870"
echo "   🔄 YARN: http://localhost:8088"
echo "   ⚡ Spark: http://localhost:8080"
echo "   📜 Spark History: http://localhost:18080"
echo ""
echo "🔧 COMANDOS ÚTILES:"
echo "   Ejecutar MapReduce: docker compose exec mapreduce-processor python mapreduce_processor.py"
echo "   Ver YARN: docker compose exec resourcemanager yarn application -list"
echo "   Ver HDFS: docker compose exec hadoop-namenode hdfs dfs -ls /results/"
echo "   Parar todo: docker compose down"