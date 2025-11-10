#!/bin/bash
# ===================================================================
# Script de Verificación Completa - Fase 9
# ===================================================================

echo "=========================================="
echo "  VERIFICACIÓN COMPLETA SISTEMA FASE 9"
echo "=========================================="
echo ""

# 1. Verificar servicios Docker
echo "=== 1. Servicios Docker ==="
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(recs-api|recs-dashboard|spark|kafka)" || echo "⚠️  Algunos servicios no están corriendo"
echo ""

# 2. Verificar API
echo "=== 2. API Endpoints ===" 
echo -n "Health: "
curl -s http://localhost:8000/metrics/health | jq -r '.status' 2>/dev/null || echo "ERROR"
echo -n "Summary: "
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/metrics/summary)
if [ "$STATUS" == "200" ]; then
    echo "✓ OK (datos disponibles)"
elif [ "$STATUS" == "404" ]; then
    echo "⏳ 404 (esperando datos del procesador)"
else
    echo "✗ ERROR (código: $STATUS)"
fi
echo ""

# 3. Verificar Kafka topics
echo "=== 3. Kafka Topics ==="
echo -n "Topic 'ratings': "
RATINGS_COUNT=$(docker exec kafka kafka-run-class kafka.tools.GetOffsetShell --broker-list localhost:9092 --topic ratings 2>/dev/null | awk -F: '{sum += $NF} END {print sum}')
echo "$RATINGS_COUNT mensajes"

echo -n "Topic 'metrics': "
METRICS_COUNT=$(docker exec kafka kafka-run-class kafka.tools.GetOffsetShell --broker-list localhost:9092 --topic metrics 2>/dev/null | awk -F: '{sum += $NF} END {print sum}')
if [ "$METRICS_COUNT" -gt 0 ]; then
    echo "✓ $METRICS_COUNT mensajes"
else
    echo "⏳ Sin mensajes (procesador debe estar activo)"
fi
echo ""

# 4. Verificar Spark
echo "=== 4. Spark Cluster ==="
WORKERS=$(curl -s http://localhost:8080/json/ 2>/dev/null | jq -r '.workers | length')
echo "Workers registrados: $WORKERS"

ACTIVE_APPS=$(curl -s http://localhost:8080/json/ 2>/dev/null | jq -r '.activeapps | length')
echo "Aplicaciones activas: $ACTIVE_APPS"

if [ "$ACTIVE_APPS" -gt 0 ]; then
    echo "Aplicaciones:"
    curl -s http://localhost:8080/json/ 2>/dev/null | jq -r '.activeapps[] | "  - \(.name) (\(.state))"'
fi
echo ""

# 5. Verificar procesadores
echo "=== 5. Procesadores Activos ==="
PROCS=$(docker exec spark-master sh -c "ps aux | grep '[p]ython.*ratings_stream_processor' | wc -l")
if [ "$PROCS" -gt 0 ]; then
    echo "✓ $PROCS procesador(es) de streaming activo(s)"
else
    echo "⚠️  No hay procesadores activos"
    echo "   Ejecuta: ./scripts/run-streaming-processor.sh"
fi
echo ""

# 6. Dashboard
echo "=== 6. Dashboard ==="
DASH_STATUS=$(docker inspect recs-dashboard --format='{{.State.Health.Status}}' 2>/dev/null)
echo "Estado: $DASH_STATUS"
echo "URL: http://localhost:8501"
echo ""

# 7. Resumen
echo "=========================================="
echo "  RESUMEN"
echo "=========================================="

if [ "$ACTIVE_APPS" -gt 0 ] && [ "$METRICS_COUNT" -gt 0 ]; then
    echo "✅ Sistema funcionando correctamente"
    echo ""
    echo "Accede al dashboard: http://localhost:8501"
elif [ "$ACTIVE_APPS" -gt 0 ]; then
    echo "⏳ Procesador activo, esperando primera ventana de métricas"
    echo ""
    echo "Las métricas se generan cada 1-5 minutos."
    echo "Espera unos momentos y recarga el dashboard."
elif [ "$PROCS" -eq 0 ]; then
    echo "⚠️  Procesador de streaming no está corriendo"
    echo ""
    echo "Ejecuta:"
    echo "  ./scripts/run-streaming-processor.sh"
else
    echo "⚠️  Sistema en inicialización"
    echo ""
    echo "Espera 1-2 minutos y vuelve a ejecutar esta verificación."
fi

echo ""
