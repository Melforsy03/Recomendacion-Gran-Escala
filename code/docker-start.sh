#!/bin/bash

echo "🔧 Solucionando problemas de dependencias..."

# Parar todo
docker-compose down

# Limpiar imágenes viejas
docker rmi code_producer code_consumer code_dashboard 2>/dev/null || true

# Reconstruir con nuevas dependencias
echo "🔨 Reconstruyendo con dependencias compatibles..."
docker-compose build --no-cache

# Iniciar solo servicios base primero
echo "🚀 Iniciando servicios base..."
docker-compose up -d redis

# Esperar un poco
sleep 5

# Iniciar dashboard
echo "🚀 Iniciando dashboard..."
docker-compose up -d dashboard

echo "✅ Proceso completado!"
echo "📊 Verifica el dashboard: http://localhost:8050"
echo "📝 Ver logs: docker-compose logs -f dashboard"