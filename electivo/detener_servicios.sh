#!/bin/bash

echo "🛑 DETENIENDO SERVICIOS HADOOP..."

# Detener YARN
stop-yarn.sh

# Detener HDFS
stop-dfs.sh

echo "✅ Servicios detenidos"