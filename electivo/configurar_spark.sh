#!/bin/bash
echo "🔧 CONFIGURANDO VARIABLES DE SPARK..."

export SPARK_HOME="/home/melani/Escritorio/Big-Data/electivo/spark_env/lib/python3.12/site-packages/pyspark"
export PATH="$SPARK_HOME/bin:$PATH"
export PYSPARK_PYTHON=python3
export PYSPARK_DRIVER_PYTHON=python3
export HADOOP_CONF_DIR="$HADOOP_HOME/etc/hadoop"  # Si tienes Hadoop instalado

echo "✅ Variables configuradas:"
echo "   SPARK_HOME: $SPARK_HOME"
echo "   PYSPARK_PYTHON: $PYSPARK_PYTHON"