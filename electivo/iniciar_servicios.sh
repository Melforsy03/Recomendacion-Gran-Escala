#!/bin/bash

echo "🔧 INICIANDO SERVICIOS HADOOP..."

# Iniciar HDFS
echo "1. Iniciando HDFS..."
start-dfs.sh

# Iniciar YARN
echo "2. Iniciando YARN..."
start-yarn.sh

# Esperar un poco
sleep 3

# Verificar servicios
echo "3. Verificando servicios..."
jps

echo "✅ Servicios iniciados correctamente"

# Crear directorios en HDFS si no existen
echo "4. Creando directorios en HDFS..."
hdfs dfs -mkdir -p /user/movies/raw
hdfs dfs -mkdir -p /user/movies/processed

echo "📁 Estructura HDFS creada:"
hdfs dfs -ls -R /user/movies