#!/bin/bash
###############################################################################
# FASE 9 - Comandos Rápidos
# Sistema de Recomendación de Películas a Gran Escala
###############################################################################

cat << 'EOF'
╔═══════════════════════════════════════════════════════════════════════════╗
║                    FASE 9 - COMANDOS RÁPIDOS                              ║
║              Analytics Batch + API + Dashboard                            ║
╚═══════════════════════════════════════════════════════════════════════════╝

📋 SERVICIOS
════════════════════════════════════════════════════════════════════════════

1️⃣  Ver estado de servicios:
   docker compose ps

2️⃣  Ver logs:
   docker compose logs -f api
   docker compose logs -f dashboard
   docker logs spark-master --tail 50

3️⃣  Reiniciar servicios:
   docker compose restart api
   docker compose restart dashboard

════════════════════════════════════════════════════════════════════════════
📊 GENERAR Y PROCESAR DATOS
════════════════════════════════════════════════════════════════════════════

1️⃣  Generar ratings sintéticos (100/seg):
   ./scripts/run-latent-generator.sh 100

2️⃣  Procesar streaming (en otra terminal):
   ./scripts/run-streaming-processor.sh

3️⃣  Ejecutar analytics batch:
   ./scripts/run-batch-analytics.sh

4️⃣  Verificar todo:
   ./scripts/verify_fase9.sh

════════════════════════════════════════════════════════════════════════════
🌐 ACCESOS WEB
════════════════════════════════════════════════════════════════════════════

Dashboard:       http://localhost:8501
API REST:        http://localhost:8000/docs
API Health:      http://localhost:8000/metrics/health
Spark UI:        http://localhost:8080
HDFS UI:         http://localhost:9870
YARN UI:         http://localhost:8088

════════════════════════════════════════════════════════════════════════════
🔍 CONSULTAS RÁPIDAS
════════════════════════════════════════════════════════════════════════════

📁 Ver outputs analytics en HDFS:
   docker exec namenode hadoop fs -ls -R /outputs/analytics

📊 Ver distribución global:
   docker exec namenode hadoop fs -ls /outputs/analytics/distributions/global

🎬 Ver películas trending:
   docker exec namenode hadoop fs -ls /outputs/analytics/trending/trending_movies

📈 Ver datos de streaming:
   docker exec namenode hadoop fs -ls /streams/ratings/raw
   docker exec namenode hadoop fs -ls /streams/ratings/agg

════════════════════════════════════════════════════════════════════════════
🔌 PROBAR API
════════════════════════════════════════════════════════════════════════════

✅ Health check:
   curl http://localhost:8000/metrics/health | jq

📊 Resumen de métricas:
   curl http://localhost:8000/metrics/summary | jq

🏆 Top-10 películas:
   curl "http://localhost:8000/metrics/topn?limit=10" | jq '.movies[] | {title, score}'

🎭 Métricas por género:
   curl http://localhost:8000/metrics/genres | jq '.genres | keys'

📈 Historial:
   curl "http://localhost:8000/metrics/history?limit=10" | jq '.count'

📡 SSE Stream (Ctrl+C para salir):
   curl -N http://localhost:8000/metrics/stream

════════════════════════════════════════════════════════════════════════════
🐛 TROUBLESHOOTING
════════════════════════════════════════════════════════════════════════════

❌ API no responde:
   docker compose logs -f api
   docker compose restart api

❌ Dashboard sin datos:
   # Verificar que el procesador streaming esté corriendo
   docker logs spark-master | grep processor
   
   # Verificar topic metrics
   docker exec kafka kafka-console-consumer \
       --bootstrap-server localhost:9092 \
       --topic metrics \
       --from-beginning \
       --max-messages 5

❌ Analytics batch falla:
   # Verificar que existan datos
   docker exec namenode hadoop fs -ls /streams/ratings/raw
   
   # Ver logs de Spark
   docker logs spark-master --tail 100

════════════════════════════════════════════════════════════════════════════
🚀 FLUJO COMPLETO DE PRUEBA
════════════════════════════════════════════════════════════════════════════

# Terminal 1: Generar ratings (dejar corriendo 2-3 minutos)
./scripts/run-latent-generator.sh 100

# Terminal 2: Procesar streaming (dejar corriendo)
./scripts/run-streaming-processor.sh

# Terminal 3: Después de 2-3 minutos, ejecutar analytics
./scripts/run-batch-analytics.sh

# Abrir dashboard en navegador
xdg-open http://localhost:8501  # Linux
# open http://localhost:8501      # macOS

# Verificar todo
./scripts/verify_fase9.sh

════════════════════════════════════════════════════════════════════════════
📚 DOCUMENTACIÓN
════════════════════════════════════════════════════════════════════════════

Resumen Completo:    docs/FASE9_RESUMEN.md
Guía Rápida:         docs/FASE9_INICIO_RAPIDO.md
Completitud:         FASE9_COMPLETADA.md

════════════════════════════════════════════════════════════════════════════

✨ FASE 9 - COMPLETADA Y OPERACIONAL ✨

EOF
