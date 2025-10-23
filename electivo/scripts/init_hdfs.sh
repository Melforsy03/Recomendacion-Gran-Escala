#!/usr/bin/env bash
set -e

# CORREGIR: Java 11
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export HADOOP_HOME=/opt/hadoop
export HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
export PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH

echo "🧹 Formateando NameNode (solo primera vez)..."
hdfs namenode -format -force -nonInteractive

echo "📂 Creando estructura base en HDFS..."
hdfs --daemon start namenode
hdfs --daemon start datanode
sleep 5

hdfs dfs -mkdir -p /user/movies/raw
hdfs dfs -mkdir -p /user/movies/processed
hdfs dfs -chmod -R 777 /user

echo "✅ Estructura creada:"
hdfs dfs -ls -R /user/movies

hdfs --daemon stop datanode
hdfs --daemon stop namenode