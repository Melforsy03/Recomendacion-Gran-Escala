# 🔄 Guía de Despliegue Regular - Ejecuciones Posteriores

**Sistema de Recomendación de Películas en Gran Escala**  
**Versión:** 1.0  
**Última actualización:** Diciembre 2025

---

> 📌 **NOTA:** Esta guía es para **ejecuciones posteriores** del sistema.
> Si es tu primera vez, consulta `GUIA_DESPLIEGUE_INICIAL_UNICO.md`.

---

## 📋 Tabla de Contenidos

1. [Inicio Rápido](#inicio-rápido)
2. [Escenarios de Reinicio](#escenarios-de-reinicio)
3. [Verificación del Sistema](#verificación-del-sistema)
4. [Gestión de Jobs Spark](#gestión-de-jobs-spark)
5. [Detener el Sistema](#detener-el-sistema)
6. [Monitoreo](#monitoreo)
7. [Troubleshooting](#troubleshooting)
8. [Comandos de Referencia Rápida](#comandos-de-referencia-rápida)

---

## Inicio Rápido

### Opción 1: Sistema Completamente Detenido

```bash
# 1. Navegar al proyecto
cd /home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala

# 2. Iniciar infraestructura
./scripts/start-system.sh

# 3. Esperar inicialización (60 segundos)
sleep 60

# 4. Verificar estado
./scripts/check-spark-resources.sh

# 5. Iniciar pipeline de datos
./scripts/run-latent-generator.sh 100 &
sleep 30
./scripts/run-streaming-processor.sh &

# 6. Verificar dashboard
xdg-open http://localhost:8501
```

**Tiempo total:** 2-3 minutos

### Opción 2: Contenedores Ya Corriendo (Reinicio de Jobs)

```bash
# 1. Verificar estado
docker compose ps
./scripts/check-spark-resources.sh

# 2. Detener jobs existentes (si hay)
./scripts/spark-job-manager.sh kill-all

# 3. Reiniciar pipeline
./scripts/run-latent-generator.sh 100 &
sleep 10
./scripts/run-streaming-processor.sh &
```

---

## Escenarios de Reinicio

### Escenario 1: Restart Suave (Solo Jobs Spark)

Si los contenedores están corriendo pero quieres reiniciar los jobs:

```bash
# 1. Detener jobs actuales
docker exec spark-master bash -c "ps aux | grep -E 'latent_generator|ratings_stream_processor' | grep -v grep | awk '{print \$2}' | xargs -r kill"

# 2. Esperar 5 segundos
sleep 5

# 3. Reiniciar generador
./scripts/run-latent-generator.sh 100 &

# 4. Reiniciar processor
./scripts/run-streaming-processor.sh &

# 5. Verificar en dashboard
xdg-open http://localhost:8501
```

### Escenario 2: Restart Completo (Contenedores Detenidos)

Si los contenedores fueron detenidos:

```bash
# 1. Levantar infraestructura
docker compose up -d

# 2. Esperar inicialización
sleep 60

# 3. Verificar fairscheduler (solo si los contenedores fueron recreados)
docker exec spark-master ls /opt/spark/conf/fairscheduler.xml || \
  docker cp fairscheduler.xml spark-master:/opt/spark/conf/

docker exec spark-worker ls /opt/spark/conf/fairscheduler.xml || \
  docker cp fairscheduler.xml spark-worker:/opt/spark/conf/

# 4. Iniciar pipeline
./scripts/run-latent-generator.sh 100 &
sleep 10
./scripts/run-streaming-processor.sh &

# 5. Verificar
curl -s http://localhost:8000/metrics/health | jq
```

### Escenario 3: Reinicio Completo con Datos Limpios

Si quieres empezar desde cero eliminando todos los datos:

```bash
# 1. Detener todo
docker compose down

# 2. Eliminar volúmenes (⚠️ CUIDADO: elimina todos los datos)
docker volume ls | grep recomendacion-gran-escala | awk '{print $2}' | xargs docker volume rm

# 3. Recrear infraestructura
docker compose up -d

# 4. Esperar inicialización
sleep 60

# 5. Copiar fair scheduler
docker cp fairscheduler.xml spark-master:/opt/spark/conf/
docker cp fairscheduler.xml spark-worker:/opt/spark/conf/

# 6. Iniciar pipeline
./scripts/run-latent-generator.sh 100 &
sleep 30
./scripts/run-streaming-processor.sh &
```

### Escenario 4: Solo Reiniciar API o Dashboard

```bash
# Reiniciar API (si cambió código)
docker compose build recs-api
docker compose up -d recs-api

# Reiniciar Dashboard (si cambió código)
docker compose build recs-dashboard
docker compose up -d recs-dashboard
```

### Escenario 5: Checkpoint Corrupto

Si el streaming processor falla por checkpoint corrupto:

```bash
# 1. Limpiar checkpoints
docker exec namenode hadoop fs -rm -r -f /checkpoints/ratings_stream/processor

# 2. Reiniciar processor
docker exec spark-master bash -c "ps aux | grep 'ratings_stream_processor' | grep -v grep | awk '{print \$2}' | xargs -r kill"
sleep 5
./scripts/run-streaming-processor.sh &
```

---

## Verificación del Sistema

### Check Rápido (30 segundos)

```bash
#!/bin/bash
echo "=== VERIFICACIÓN RÁPIDA DEL SISTEMA ==="
echo ""

# Contenedores
echo "📦 Contenedores corriendo:"
docker compose ps | grep -E "(Up|running)" | wc -l

# Spark Jobs
echo ""
echo "⚡ Spark Jobs activos:"
docker exec spark-master bash -c "ps aux | grep -E 'latent_generator|ratings_stream_processor' | grep -v grep | wc -l"

# Datos en Kafka
echo ""
echo "📊 Mensajes en Kafka:"
echo -n "  Ratings: "
docker exec kafka kafka-run-class kafka.tools.GetOffsetShell --broker-list localhost:9092 --topic ratings 2>/dev/null | awk -F: '{sum += $NF} END {print sum}'
echo -n "  Metrics: "
docker exec kafka kafka-run-class kafka.tools.GetOffsetShell --broker-list localhost:9092 --topic metrics 2>/dev/null | awk -F: '{sum += $NF} END {print sum}'

# API
echo ""
echo "🌐 API Health:"
curl -s http://localhost:8000/metrics/health | jq -r '.status' 2>/dev/null || echo "❌ No disponible"

echo ""
echo "✅ Verificación completa"
```

### Check Completo

```bash
./scripts/verify_fase9_system.sh
```

### Verificar Recursos Spark

```bash
./scripts/check-spark-resources.sh
```

**Salida esperada:**
```
✅ Servicios corriendo: spark-master, spark-worker
✅ Workers registrados: 1
   Memoria: 4G
   Cores: 4-6
```

---

## Gestión de Jobs Spark

### Ver Jobs Activos

```bash
./scripts/spark-job-manager.sh list
```

### Detener Todos los Jobs

```bash
./scripts/spark-job-manager.sh kill-all
```

### Ver Recursos Disponibles

```bash
./scripts/spark-job-manager.sh resources
```

### Reconfigurar Fair Scheduling

```bash
./scripts/spark-job-manager.sh fair-mode
```

### Distribución de Recursos

```
Worker Total: 4 cores, 4GB RAM

┌─────────────┬─────────┬────────┬────────────────┐
│ Pool        │ Cores   │ RAM    │ Prioridad      │
├─────────────┼─────────┼────────┼────────────────┤
│ streaming   │ 2 cores │ 1GB    │ ALTA (peso 2)  │
│ batch       │ 2 cores │ 1GB    │ MEDIA (peso 1) │
│ generator   │ 1 core  │ 512MB  │ BAJA (peso 1)  │
└─────────────┴─────────┴────────┴────────────────┘
```

---

## Detener el Sistema

### Opción 1: Detener Solo Jobs Spark

```bash
# Detener jobs manualmente
./scripts/spark-job-manager.sh kill-all

# O presionar Ctrl+C en cada terminal donde corre un proceso
```

### Opción 2: Detener Todo el Sistema (Conserva Datos)

```bash
./scripts/stop-system.sh
```

Esto detiene y elimina todos los contenedores, pero **conserva los datos** en volúmenes Docker.

### Opción 3: Limpieza Completa (⚠️ Elimina Datos)

```bash
./scripts/stop-system.sh

# Eliminar volúmenes (PERDERÁS TODOS LOS DATOS)
docker volume prune -f
```

---

## Monitoreo

### Interfaces Web

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Dashboard** | http://localhost:8501 | Visualizaciones en tiempo real |
| **API Docs** | http://localhost:8000/docs | Documentación Swagger |
| **API Health** | http://localhost:8000/metrics/health | Estado del sistema |
| **Spark Master** | http://localhost:8080 | Jobs y recursos Spark |
| **Spark Worker** | http://localhost:8081 | Estado del worker |
| **HDFS** | http://localhost:9870 | Explorador de archivos |
| **YARN** | http://localhost:8088 | Gestor de recursos |

### Comandos de Monitoreo

```bash
# Ver estado de contenedores
docker compose ps

# Ver logs de un servicio
docker compose logs -f spark-master
docker compose logs -f kafka
docker compose logs -f recs-api

# Ver recursos de Docker
docker stats

# Ver estructura de HDFS
./scripts/recsys-utils.sh hdfs-ls /

# Ver uso de disco en HDFS
./scripts/recsys-utils.sh hdfs-du /streams
```

### Logs en Tiempo Real

```bash
# Streaming processor
docker logs -f spark-master | grep -i "batch"

# Ver métricas enviadas a Kafka
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic metrics \
  --from-beginning

# Ver ratings generados
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic ratings \
  --max-messages 10
```

### Verificar Datos en HDFS

```bash
# Ver datos de streaming
docker exec namenode hadoop fs -ls -R /streams/ratings/

# Ver resultados de analytics
docker exec namenode hadoop fs -ls -R /outputs/analytics/
```

### Probar la API

```bash
# Health check
curl http://localhost:8000/metrics/health | jq

# Resumen de métricas
curl http://localhost:8000/metrics/summary | jq

# Top-10 películas
curl "http://localhost:8000/metrics/topn?limit=10" | jq
```

### Verificar Kafka

```bash
# Ver mensajes en topic 'ratings'
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic ratings \
  --max-messages 5

# Contar mensajes
docker exec kafka kafka-run-class kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic ratings
```

---

## Troubleshooting

### Problema: "Initial job has not accepted any resources"

**Causa:** Jobs no pueden obtener recursos del worker

**Solución:**
```bash
# 1. Verificar recursos
./scripts/check-spark-resources.sh

# 2. Si worker no está registrado, reiniciarlo
docker compose restart spark-worker

# 3. Esperar 10 segundos
sleep 10

# 4. Verificar nuevamente
./scripts/check-spark-resources.sh
```

### Problema: Fair Scheduler No Carga

**Síntoma:** `ERROR FairSchedulableBuilder: File does not exist`

**Solución:**
```bash
# Recrear archivo en contenedores
docker exec spark-master mkdir -p /opt/spark/conf
docker exec spark-worker mkdir -p /opt/spark/conf
docker cp fairscheduler.xml spark-master:/opt/spark/conf/
docker cp fairscheduler.xml spark-worker:/opt/spark/conf/

# Reiniciar jobs
./scripts/spark-job-manager.sh kill-all
./scripts/run-streaming-processor.sh &
```

### Problema: Dashboard No Muestra Datos

**Verificar:**
```bash
# 1. API está corriendo
curl http://localhost:8000/metrics/health

# 2. Hay métricas en Kafka
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic metrics \
  --max-messages 5

# 3. Reiniciar API y dashboard
docker compose restart recs-api recs-dashboard
```

### Problema: Topic 'ratings' Vacío

**Solución:**
```bash
# Generar datos nuevamente
./scripts/run-latent-generator.sh 200

# Verificar que se crearon
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic ratings \
  --max-messages 5
```

### Problema: Worker No Registrado

**Solución:**
```bash
# Verificar logs del worker
docker logs spark-worker | tail -20

# Reiniciar servicios Spark
docker compose restart spark-master spark-worker

# Esperar y verificar
sleep 10
./scripts/check-spark-resources.sh
```

### Problema: HDFS No Accesible

**Solución:**
```bash
# Verificar que namenode está corriendo
docker ps | grep namenode

# Reiniciar namenode si es necesario
docker restart namenode
sleep 30
```

### Problema: Puertos En Uso

**Solución:**
```bash
# Identificar proceso usando el puerto (ejemplo: 8080)
sudo lsof -i :8080

# Matar proceso si es necesario
sudo kill -9 <PID>
```

### Limpiar Checkpoints

```bash
# Limpiar checkpoints del generador
./scripts/clean-checkpoints.sh latent

# Limpiar checkpoints del procesador
./scripts/clean-checkpoints.sh processor

# Limpiar todos los checkpoints
./scripts/clean-checkpoints.sh all
```

---

## Comandos de Referencia Rápida

### Infraestructura

```bash
# Iniciar sistema
./scripts/start-system.sh

# Detener sistema
./scripts/stop-system.sh

# Ver estado
docker compose ps
./scripts/check-status.sh

# Ver logs
docker compose logs -f <nombre-contenedor>
```

### Pipeline de Datos

```bash
# Generador de ratings
./scripts/run-latent-generator.sh 100

# Procesador de streaming
./scripts/run-streaming-processor.sh

# Analytics batch
./scripts/run-batch-analytics.sh
```

### Gestión de Jobs

```bash
# Ver jobs activos
./scripts/spark-job-manager.sh list

# Ver recursos
./scripts/spark-job-manager.sh resources

# Detener todos los jobs
./scripts/spark-job-manager.sh kill-all
```

### HDFS

```bash
# Listar directorio
./scripts/recsys-utils.sh hdfs-ls <path>

# Ver uso de disco
./scripts/recsys-utils.sh hdfs-du <path>

# Estado del cluster
./scripts/recsys-utils.sh hdfs-status
```

### Kafka

```bash
# Listar topics
./scripts/recsys-utils.sh kafka-topics

# Describir topic
./scripts/recsys-utils.sh kafka-describe <topic-name>

# Consumir mensajes
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic <topic-name> \
  --max-messages 10
```

---

## Workflow Recomendado

### Ejecución Secuencial (Más Estable)

```bash
# 1. Verificar sistema
./scripts/check-spark-resources.sh

# 2. Generar datos
./scripts/run-latent-generator.sh 100

# 3. Iniciar streaming (dejar corriendo) - Terminal 2
./scripts/run-streaming-processor.sh

# 4. Generar más datos mientras streaming corre - Terminal 1
./scripts/run-latent-generator.sh 200

# 5. Esperar 2-3 minutos, luego analytics - Terminal 3
sleep 180
./scripts/run-batch-analytics.sh

# 6. Ver dashboard en navegador
# http://localhost:8501
```

### Ejecución Paralela (Background)

```bash
# Streaming en background
nohup ./scripts/run-streaming-processor.sh > streaming.log 2>&1 &

# Esperar que inicie
sleep 30

# Generar datos continuamente
./scripts/run-latent-generator.sh 500

# Analytics periódico
sleep 180
./scripts/run-batch-analytics.sh

# Monitorear
tail -f streaming.log
```

---

## Métricas de Rendimiento Esperadas

| Componente | Métrica | Valor Esperado |
|------------|---------|----------------|
| **Latent Generator** | Velocidad | ~10-20 ratings/segundo |
| **Streaming Processor** | Latencia | <1 segundo por batch |
| **Streaming Processor** | Throughput | 100+ ratings/segundo |
| **Batch Analytics** | Duración | 30-60 segundos |
| **Dashboard** | Actualización | Cada 5 segundos |

---

**Consultar también:**
- `GUIA_DESPLIEGUE_INICIAL_UNICO.md` - Primera ejecución
- `DOCUMENTACION.md` - Documentación técnica completa
