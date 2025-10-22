#!/bin/bash

echo "=========================================="
echo "Deteniendo Sistema de Big Data"
echo "=========================================="
echo ""

read -p "¿Deseas eliminar también los volúmenes de datos? (s/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo "Deteniendo servicios y eliminando volúmenes..."
    docker-compose down -v
    echo ""
    echo "✓ Sistema detenido y datos eliminados"
else
    echo "Deteniendo servicios (manteniendo datos)..."
    docker-compose down
    echo ""
    echo "✓ Sistema detenido (datos preservados)"
fi

echo ""
echo "Para volver a iniciar el sistema, ejecuta:"
echo "  ./start-system.sh"
echo ""
