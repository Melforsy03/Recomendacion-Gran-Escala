#!/usr/bin/env bash
set -e

export SPARK_HOME=/opt/spark
export HADOOP_HOME=/opt/hadoop
export HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
export PATH=$SPARK_HOME/bin:$HADOOP_HOME/bin:$PATH

echo "▶️  Producer → escribe raw en HDFS"
spark-submit --master yarn --deploy-mode client movies_producer.py

echo "▶️  Processor → lee raw y guarda processed en HDFS"
spark-submit --master yarn --deploy-mode client movies_processor.py

echo "📄 Comprobando en HDFS..."
hdfs dfs -ls -R /user/movies