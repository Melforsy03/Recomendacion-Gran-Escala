#!/usr/bin/env bash
set -e

export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export HADOOP_HOME=/opt/hadoop
export HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
export PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH

echo "▶️  Iniciando HDFS..."
hdfs dfsadmin -safemode leave || true
hdfs --daemon start namenode
hdfs --daemon start datanode

echo "▶️  Iniciando YARN..."
yarn --daemon start resourcemanager
yarn --daemon start nodemanager

echo "✅ HDFS UI:   http://localhost:9870"
echo "✅ YARN UI:   http://localhost:8088"
echo "✅ DataNode:  http://localhost:9864"
echo "✅ NodeMgr:   http://localhost:8042"

# Mantener el contenedor vivo si se ejecuta como CMD
tail -f /dev/null
