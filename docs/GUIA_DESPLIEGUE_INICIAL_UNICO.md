# 🚀 Guía de Despliegue Inicial - Primera Ejecución

**Sistema de Recomendación de Películas en Gran Escala**  
**Versión:** 2.0 (Modelo Híbrido)  
**Última actualización:** Diciembre 2025

---

> ⚠️ **IMPORTANTE:** Esta guía es **solo para la primera vez** que ejecutas el sistema o después de eliminar los volúmenes de Docker.
> Para ejecuciones posteriores, consulta `GUIA_DESPLIEGUE_REGULAR.md`.

---

## 📋 Tabla de Contenidos

1. [Requisitos Previos](#1-requisitos-previos)
2. [Paso 1: Preparar el Entorno](#paso-1-preparar-el-entorno)
3. [Paso 2: Iniciar Infraestructura Docker](#paso-2-iniciar-infraestructura-docker)
4. [Paso 3: Verificar Servicios](#paso-3-verificar-servicios)
5. [Paso 4: Configurar Fair Scheduler](#paso-4-configurar-fair-scheduler)
6. [Paso 5: Crear Estructura HDFS](#paso-5-crear-estructura-hdfs)
7. [Paso 6: Cargar Datos CSV](#paso-6-cargar-datos-csv)
8. [Paso 7: Ejecutar Pipeline ETL](#paso-7-ejecutar-pipeline-etl)
9. [Paso 8: Entrenar Modelos de Recomendación](#paso-8-entrenar-modelos-de-recomendación)
10. [Paso 9: Configurar Kafka](#paso-9-configurar-kafka)
11. [Paso 10: Iniciar Pipeline de Streaming](#paso-10-iniciar-pipeline-de-streaming)
12. [Paso 11: Verificar Sistema Completo](#paso-11-verificar-sistema-completo)
13. [Checklist Final](#checklist-final)

---

## 1. Requisitos Previos

### Hardware Mínimo

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| **RAM** | 8 GB | 12 GB |
| **CPU** | 4 cores | 6+ cores |
| **Disco** | 20 GB libres | 50 GB libres |

### Software Requerido

- **Docker Engine:** 20.10 o superior
- **Docker Compose:** v2.0 o superior
- **Python:** 3.8+ (para scripts auxiliares y entrenamiento)
- **Java:** OpenJDK 8+ (para PySpark local)

### Verificar Instalación

```bash
# Verificar Docker
docker --version
docker compose version

# Verificar que Docker está corriendo
docker info

# Verificar recursos disponibles
docker info | grep -E "CPUs|Total Memory"

# Verificar Python
python3 --version

# Verificar Java (para entrenamiento local)
java -version
```

### Puertos Necesarios (Deben estar libres)

| Puerto | Servicio |
|--------|----------|
| `8000` | API de Recomendaciones |
| `8080` | Spark Master UI |
| `8081` | Spark Worker UI |
| `8088` | YARN ResourceManager UI |
| `8501` | Dashboard Streamlit |
| `9000` | HDFS NameNode RPC |
| `9092` | Kafka (interno) |
| `9093` | Kafka (externo) |
| `9870` | HDFS NameNode UI |

Verificar puertos libres:
```bash
sudo lsof -i :8080,8081,8088,8000,8501,9870,9092,9093,9000
```

---

## Paso 1: Preparar el Entorno

### 1.1. Navegar al Proyecto

```bash
cd /home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala
```

### 1.2. Dar Permisos a Scripts

```bash
chmod +x scripts/*.sh
```

### 1.3. Verificar Estructura del Proyecto

```bash
# Verificar que existen los archivos necesarios
ls -la docker-compose.yml fairscheduler.xml
ls -la Dataset/
ls -la scripts/
```

**Archivos esperados en Dataset/:**
- `movie.csv` (~27,000 películas)
- `rating.csv` (~20M ratings)
- `tag.csv`
- `genome_tags.csv`
- `genome_scores.csv`
- `link.csv`

---

## Paso 2: Iniciar Infraestructura Docker

### 2.1. Iniciar Todos los Servicios

```bash
./scripts/start-system.sh
```

**Tiempo estimado:** 2-3 minutos

### 2.2. Verificar Contenedores

```bash
docker compose ps
```

**Contenedores esperados (10 en total):**

| Contenedor | Estado Esperado |
|------------|-----------------|
| `namenode` | Up (healthy) |
| `datanode` | Up (healthy) |
| `resourcemanager` | Up (healthy) |
| `nodemanager` | Up (healthy) |
| `spark-master` | Up |
| `spark-worker` | Up |
| `zookeeper` | Up |
| `kafka` | Up |
| `recs-api` | Up |
| `recs-dashboard` | Up |

### 2.3. Esperar Inicialización Completa

```bash
echo "Esperando inicialización de servicios..."
sleep 60
```

---

## Paso 3: Verificar Servicios

### 3.1. Verificación Automática

```bash
./scripts/run-all-tests.sh
```

**Tiempo estimado:** 3-5 minutos

### 3.2. Verificación Manual de Servicios Críticos

```bash
# HDFS
echo "=== HDFS ===" && curl -s http://localhost:9870 | grep -q "Hadoop" && echo "✅ OK" || echo "❌ ERROR"

# YARN
echo "=== YARN ===" && curl -s http://localhost:8088 | grep -q "cluster" && echo "✅ OK" || echo "❌ ERROR"

# Spark
echo "=== Spark ===" && curl -s http://localhost:8080 | grep -q "Spark" && echo "✅ OK" || echo "❌ ERROR"

# API
echo "=== API ===" && curl -s http://localhost:8000/recommendations/health | grep -q "status" && echo "✅ OK" || echo "❌ ERROR"
```

### 3.3. Verificar Recursos de Spark

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

## Paso 4: Configurar Fair Scheduler

### 4.1. Copiar a Contenedores Spark

```bash
# Crear directorio de configuración
docker exec spark-master mkdir -p /opt/spark/conf
docker exec spark-worker mkdir -p /opt/spark/conf

# Copiar archivo
docker cp fairscheduler.xml spark-master:/opt/spark/conf/
docker cp fairscheduler.xml spark-worker:/opt/spark/conf/
```

### 4.2. Verificar Configuración

```bash
docker exec spark-master cat /opt/spark/conf/fairscheduler.xml | head -10
```

**Pools configurados:**
- `streaming` (prioridad ALTA, peso 2)
- `batch` (prioridad MEDIA, peso 1)
- `generator` (prioridad BAJA, peso 1)

---

## Paso 5: Crear Estructura HDFS

### 5.1. Crear Directorios Necesarios

```bash
# Datos CSV originales
./scripts/recsys-utils.sh hdfs-mkdir /data/movielens/csv

# Datos Parquet procesados
./scripts/recsys-utils.sh hdfs-mkdir /data/movielens_parquet

# Features de contenido
./scripts/recsys-utils.sh hdfs-mkdir /data/content_features

# Streaming
./scripts/recsys-utils.sh hdfs-mkdir /streams/ratings

# Checkpoints
./scripts/recsys-utils.sh hdfs-mkdir /checkpoints

# Outputs de analytics
./scripts/recsys-utils.sh hdfs-mkdir /outputs/analytics
```

### 5.2. Verificar Estructura

```bash
./scripts/recsys-utils.sh hdfs-ls /
```

---

## Paso 6: Cargar Datos CSV

### 6.1. Subir Archivos CSV a HDFS

```bash
cd /home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala

# Subir los 6 archivos CSV
./scripts/recsys-utils.sh hdfs-put Dataset/movie.csv /data/movielens/csv/
./scripts/recsys-utils.sh hdfs-put Dataset/rating.csv /data/movielens/csv/
./scripts/recsys-utils.sh hdfs-put Dataset/tag.csv /data/movielens/csv/
./scripts/recsys-utils.sh hdfs-put Dataset/genome_tags.csv /data/movielens/csv/
./scripts/recsys-utils.sh hdfs-put Dataset/genome_scores.csv /data/movielens/csv/
./scripts/recsys-utils.sh hdfs-put Dataset/link.csv /data/movielens/csv/
```

**Tiempo estimado:** 5-10 minutos

### 6.2. Verificar Archivos Subidos

```bash
./scripts/recsys-utils.sh hdfs-ls /data/movielens/csv
```

---

## Paso 7: Ejecutar Pipeline ETL

### 7.1. ETL: CSV a Parquet

```bash
./scripts/recsys-utils.sh spark-submit movies/src/etl/etl_movielens.py
```

**Tiempo estimado:** 10-15 minutos

### 7.2. Generar Features de Contenido

```bash
./scripts/recsys-utils.sh spark-submit movies/src/features/generate_content_features.py
```

**Tiempo estimado:** 5-8 minutos

### 7.3. Verificar Datos Procesados

```bash
./scripts/recsys-utils.sh hdfs-ls /data/movielens_parquet
./scripts/recsys-utils.sh hdfs-ls /data/content_features
```

---

## Paso 8: Entrenar Modelos de Recomendación

### 8.1. Entrenamiento Automatizado (Recomendado)

```bash
# Entrena ALS, Item-CF, Content-Based e Hybrid
./scripts/train_all_models.sh
```

**Tiempo estimado:** 30-60 minutos (primera vez)

El script:
1. ✅ Crea entorno virtual en `.venv-training/`
2. ✅ Instala PySpark, pandas, numpy
3. ✅ Verifica Java y memoria
4. ✅ Entrena todos los modelos
5. ✅ Muestra resumen de métricas

### 8.2. Verificar Modelos Entrenados

```bash
# Listar modelos
ls -lh movies/trained_models/*/model_latest

# Ver métricas de ALS
cat movies/trained_models/als/model_latest/metadata.json | python3 -m json.tool
```

**Salida esperada:**
```json
{
  "metrics": {
    "rmse": 0.8234,
    "mae": 0.6431
  }
}
```

### 8.3. Re-entrenar Modelos (si es necesario)

```bash
# Forzar re-entrenamiento de todos los modelos
./scripts/train_all_models.sh --force

# Entrenar solo modelos específicos
./scripts/train_all_models.sh --models=ALS,ITEM_CF
```

---

## Paso 9: Configurar Kafka

### 9.1. Crear Topics

```bash
python3 movies/src/streaming/create_kafka_topics.py
```

**Topics creados:**
- `ratings` (6 particiones)
- `metrics` (3 particiones)

### 9.2. Verificar Topics

```bash
./scripts/recsys-utils.sh kafka-topics
```

---

## Paso 10: Iniciar Pipeline de Streaming

### 10.1. Terminal 1 - Generador de Datos

```bash
./scripts/run-latent-generator.sh 100 &
```

**Salida esperada:**
```
✅ STREAMING INICIADO
Topic Kafka: ratings
Throughput: 100 ratings/segundo
```

Alternativa (productor HTTP que envía a la API local):

```bash
# Envía ratings por HTTP al endpoint /ratings de la API
RATINGS_HTTP_URL="http://localhost:8000/ratings/" python3 movies/src/streaming/latent_http_producer.py 1
```

### 10.2. Terminal 2 - Procesador de Streaming

```bash
./scripts/run-streaming-processor.sh &
```

**Salida esperada:**
```
Batch: 0
Batch: 1
...
```

### 10.3. Terminal 3 - Analytics Batch (Opcional)

**Esperar 2-3 minutos** después de iniciar el streaming:

```bash
./scripts/run-batch-analytics.sh
```

---

## Paso 11: Verificar Sistema Completo

### 11.1. Health Check del API

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

### 11.2. Probar Recomendaciones

```bash
# Recomendaciones con estrategia por defecto (balanced)
curl "http://localhost:8000/recommendations/recommend/123?n=5" | python3 -m json.tool

# Recomendaciones con estrategia específica
curl "http://localhost:8000/recommendations/recommend/123?n=5&strategy=als_heavy" | python3 -m json.tool
```

### 11.3. Verificar Dashboard

```bash
xdg-open http://localhost:8501
```

### 11.4. Verificar Datos en Kafka

```bash
# Ver mensajes en topic 'ratings'
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic ratings \
  --max-messages 5

# Ver métricas
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic metrics \
  --max-messages 5
```

---

## Checklist Final

### Infraestructura
- [ ] 10 contenedores Docker corriendo
- [ ] HDFS accesible (http://localhost:9870)
- [ ] Spark UI accesible (http://localhost:8080)
- [ ] YARN accesible (http://localhost:8088)

### Datos
- [ ] 6 archivos CSV en HDFS `/data/movielens/csv/`
- [ ] Datos Parquet en `/data/movielens_parquet/`
- [ ] Features en `/data/content_features/`

### Modelos
- [ ] Modelo ALS entrenado y cargado
- [ ] Modelo Item-CF entrenado
- [ ] Modelo Content-Based entrenado
- [ ] Modelo Hybrid configurado

### Streaming
- [ ] Topics Kafka creados (ratings, metrics)
- [ ] Latent Generator corriendo
- [ ] Streaming Processor corriendo

### API
- [ ] Health check responde "healthy"
- [ ] Recomendaciones funcionando
- [ ] Dashboard mostrando métricas

---

## 🎉 ¡Sistema Desplegado!

Una vez completados todos los pasos:

1. **API de Recomendaciones:** http://localhost:8000/docs
2. **Dashboard:** http://localhost:8501
3. **Monitoreo Spark:** http://localhost:8080

Para próximas ejecuciones, usa `GUIA_DESPLIEGUE_REGULAR.md`.

---

**Tiempo total de despliegue inicial:** ~60-90 minutos
