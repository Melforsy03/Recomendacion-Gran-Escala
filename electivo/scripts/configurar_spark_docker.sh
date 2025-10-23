# scripts/configurar_spark_docker.sh
#!/bin/bash

echo "🔧 CONFIGURANDO VARIABLES DE SPARK PARA DOCKER..."

export SPARK_HOME="/opt/spark"
export HADOOP_HOME="/opt/hadoop"
export JAVA_HOME="/usr/lib/jvm/java-11-openjdk-amd64"
export HADOOP_CONF_DIR="$HADOOP_HOME/etc/hadoop"
export PATH="$SPARK_HOME/bin:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$PATH"
export PYSPARK_PYTHON=python3
export PYSPARK_DRIVER_PYTHON=python3

echo "✅ Variables configuradas para Docker:"
echo "   SPARK_HOME: $SPARK_HOME"
echo "   HADOOP_HOME: $HADOOP_HOME"
echo "   JAVA_HOME: $JAVA_HOME"