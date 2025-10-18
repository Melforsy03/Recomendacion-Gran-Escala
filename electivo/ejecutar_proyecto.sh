#!/bin/bash
echo "🎬 PROYECTO MOVIES CON YARN, SPARK Y HDFS"
echo "=========================================="

# 1. Iniciar servicios
echo ""
echo "1. 🚀 INICIANDO SERVICIOS HADOOP Y YARN..."
./iniciar_servicios.sh
sleep 8

# 2. Activar entorno virtual y configurar Spark
source spark_env/bin/activate
source configurar_spark.sh

# 3. Ejecutar Producer
echo ""
echo "2. 📤 EJECUTANDO PRODUCER CON YARN Y HDFS..."
python3 movies_producer.py

if [ $? -eq 0 ]; then
    echo "✅ Producer con YARN ejecutado correctamente"
else
    echo "❌ Error en Producer YARN"
    ./detener_servicios.sh
    exit 1
fi

# 4. Ejecutar Processor
echo ""
echo "3. 🔄 EJECUTANDO PROCESSOR CON YARN Y HDFS..."
python3 movies_processor.py

if [ $? -eq 0 ]; then
    echo "✅ Processor con YARN ejecutado correctamente"
else
    echo "❌ Error en Processor YARN"
    ./detener_servicios.sh
    exit 1
fi

# 5. Mostrar resultados
echo ""
echo "4. 📊 MOSTRANDO RESULTADOS..."
echo "📍 HDFS Web UI: http://localhost:9870"
echo "📍 YARN Web UI: http://localhost:8088"
echo ""
echo "📁 Archivos en HDFS:"
hdfs dfs -ls -R /user/movies

echo ""
echo "🎉 PROYECTO CON YARN Y HDFS COMPLETADO!"