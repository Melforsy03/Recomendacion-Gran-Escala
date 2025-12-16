# 🔄 Guía de Despliegue Regular - Operaciones Diarias

**Sistema de Recomendación de Películas en Gran Escala**  
**Versión:** 2.0 (Modelo Híbrido)  
**Última actualización:** Diciembre 2025

---

> ⚠️ **Prerequisito:** Esta guía asume que ya ejecutaste el despliegue inicial. Si es la primera vez, consulta `GUIA_DESPLIEGUE_INICIAL_UNICO.md`.

---

## 📋 Tabla de Contenidos

1. [Quick Start - Inicio Rápido](#1-quick-start---inicio-rápido)
2. [Inicio y Detención del Sistema](#2-inicio-y-detención-del-sistema)
3. [Escenarios de Reinicio](#3-escenarios-de-reinicio)
4. [Comandos de Verificación](#4-comandos-de-verificación)
5. [Operaciones de Streaming](#5-operaciones-de-streaming)
6. [Operaciones de Análisis Batch](#6-operaciones-de-análisis-batch)
7. [Troubleshooting](#7-troubleshooting)
8. [Ejemplos de Salida del Sistema](#8-ejemplos-de-salida-del-sistema)
9. [Monitoreo y Métricas](#9-monitoreo-y-métricas)
10. [Mantenimiento](#10-mantenimiento)

---

## 1. Quick Start - Inicio Rápido

### Iniciar Todo el Sistema (30 segundos)

```bash
cd /home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala
./scripts/start-system.sh
```

### Verificar que Todo Funciona

```bash
./scripts/check-status.sh
```

### Iniciar Pipelines de Datos

```bash
# Terminal 1: Generador de ratings
./scripts/run-latent-generator.sh 100 &

# Terminal 2: Procesador de streaming
./scripts/run-streaming-processor.sh &
```

### Acceder al Sistema

| Servicio | URL |
|----------|-----|
| **API Docs** | http://localhost:8000/docs |
| **Dashboard** | http://localhost:8501 |
| **Spark UI** | http://localhost:8080 |
| **HDFS** | http://localhost:9870 |

---

## 2. Inicio y Detención del Sistema

### Iniciar Sistema Completo

```bash
./scripts/start-system.sh
```

**Servicios iniciados:**
- Infraestructura: HDFS, YARN, Spark
- Mensajería: Kafka, Zookeeper
- Aplicación: API, Dashboard

### Detener Sistema Completo

```bash
./scripts/stop-system.sh
```

### Reiniciar Sistema

```bash
./scripts/stop-system.sh && sleep 5 && ./scripts/start-system.sh
```

### Iniciar/Detener Servicios Específicos

```bash
# Solo API
docker compose restart recs-api

# Solo Dashboard
docker compose restart recs-dashboard

# Solo Kafka
docker compose restart kafka
```

---

## 3. Escenarios de Reinicio

### Escenario A: Reinicio Normal (más común)

Después de un reinicio del equipo:

```bash
cd /home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala
./scripts/start-system.sh
```

**Tiempo:** ~1 minuto

### Escenario B: Reinicio después de Cambios en API

```bash
docker compose build --no-cache recs-api
docker compose up -d recs-api
```

### Escenario C: Reinicio después de Cambios en Dashboard

```bash
docker compose build --no-cache recs-dashboard
docker compose up -d recs-dashboard
```

### Escenario D: Limpiar y Reiniciar (datos persistentes)

```bash
docker compose down
./scripts/clean-checkpoints.sh
docker compose up -d
```

### Escenario E: Reset Completo (perder datos)

> ⚠️ **CUIDADO:** Esto elimina todos los datos en HDFS y Kafka

```bash
docker compose down -v
docker compose up -d
# Volver a ejecutar GUIA_DESPLIEGUE_INICIAL_UNICO.md
```

---

## 4. Comandos de Verificación

### Estado General del Sistema

```bash
./scripts/check-status.sh
```

**Salida esperada:**

```
========================================
  ESTADO DEL SISTEMA
========================================

📦 CONTENEDORES:
✅ namenode       Up 2 hours (healthy)
✅ datanode       Up 2 hours (healthy)
✅ resourcemanager Up 2 hours (healthy)
✅ nodemanager    Up 2 hours (healthy)
✅ spark-master   Up 2 hours
✅ spark-worker   Up 2 hours
✅ zookeeper      Up 2 hours
✅ kafka          Up 2 hours
✅ recs-api       Up 2 hours
✅ recs-dashboard Up 2 hours

🌐 SERVICIOS WEB:
✅ HDFS UI        http://localhost:9870
✅ Spark Master   http://localhost:8080
✅ YARN           http://localhost:8088
✅ API            http://localhost:8000
✅ Dashboard      http://localhost:8501
```

### Verificar Recursos de Spark

```bash
./scripts/check-spark-resources.sh
```

### Verificar HDFS

```bash
./scripts/recsys-utils.sh hdfs-ls /data
```

### Verificar Kafka

```bash
./scripts/recsys-utils.sh kafka-topics
```

### Verificar API Health

```bash
curl http://localhost:8000/recommendations/health | python3 -m json.tool
```

**Respuesta esperada:**

```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_version": "hybrid_v1",
  "strategy": "balanced",
  "models": {
    "als": true,
    "item_cf": true,
    "content_based": true
  }
}
```

---

## 5. Operaciones de Streaming

### Iniciar Productor API/Dataset → Kafka

```bash
# Modo dataset local (sin dependencias externas)
./scripts/run-api-kafka-producer.sh

# Con API externa
./scripts/run-api-kafka-producer.sh http://api.example.com/ratings

# O usando variable de entorno
RATINGS_API_URL="http://api.example.com/ratings" ./scripts/run-api-kafka-producer.sh
```

### Iniciar Generador de Ratings

```bash
# Generar 100 ratings/segundo
./scripts/run-latent-generator.sh 100

# Generar 500 ratings/segundo (alto throughput)
./scripts/run-latent-generator.sh 500
```

Alternativa: usar el productor HTTP que envía directamente a la API (útil para pruebas locales):

```bash
# Envía ratings por HTTP al endpoint /ratings de la API (ejemplo: 1 r/s)
RATINGS_HTTP_URL="http://localhost:8000/ratings/" python3 movies/src/streaming/latent_http_producer.py 1
```

### Simular Tráfico HTTP

```bash
# Simular tráfico con valores por defecto (10 req/s durante 30s)
./scripts/simulate-traffic.sh

# Simular alta carga (50 req/s durante 5 minutos)
./scripts/simulate-traffic.sh 50 300

# Usando flags explícitos
./scripts/simulate-traffic.sh --rate 10 --duration 30

# Con API personalizada
./scripts/simulate-traffic.sh --rate 20 --duration 60 --api-url http://localhost:8000
```

**Características del simulador:**
- Distribución realista de usuarios (80% existentes, 20% nuevos)
- Métricas de latencia (p50, p95, p99)
- Logs detallados con timestamps en `logs/`
- Verificación automática de disponibilidad de la API

### Iniciar Procesador de Streaming

```bash
./scripts/run-streaming-processor.sh
```

### Detener Streaming (graceful)

```bash
# Encontrar proceso
ps aux | grep -E "latent|streaming"

# Detener con Ctrl+C o
kill -SIGTERM <PID>
```

### Ver Datos en Kafka

```bash
# Ver mensajes de ratings (últimos 10)
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic ratings \
  --max-messages 10

# Ver métricas
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic metrics \
  --max-messages 5
```

---

## 6. Operaciones de Análisis Batch

### Ejecutar Analytics Batch

```bash
./scripts/run-batch-analytics.sh
```

**Outputs generados en HDFS:**
- `/outputs/analytics/movie_stats`
- `/outputs/analytics/user_activity`
- `/outputs/analytics/temporal_trends`

### Leer Resultados de Analytics

```bash
# Ver estadísticas de películas
./scripts/recsys-utils.sh hdfs-cat /outputs/analytics/movie_stats/part-*.json | head -20

# Ver actividad de usuarios
./scripts/recsys-utils.sh hdfs-cat /outputs/analytics/user_activity/part-*.json | head -20
```

---

## 7. Troubleshooting

### Error: Contenedor no arranca

```bash
# Ver logs del contenedor
docker logs <nombre-contenedor> --tail 100

# Ejemplo para API
docker logs recs-api --tail 100
```

### Error: HDFS no accesible

```bash
# Verificar NameNode
docker logs namenode --tail 50

# Verificar conectividad
docker exec namenode hdfs dfsadmin -report
```

### Error: API responde 500

```bash
# Ver logs de la API
docker logs recs-api --tail 200

# Verificar que los modelos están cargados
curl http://localhost:8000/recommendations/health
```

### Error: "Model not loaded"

Esto ocurre cuando los modelos no se han entrenado o no se encuentran:

```bash
# Verificar que existen los modelos
ls -la movies/trained_models/*/model_latest/

# Re-entrenar si es necesario
./scripts/train_all_models.sh

# Reiniciar API para recargar modelos
docker compose restart recs-api
```

### Error: Kafka no disponible

```bash
# Verificar Zookeeper
docker logs zookeeper --tail 50

# Verificar Kafka
docker logs kafka --tail 50

# Reiniciar Kafka
docker compose restart zookeeper kafka
```

### Error: Spark job falla

```bash
# Ver logs de Spark Master
docker logs spark-master --tail 100

# Ver logs de Spark Worker
docker logs spark-worker --tail 100

# Verificar memoria disponible
docker exec spark-master cat /proc/meminfo | grep MemAvailable
```

### Error: Dashboard no carga datos

```bash
# Ver logs del dashboard
docker logs recs-dashboard --tail 100

# Verificar conectividad con API
docker exec recs-dashboard curl http://recs-api:8000/recommendations/health
```

### Limpiar Checkpoints (si streaming falla)

```bash
./scripts/clean-checkpoints.sh
```

---

## 8. Ejemplos de Salida del Sistema

### API: GET /recommendations/health

**Request:**
```bash
curl http://localhost:8000/recommendations/health
```

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_version": "hybrid_v1",
  "strategy": "balanced",
  "models": {
    "als": true,
    "item_cf": true,
    "content_based": true
  }
}
```

### API: GET /recommendations/recommend/{user_id}

**Request:**
```bash
curl "http://localhost:8000/recommendations/recommend/123?n=5&strategy=balanced"
```

**Response:**
```json
{
  "user_id": 123,
  "recommendations": [
    {
      "movie_id": 318,
      "title": "Shawshank Redemption, The (1994)",
      "genres": "Crime|Drama",
      "score": 4.85
    },
    {
      "movie_id": 296,
      "title": "Pulp Fiction (1994)",
      "genres": "Comedy|Crime|Drama|Thriller",
      "score": 4.72
    },
    {
      "movie_id": 2571,
      "title": "Matrix, The (1999)",
      "genres": "Action|Sci-Fi|Thriller",
      "score": 4.65
    },
    {
      "movie_id": 593,
      "title": "Silence of the Lambs, The (1991)",
      "genres": "Crime|Horror|Thriller",
      "score": 4.58
    },
    {
      "movie_id": 260,
      "title": "Star Wars: Episode IV - A New Hope (1977)",
      "genres": "Action|Adventure|Sci-Fi",
      "score": 4.52
    }
  ],
  "strategy": "balanced"
}
```

### Estrategias Disponibles

| Estrategia | Descripción | Pesos (ALS/Item-CF/Content) |
|------------|-------------|--------------------------|
| `als_heavy` | Prioriza filtrado colaborativo | 0.6 / 0.3 / 0.1 |
| `balanced` | Balance entre métodos | 0.4 / 0.35 / 0.25 |
| `content_heavy` | Prioriza contenido | 0.2 / 0.3 / 0.5 |
| `cold_start` | Para usuarios nuevos | 0.1 / 0.2 / 0.7 |

**Ejemplo con estrategia cold_start:**

```bash
curl "http://localhost:8000/recommendations/recommend/999999?n=3&strategy=cold_start"
```

```json
{
  "user_id": 999999,
  "recommendations": [
    {
      "movie_id": 318,
      "title": "Shawshank Redemption, The (1994)",
      "genres": "Crime|Drama",
      "score": 4.91
    },
    {
      "movie_id": 858,
      "title": "Godfather, The (1972)",
      "genres": "Crime|Drama",
      "score": 4.88
    },
    {
      "movie_id": 50,
      "title": "Usual Suspects, The (1995)",
      "genres": "Crime|Mystery|Thriller",
      "score": 4.85
    }
  ],
  "strategy": "cold_start"
}
```

### Streaming: Formato de Mensajes Kafka

**Topic: ratings**
```json
{
  "user_id": 12345,
  "movie_id": 318,
  "rating": 4.5,
  "timestamp": 1702234567890
}
```

**Topic: metrics**
```json
{
  "batch_id": 42,
  "records_processed": 1000,
  "avg_rating": 3.67,
  "processing_time_ms": 234,
  "timestamp": 1702234567890
}
```

### Batch Analytics: Estadísticas de Películas

```json
{
  "movie_id": 318,
  "title": "Shawshank Redemption, The (1994)",
  "count": 81482,
  "avg_rating": 4.43,
  "std_rating": 0.71,
  "min_rating": 0.5,
  "max_rating": 5.0
}
```

---

## 9. Monitoreo y Métricas

### URLs de Monitoreo

| Componente | URL | Descripción |
|------------|-----|-------------|
| **Spark Master** | http://localhost:8080 | Jobs, workers, memoria |
| **Spark Worker** | http://localhost:8081 | Tareas del worker |
| **YARN** | http://localhost:8088 | Aplicaciones YARN |
| **HDFS** | http://localhost:9870 | Estado del filesystem |
| **Dashboard** | http://localhost:8501 | Métricas del sistema |

### Métricas Importantes

**Spark:**
- Workers activos
- Jobs en ejecución
- Memoria disponible
- Cores utilizados

**HDFS:**
- Espacio utilizado/disponible
- Bloques bajo-replicados
- DataNodes activos

**API:**
- Latencia de respuesta
- Requests por segundo
- Modelos cargados

### Comandos de Monitoreo

```bash
# Ver memoria de Docker
docker stats --no-stream

# Ver uso de disco de HDFS
docker exec namenode hdfs dfsadmin -report | grep -A 5 "Live datanodes"

# Ver jobs de Spark activos
curl -s http://localhost:8080/json/ | python3 -m json.tool
```

---

## 10. Mantenimiento

### Limpieza Periódica

```bash
# Limpiar checkpoints antiguos (semanal)
./scripts/clean-checkpoints.sh

# Limpiar imágenes Docker no usadas (mensual)
docker image prune -a

# Limpiar logs de contenedores (mensual)
docker compose logs --tail=1000 > logs_backup.txt
```

### Backup de Modelos

```bash
# Crear backup de modelos entrenados
tar -czvf models_backup_$(date +%Y%m%d).tar.gz movies/trained_models/
```

### Re-entrenamiento de Modelos

```bash
# Re-entrenar todos los modelos (mensual recomendado)
./scripts/train_all_models.sh --force
```

### Actualizar Sistema

```bash
# Pull de cambios
git pull origin main

# Rebuild de contenedores
docker compose build --no-cache

# Reiniciar
docker compose up -d
```

---

## 📌 Comandos de Referencia Rápida

| Acción | Comando |
|--------|---------|
| Iniciar sistema | `./scripts/start-system.sh` |
| Detener sistema | `./scripts/stop-system.sh` |
| Ver estado | `./scripts/check-status.sh` |
| Ver logs API | `docker logs recs-api --tail 100` |
| Reiniciar API | `docker compose restart recs-api` |
| Health check | `curl localhost:8000/recommendations/health` |
| Obtener recomendaciones | `curl "localhost:8000/recommendations/recommend/123?n=5"` |
| Ver Kafka topics | `./scripts/recsys-utils.sh kafka-topics` |
| Limpiar checkpoints | `./scripts/clean-checkpoints.sh` |
| Re-entrenar modelos | `./scripts/train_all_models.sh` |

---

**¿Problemas?** Revisa la sección de [Troubleshooting](#7-troubleshooting) o consulta `DOCUMENTACION.md` para información técnica detallada.
