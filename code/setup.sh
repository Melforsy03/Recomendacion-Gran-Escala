#!/bin/bash
# setup.sh

echo "🚀 Iniciando configuración paso a paso..."

# 1. Limpiar
echo "🧹 Limpiando ambiente..."
docker-compose down
docker system prune -f

# 2. Iniciar solo servicios base
echo "📦 Iniciando servicios base (Zookeeper + Kafka + Redis)..."
docker-compose up -d zookeeper redis

# Esperar a Zookeeper
echo "⏳ Esperando a Zookeeper..."
sleep 15

# Iniciar Kafka
docker-compose up -d kafka

# Esperar a Kafka
echo "⏳ Esperando a Kafka..."
sleep 30

# 3. Verificar Kafka
echo "🔍 Verificando Kafka..."
for i in {1..5}; do
    if docker-compose exec kafka kafka-topics --list --bootstrap-server kafka:9092 2>/dev/null; then
        echo "✅ Kafka está funcionando"
        break
    else
        echo "⏳ Kafka aún no está listo, reintento $i/5..."
        sleep 10
    fi
done

# 4. Crear topic
echo "📝 Creando topic..."
docker-compose exec kafka kafka-topics --create \
    --topic movie-interactions \
    --bootstrap-server kafka:9092 \
    --partitions 1 \
    --replication-factor 1 \
    --if-not-exists

# 5. Iniciar Spark
echo "⚡ Iniciando Spark..."
docker-compose up -d spark-master spark-worker

# 6. Iniciar aplicación
echo "🎬 Iniciando aplicación..."
docker-compose up -d dashboard

# 7. Verificar estado
echo "📊 Estado de servicios:"
docker-compose ps

echo ""
echo "✅ Configuración completada!"
echo ""
echo "🌐 URLs:"
echo "   - Dashboard: http://localhost:8050"
echo "   - Spark: http://localhost:8080"
echo ""
echo "🚀 Comandos:"
echo "   - Generar datos: docker-compose up producer"
echo "   - Ver métricas: docker-compose up consumer"
echo "   - Logs: docker-compose logs -f [servicio]"