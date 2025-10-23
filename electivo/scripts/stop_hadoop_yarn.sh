#!/usr/bin/env bash
set -e
export HADOOP_HOME=/opt/hadoop
export PATH=$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH

echo "⏹️  Parando YARN..."
yarn --daemon stop nodemanager || true
yarn --daemon stop resourcemanager || true

echo "⏹️  Parando HDFS..."
hdfs --daemon stop datanode || true
hdfs --daemon stop namenode || true

echo "✅ Todo detenido."