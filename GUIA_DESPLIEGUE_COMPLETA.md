# 🚀 Guía Completa de Despliegue - Sistema de Recomendación a Gran Escala

**Fecha:** 10 de noviembre de 2025  
**Versión:** 1.0  
**Estado:** ✅ Sistema completamente funcional

---

## 📋 Tabla de Contenidos

1. [Requisitos Previos](#requisitos-previos)
2. [Primera Ejecución](#primera-ejecución)
3. [Ejecuciones Posteriores](#ejecuciones-posteriores)
4. [Verificación del Sistema](#verificación-del-sistema)
5. [Troubleshooting](#troubleshooting)
6. [Scripts Útiles](#scripts-útiles)

---

## 🔧 Requisitos Previos

### Software Necesario

- **Docker Engine:** 20.10 o superior
- **Docker Compose:** v2.0 o superior
- **RAM:** Mínimo 8GB (recomendado 12GB)
- **CPU:** Mínimo 4 cores
- **Disco:** Mínimo 20GB libres

### Verificar Instalación

```bash
# Verificar Docker
docker --version
docker compose version

# Verificar recursos disponibles
docker info | grep -E "CPUs|Total Memory"
```

---

## 🎬 Primera Ejecución

### Paso 1: Clonar y Preparar el Repositorio

```bash
cd /home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala

# Verificar estructura
ls -la
```

### Paso 2: Configurar Fairscheduler

El archivo `fairscheduler.xml` debe estar en la raíz del proyecto. Verificar:

```bash
ls -la fairscheduler.xml
```

Si no existe, fue creado con esta configuración:

```xml
<?xml version="1.0"?>
<allocations>
  <!-- Pool para Streaming Processor - Prioridad ALTA -->
  <pool name="streaming">
    <schedulingMode>FAIR</schedulingMode>
    <weight>2</weight>
    <minShare>1</minShare>
  </pool>
  
  <!-- Pool para Batch Analytics - Prioridad MEDIA -->
  <pool name="batch">
    <schedulingMode>FAIR</schedulingMode>
    <weight>1</weight>
    <minShare>1</minShare>
  </pool>
  
  <!-- Pool para Latent Generator - Prioridad BAJA -->
  <pool name="generator">
    <schedulingMode>FAIR</schedulingMode>
    <weight>1</weight>
    <minShare>1</minShare>
  </pool>
  
  <!-- Pool por defecto -->
  <pool name="default">
    <schedulingMode>FAIR</schedulingMode>
    <weight>1</weight>
    <minShare>0</minShare>
  </pool>
</allocations>
```

### Paso 3: Levantar la Infraestructura

```bash
# Levantar todos los servicios
docker compose up -d

# Verificar que todos los contenedores estén corriendo
docker compose ps
```

**Contenedores esperados:**
- ✅ namenode (HDFS)
- ✅ datanode (HDFS)
- ✅ resourcemanager (YARN)
- ✅ nodemanager (YARN)
- ✅ spark-master
- ✅ spark-worker
- ✅ zookeeper
- ✅ kafka
- ✅ recs-api
- ✅ recs-dashboard

### Paso 4: Esperar Inicialización (IMPORTANTE)

```bash
# Esperar 30-60 segundos para que los servicios se inicialicen
sleep 60

# Verificar salud de servicios críticos
echo "=== HDFS ===" && curl -s http://localhost:9870 | grep -q "Hadoop" && echo "✅ OK" || echo "❌ ERROR"
echo "=== YARN ===" && curl -s http://localhost:8088 | grep -q "cluster" && echo "✅ OK" || echo "❌ ERROR"
echo "=== Spark ===" && curl -s http://localhost:8080 | grep -q "Spark" && echo "✅ OK" || echo "❌ ERROR"
echo "=== API ===" && curl -s http://localhost:8000/metrics/health | grep -q "healthy" && echo "✅ OK" || echo "❌ ERROR"
```

### Paso 5: Verificar Fair Scheduler

```bash
# Verificar que fairscheduler.xml esté montado en Spark
docker exec spark-master cat /opt/spark/conf/fairscheduler.xml | head -5
docker exec spark-worker cat /opt/spark/conf/fairscheduler.xml | head -5
```

**Si falta el archivo** (solo debería pasar si los contenedores se recrearon):

```bash
docker exec spark-master mkdir -p /opt/spark/conf
docker exec spark-worker mkdir -p /opt/spark/conf
docker cp fairscheduler.xml spark-master:/opt/spark/conf/
docker cp fairscheduler.xml spark-worker:/opt/spark/conf/
```

### Paso 6: Iniciar el Pipeline de Datos

#### 6.1. Iniciar Generador Latente

```bash
# Generar ratings sintéticos (100 ratings/segundo)
./scripts/run-latent-generator.sh 100 &

# Guardar el PID para detenerlo después
GENERATOR_PID=$!
echo $GENERATOR_PID > /tmp/generator.pid
```

**Esperar 1-2 minutos** para que genere suficientes datos iniciales.

#### 6.2. Verificar Datos en Kafka

```bash
# Ver cuántos mensajes se han generado
docker exec kafka kafka-run-class kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic ratings 2>/dev/null | \
  awk -F: '{sum += $NF} END {print "Total ratings:", sum}'

# Ver un mensaje de ejemplo
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic ratings \
  --max-messages 1 \
  --timeout-ms 5000 2>/dev/null
```

#### 6.3. Iniciar Streaming Processor

```bash
# Lanzar el procesador de streaming
./scripts/run-streaming-processor.sh &

# Guardar el PID
PROCESSOR_PID=$!
echo $PROCESSOR_PID > /tmp/processor.pid
```

**Esperar 30-60 segundos** para que procese los primeros batches.

#### 6.4. Verificar Procesamiento

```bash
# Ver cuántas métricas se han generado
docker exec kafka kafka-run-class kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic metrics 2>/dev/null | \
  awk -F: '{sum += $NF} END {print "Total metrics:", sum}'

# Ver logs del processor (últimas ventanas procesadas)
tail -50 /tmp/processor.log | grep -E "Batch|count=" | tail -10
```

### Paso 7: Verificar API y Dashboard

#### 7.1. Probar Endpoints de la API

```bash
# Health check
curl -s http://localhost:8000/metrics/health | jq

# Resumen de métricas
curl -s http://localhost:8000/metrics/summary | jq

# Top-N películas
curl -s http://localhost:8000/metrics/topn?limit=5 | jq

# Métricas por género
curl -s http://localhost:8000/metrics/genres | jq
```

#### 7.2. Abrir Dashboard

```bash
# Abrir en navegador
xdg-open http://localhost:8501
```

O manualmente: **http://localhost:8501**

**Verificar que se vea:**
- ✅ Métricas en tiempo real actualizándose
- ✅ Gráficas de ratings por minuto
- ✅ Top películas con IDs
- ✅ Distribución de géneros

### Paso 8: Estado Final Primera Ejecución

Si todo funciona correctamente, deberías tener:

```
✅ Infraestructura: HDFS, YARN, Spark, Kafka
✅ Fair Scheduler: Configurado y funcionando
✅ Generador: Produciendo ~100 ratings/segundo
✅ Streaming Processor: Procesando y agregando datos
✅ API: Respondiendo con métricas en tiempo real
✅ Dashboard: Mostrando visualizaciones actualizadas
```

---

## 🔄 Ejecuciones Posteriores

### Escenario 1: Sistema Ya Corriendo (Restart Suave)

Si los contenedores están corriendo pero quieres reiniciar los jobs de Spark:

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

### Escenario 2: Contenedores Detenidos (Restart Completo)

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

# 2. Eliminar volúmenes (CUIDADO: elimina todos los datos)
docker volume ls | grep recomendacion-gran-escala | awk '{print $2}' | xargs docker volume rm

# 3. Recrear infraestructura
docker compose up -d

# 4. Esperar inicialización
sleep 60

# 5. Verificar fair scheduler
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
docker compose build api
docker compose up -d api

# Reiniciar Dashboard (si cambió código)
docker compose build dashboard
docker compose up -d dashboard
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

## ✅ Verificación del Sistema

### Check Rápido (30 segundos)

```bash
#!/bin/bash
echo "=== VERIFICACIÓN RÁPIDA DEL SISTEMA ==="
echo ""

# Contenedores
echo "📦 Contenedores:"
docker compose ps | grep -E "(Up|healthy)" | wc -l
echo ""

# Spark Jobs
echo "⚡ Spark Jobs:"
docker exec spark-master bash -c "ps aux | grep -E 'latent_generator|ratings_stream_processor' | grep -v grep | wc -l"
echo ""

# Datos en Kafka
echo "📊 Mensajes en Kafka:"
echo -n "  Ratings: "
docker exec kafka kafka-run-class kafka.tools.GetOffsetShell --broker-list localhost:9092 --topic ratings 2>/dev/null | awk -F: '{sum += $NF} END {print sum}'
echo -n "  Metrics: "
docker exec kafka kafka-run-class kafka.tools.GetOffsetShell --broker-list localhost:9092 --topic metrics 2>/dev/null | awk -F: '{sum += $NF} END {print sum}'
echo ""

# API
echo "🌐 API Health:"
curl -s http://localhost:8000/metrics/health | jq -r '.status'
echo ""

echo "✅ Verificación completa"
```

Guardar como `scripts/check-quick.sh` y ejecutar:

```bash
chmod +x scripts/check-quick.sh
./scripts/check-quick.sh
```

### Check Completo (2 minutos)

```bash
# Usar script existente
./scripts/verify_fase9_system.sh
```

---

## 🔧 Troubleshooting

### Problema 1: Fair Scheduler No Carga

**Síntoma:**
```
ERROR FairSchedulableBuilder: File file:/opt/spark/conf/fairscheduler.xml does not exist
```

**Solución:**
```bash
# Recrear archivo en contenedores
docker exec spark-master mkdir -p /opt/spark/conf
docker exec spark-worker mkdir -p /opt/spark/conf
docker cp fairscheduler.xml spark-master:/opt/spark/conf/
docker cp fairscheduler.xml spark-worker:/opt/spark/conf/

# Reiniciar jobs
docker exec spark-master bash -c "ps aux | grep 'spark-submit' | grep -v grep | awk '{print \$2}' | xargs -r kill"
./scripts/run-latent-generator.sh 100 &
./scripts/run-streaming-processor.sh &
```

### Problema 2: API Devuelve 404 en /metrics/topn

**Síntoma:**
```
{"detail":"No hay datos de top-N disponibles"}
```

**Causa:** El streaming processor no está enviando datos o la API no los está consumiendo.

**Solución:**
```bash
# 1. Verificar que hay métricas en Kafka
docker exec kafka kafka-run-class kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 --topic metrics 2>/dev/null

# 2. Si hay mensajes pero API no los ve, reiniciar API
docker compose stop api
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 \
  --delete --group api-metrics-consumer 2>&1
docker compose start api

# 3. Esperar 10 segundos y probar
sleep 10
curl -s http://localhost:8000/metrics/topn?limit=3 | jq
```

### Problema 3: Dashboard Muestra Error ValueError

**Síntoma:**
```
ValueError: Value of 'x' is not the name of a column in 'data_frame'
```

**Causa:** El dashboard fue actualizado para manejar tanto IDs como objetos completos.

**Solución:**
```bash
# Reconstruir dashboard
docker compose build dashboard
docker compose up -d dashboard

# Esperar 5 segundos
sleep 5
xdg-open http://localhost:8501
```

### Problema 4: Streaming Processor Procesa Ventanas Vacías

**Síntoma:**
```
Getting 0 (0.0 B) non-empty blocks
```

**Causa:** No hay datos nuevos en el topic ratings.

**Solución:**
```bash
# 1. Verificar que el generador esté corriendo
docker exec spark-master bash -c "ps aux | grep latent_generator | grep -v grep"

# 2. Si no está corriendo, iniciarlo
./scripts/run-latent-generator.sh 100 &

# 3. Esperar 30 segundos para que genere datos
sleep 30

# 4. Verificar que los datos lleguen
docker exec kafka kafka-run-class kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 --topic ratings 2>/dev/null
```

### Problema 5: ModuleNotFoundError: numpy

**Síntoma:**
```
ModuleNotFoundError: No module named 'numpy'
```

**Solución:**
```bash
# Instalar dependencias en ambos contenedores
./scripts/instalar-dependencias-spark.sh

# O manualmente:
docker exec spark-master pip install numpy pandas kafka-python
docker exec spark-worker pip install numpy pandas kafka-python
```

### Problema 6: Memoria Insuficiente

**Síntoma:**
```
Container killed because of memory limit
```

**Solución:**
```bash
# Verificar recursos disponibles
docker info | grep -E "CPUs|Total Memory"

# Ajustar configuración en docker-compose.yml
# Reducir memoria de Spark worker:
#   SPARK_WORKER_MEMORY=2G  # En lugar de 4G

# Reiniciar
docker compose down
docker compose up -d
```

---

## 📚 Scripts Útiles

### Scripts de Inicio

| Script | Descripción | Uso |
|--------|-------------|-----|
| `start-system.sh` | Inicia toda la infraestructura | `./scripts/start-system.sh` |
| `run-latent-generator.sh` | Inicia generador de ratings | `./scripts/run-latent-generator.sh 100` |
| `run-streaming-processor.sh` | Inicia procesador de streaming | `./scripts/run-streaming-processor.sh` |
| `quickstart.sh` | Inicio rápido completo | `./scripts/quickstart.sh` |

### Scripts de Verificación

| Script | Descripción | Uso |
|--------|-------------|-----|
| `verify_fase9_system.sh` | Verificación completa del sistema | `./scripts/verify_fase9_system.sh` |
| `check-spark-resources.sh` | Ver recursos de Spark | `./scripts/check-spark-resources.sh` |
| `check-status.sh` | Estado de servicios | `./scripts/check-status.sh` |

### Scripts de Mantenimiento

| Script | Descripción | Uso |
|--------|-------------|-----|
| `clean-checkpoints.sh` | Limpiar checkpoints | `./scripts/clean-checkpoints.sh all` |
| `stop-system.sh` | Detener todo el sistema | `./scripts/stop-system.sh` |
| `reiniciar-pipeline-completo.sh` | Reinicio completo con limpieza | `./scripts/reiniciar-pipeline-completo.sh` |
| `spark-job-manager.sh` | Gestión de jobs Spark | `./scripts/spark-job-manager.sh list` |

### Scripts de Utilidad

| Script | Descripción | Uso |
|--------|-------------|-----|
| `instalar-dependencias-spark.sh` | Instalar Python deps en Spark | `./scripts/instalar-dependencias-spark.sh` |
| `recsys-utils.sh` | Utilidades generales | `source ./scripts/recsys-utils.sh` |

---

## 🌐 URLs de Acceso

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Dashboard** | http://localhost:8501 | Interfaz principal de visualización |
| **API Metrics** | http://localhost:8000/docs | Documentación interactiva de la API |
| **Spark Master UI** | http://localhost:8080 | Interfaz de Spark Master |
| **Spark Worker UI** | http://localhost:8081 | Interfaz de Spark Worker |
| **HDFS NameNode** | http://localhost:9870 | Interfaz de HDFS |
| **YARN ResourceManager** | http://localhost:8088 | Interfaz de YARN |

---

## 📊 Endpoints de la API

### Health & Status

```bash
# Health check
GET http://localhost:8000/metrics/health

# Response:
{
  "status": "healthy",
  "last_update": "2025-11-10T18:58:24.000Z",
  "metrics_available": true
}
```

### Métricas Agregadas

```bash
# Resumen actual
GET http://localhost:8000/metrics/summary

# Response:
{
  "window_start": "2025-11-10T18:57:00.000Z",
  "window_end": "2025-11-10T18:58:00.000Z",
  "window_type": "tumbling_1min",
  "total_ratings": 6000,
  "avg_rating": 3.50,
  "p50_rating": 3.5,
  "p95_rating": 4.5,
  "timestamp": "2025-11-10T18:58:24.000Z",
  "last_update": "2025-11-10T18:58:24.000Z"
}
```

### Top Películas

```bash
# Top-N películas
GET http://localhost:8000/metrics/topn?limit=10

# Response:
{
  "window_start": "2025-11-10T18:57:00.000Z",
  "window_end": "2025-11-10T18:58:00.000Z",
  "movies": [32518, 103135, 68435, 87191, 74226, ...],
  "timestamp": "2025-11-10T18:58:24.000Z",
  "count": 10
}
```

### Métricas por Género

```bash
# Géneros
GET http://localhost:8000/metrics/genres

# Response:
{
  "window_start": "2025-11-10T18:57:00.000Z",
  "window_end": "2025-11-10T18:58:00.000Z",
  "genres": {
    "Action": {"count": 1},
    "Action|Adventure": {"count": 1},
    ...
  },
  "timestamp": "2025-11-10T18:58:24.000Z"
}
```

### Historial

```bash
# Historial de métricas
GET http://localhost:8000/metrics/history?limit=50

# Response:
{
  "count": 50,
  "history": [
    {"type": "summary", "timestamp": "...", "data": {...}},
    ...
  ]
}
```

---

## 🎯 Flujo de Datos Completo

```
┌─────────────────────┐
│ Latent Generator    │  (Spark Job)
│ • Matrix Factoriza. │  → 100 ratings/seg
│ • Synthetic Ratings │
└──────────┬──────────┘
           │
           ▼
    ┌─────────────┐
    │ Kafka Topic │
    │  "ratings"  │  → 240K+ mensajes
    └──────┬──────┘
           │
           ▼
┌──────────────────────┐
│ Streaming Processor  │  (Spark Structured Streaming)
│ • Tumbling: 1 min    │
│ • Sliding: 5 min     │
│ • Agregaciones       │
│ • Top-N              │
└──────────┬───────────┘
           │
           ├──────────────────────┐
           │                      │
           ▼                      ▼
    ┌─────────────┐      ┌──────────────┐
    │ HDFS        │      │ Kafka Topic  │
    │ /streams/*  │      │  "metrics"   │  → 74+ mensajes
    └─────────────┘      └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │ FastAPI      │
                         │ Consumer     │
                         └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │ Streamlit    │
                         │ Dashboard    │  → http://localhost:8501
                         └──────────────┘
```

---

## 📝 Notas Importantes

### Configuración de Fair Scheduler

El Fair Scheduler distribuye recursos entre 4 pools:

1. **streaming** (weight=2, minShare=1): Mayor prioridad para procesador en tiempo real
2. **batch** (weight=1, minShare=1): Prioridad media para análisis batch
3. **generator** (weight=1, minShare=1): Prioridad baja para generador sintético
4. **default** (weight=1, minShare=0): Pool por defecto

### Persistencia de Datos

Los siguientes datos persisten entre reinicios (volúmenes Docker):

- ✅ Datos HDFS: `namenode_data`, `datanode_data`
- ✅ Checkpoints Spark: `spark_master_data`, `spark_worker_data`
- ✅ Datos Kafka: `kafka_data`, `zookeeper_data`
- ✅ Caché Ivy/PIP: `spark-ivy-cache`, `spark-pip-cache`

### Dependencias Python

Las dependencias se instalan automáticamente en el primer inicio de los contenedores Spark:

- numpy >= 1.24.4
- pandas >= 2.0.3
- kafka-python >= 2.0.2
- python-dateutil, pytz

Si necesitas reinstalarlas: `./scripts/instalar-dependencias-spark.sh`

### Consumo de Recursos Aproximado

| Servicio | CPU | RAM | Descripción |
|----------|-----|-----|-------------|
| HDFS (namenode + datanode) | 0.5 cores | 2GB | Almacenamiento distribuido |
| YARN (RM + NM) | 0.5 cores | 2GB | Gestión de recursos |
| Spark Master | 0.5 cores | 512MB | Coordinador Spark |
| Spark Worker | 6 cores | 4GB | Ejecutor de trabajos |
| Kafka + Zookeeper | 1 core | 2GB | Mensajería |
| API + Dashboard | 0.5 cores | 1GB | Visualización |
| **TOTAL** | **~9 cores** | **~12GB** | |

---

## 🔒 Seguridad

⚠️ **Este sistema es para desarrollo/demostración.**

Para producción, considerar:

- Autenticación y autorización en todos los servicios
- Encriptación de datos en tránsito y reposo
- Network policies y firewalls
- Secrets management para credenciales
- Monitoring y alertas

---

## 📚 Documentación Adicional

- **Fair Scheduling:** `docs/FAIR_SCHEDULING_GUIA.md`
- **Optimización:** `docs/OPTIMIZACION_RECURSOS.md`
- **Comandos Rápidos:** `docs/COMANDOS_RAPIDOS.md`
- **Solución API:** `SOLUCION_API_SIN_DATOS.md`
- **Solución Streaming:** `SOLUCION_STREAMING_EARLIEST.md`
- **Solución Completa:** `SOLUCION_COMPLETA_FINAL.md`

---

## 🆘 Soporte

Si encuentras problemas:

1. Revisar logs de contenedores: `docker compose logs [servicio]`
2. Verificar recursos: `docker stats`
3. Consultar troubleshooting en este documento
4. Revisar issues del repositorio

---

**Última actualización:** 10 de noviembre de 2025  
**Mantenido por:** abraham  
**Repositorio:** Melforsy03/Recomendacion-Gran-Escala  
**Branch:** dev_abraham
