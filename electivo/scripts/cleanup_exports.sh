#!/bin/bash
# cleanup_exports.sh

echo "🧹 Limpiando carpeta exports..."

# Eliminar carpeta exports
docker exec --user root movies-project rm -rf /app/exports

# Crear nueva carpeta con permisos correctos
docker exec --user root movies-project mkdir -p /app/exports
docker exec --user root movies-project chmod 777 /app/exports

echo "✅ Carpeta /app/exports limpiada y recreada"