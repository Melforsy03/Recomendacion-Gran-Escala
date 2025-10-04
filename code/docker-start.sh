#!/bin/bash

echo "🐳 Construyendo y iniciando el sistema con Docker Compose..."
echo "📦 Esto puede tomar unos minutos la primera vez..."

# Construir las imágenes
docker-compose build

# Iniciar los servicios
docker-compose up -d

echo "✅ Servicios iniciados:"
echo "   📊 Dashboard: http://localhost:8050"
echo "   📡 Kafka: localhost:9092"
echo "   🐘 Zookeeper: localhost:2181"
echo "   🔴 Redis: localhost:6379"

echo ""
echo "📋 Para ver logs: docker-compose logs -f"
echo "🛑 Para detener: docker-compose down"
echo "🔍 Para ver estado: docker-compose ps"
