#!/bin/bash
echo "🔍 Estado de los contenedores:"
docker-compose ps
echo ""
echo "📊 Estadísticas de recursos:"
docker stats --no-stream
