#!/bin/bash

echo "🎬 INICIANDO PROYECTO MOVIES EN DOCKER..."
echo "=========================================="

# Configurar entorno
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export HADOOP_HOME=/opt/hadoop
export SPARK_HOME=/opt/spark
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
export PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$SPARK_HOME/bin:$PATH

echo "✅ JAVA_HOME: $JAVA_HOME"
echo "✅ HADOOP_HOME: $HADOOP_HOME"

# SOLUCIÓN: Formatear e iniciar en primer plano
echo "0. 🔧 INICIALIZANDO HADOOP..."
ln -sf /usr/lib/jvm/java-11-openjdk-amd64 /usr/lib/jvm/java-8-openjdk-amd64 2>/dev/null || true

echo "📝 FORMATEANDO NAMENODE..."
hdfs namenode -format -force -nonInteractive
echo "✅ NameNode formateado"

# Iniciar servicios Hadoop EN PRIMER PLANO
echo "1. 🚀 INICIANDO HADOOP Y YARN..."
/app/scripts/start_hadoop_yarn.sh
