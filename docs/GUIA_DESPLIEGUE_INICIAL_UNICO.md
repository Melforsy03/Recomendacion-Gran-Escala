# 🚀 Guía de Despliegue Inicial - Primera Ejecución

**Sistema de Recomendación de Películas en Gran Escala**  
**Versión:** 1.0  
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
9. [Paso 8: Configurar Kafka](#paso-8-configurar-kafka)
10. [Paso 9: Iniciar Pipeline de Streaming](#paso-9-iniciar-pipeline-de-streaming)
11. [Paso 10: Verificar Sistema Completo](#paso-10-verificar-sistema-completo)
12. [Checklist Final](#checklist-final)

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
- **Python:** 3.8+ (para scripts auxiliares)

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
# Verificar si algún puerto está en uso
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
- `movie.csv`
- `rating.csv`
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
# Esperar 60 segundos para que todos los servicios se inicialicen
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

**Tests ejecutados:**
- ✅ Conectividad de servicios
- ✅ HDFS (lectura/escritura)
- ✅ Kafka (topics/producer/consumer)
- ✅ Spark Standalone
- ✅ Spark + Kafka Integration

### 3.2. Verificación Manual de Servicios Críticos

```bash
# HDFS
echo "=== HDFS ===" && curl -s http://localhost:9870 | grep -q "Hadoop" && echo "✅ OK" || echo "❌ ERROR"

# YARN
echo "=== YARN ===" && curl -s http://localhost:8088 | grep -q "cluster" && echo "✅ OK" || echo "❌ ERROR"

# Spark
echo "=== Spark ===" && curl -s http://localhost:8080 | grep -q "Spark" && echo "✅ OK" || echo "❌ ERROR"

# API
echo "=== API ===" && curl -s http://localhost:8000/metrics/health | grep -q "healthy" && echo "✅ OK" || echo "❌ ERROR"
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

### 4.1. Verificar que fairscheduler.xml Existe

```bash
ls -la fairscheduler.xml
```

### 4.2. Copiar a Contenedores Spark

```bash
# Crear directorio de configuración
docker exec spark-master mkdir -p /opt/spark/conf
docker exec spark-worker mkdir -p /opt/spark/conf

# Copiar archivo
docker cp fairscheduler.xml spark-master:/opt/spark/conf/
docker cp fairscheduler.xml spark-worker:/opt/spark/conf/
```

### 4.3. Verificar Configuración

```bash
# Verificar en spark-master
docker exec spark-master cat /opt/spark/conf/fairscheduler.xml | head -10

# Verificar en spark-worker
docker exec spark-worker cat /opt/spark/conf/fairscheduler.xml | head -10
```

**Pools configurados:**
- `streaming` (prioridad ALTA, peso 2)
- `batch` (prioridad MEDIA, peso 1)
- `generator` (prioridad BAJA, peso 1)
- `default` (peso 1)

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
# Asegurarse de estar en el directorio raíz del proyecto
cd /home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala

# Subir los 6 archivos CSV
./scripts/recsys-utils.sh hdfs-put Dataset/movie.csv /data/movielens/csv/
./scripts/recsys-utils.sh hdfs-put Dataset/rating.csv /data/movielens/csv/
./scripts/recsys-utils.sh hdfs-put Dataset/tag.csv /data/movielens/csv/
./scripts/recsys-utils.sh hdfs-put Dataset/genome_tags.csv /data/movielens/csv/
./scripts/recsys-utils.sh hdfs-put Dataset/genome_scores.csv /data/movielens/csv/
./scripts/recsys-utils.sh hdfs-put Dataset/link.csv /data/movielens/csv/
```

**Tiempo estimado:** 5-10 minutos (dependiendo del tamaño de datos)

### 6.2. Verificar Archivos Subidos

```bash
# Listar archivos en HDFS
./scripts/recsys-utils.sh hdfs-ls /data/movielens/csv
```

**Resultado esperado:** 6 archivos CSV

### 6.3. Verificar Integridad

```bash
./scripts/recsys-utils.sh spark-submit scripts/verify_csv_integrity.py
```

**Resultado esperado:** ~32 millones de registros totales

---

## Paso 7: Ejecutar Pipeline ETL

### 7.1. ETL: CSV a Parquet (Fase 3)

```bash
./scripts/recsys-utils.sh spark-submit movies/src/etl/etl_movielens.py
```

**Tiempo estimado:** 10-15 minutos  
**Qué hace:** Convierte CSV a Parquet con schemas tipados y particionado inteligente

Verificar:
```bash
./scripts/recsys-utils.sh hdfs-ls /data/movielens_parquet
```

### 7.2. Generar Features de Contenido (Fase 4)

```bash
./scripts/recsys-utils.sh spark-submit movies/src/features/generate_content_features.py
```

**Tiempo estimado:** 5-8 minutos  
**Qué hace:** Crea vectores de features (géneros + genome tags) para cada película

Verificar:
```bash
./scripts/recsys-utils.sh hdfs-ls /data/content_features
```

---

## Paso 8: Configurar Kafka

### 8.1. Crear Topics

```bash
python3 movies/src/streaming/create_kafka_topics.py
```

**Tiempo estimado:** 30 segundos  
**Topics creados:**
- `ratings` (6 particiones)
- `metrics` (3 particiones)

### 8.2. Verificar Topics

```bash
./scripts/recsys-utils.sh kafka-topics
```

---

## Paso 9: Iniciar Pipeline de Streaming

### 9.1. Terminal 1 - Generador de Datos

```bash
# Generar ratings sintéticos (1 rating/segundo)
./scripts/run-latent-generator.sh 1
```

**Qué hace:**
- 📊 Genera ratings basados en factores latentes (Factorización Matricial)
- 📤 Envía datos al topic Kafka `ratings`
- 🎯 Usa pool `generator` (prioridad baja)

**Salida esperada:**
```
✅ STREAMING INICIADO
Topic Kafka: ratings
Throughput: 100 ratings/segundo
```

**Dejar correr 1-2 minutos**, luego puedes detenerlo con `Ctrl+C` o dejarlo en background.

### 9.2. Verificar Datos en Kafka

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
  --max-messages 3 \
  --timeout-ms 5000 2>/dev/null
```

### 9.3. Terminal 2 - Procesador de Streaming

```bash
./scripts/run-streaming-processor.sh
```

**Qué hace:**
- 📥 Lee del topic `ratings` de Kafka
- 🪟 Calcula ventanas: Tumbling (1 min) y Sliding (5 min)
- 💾 Guarda agregaciones en HDFS `/streams/ratings/`
- 📊 Publica métricas al topic `metrics`
- 🎯 Usa pool `streaming` (prioridad alta)

**Salida esperada:**
```
-------------------------------------------
Batch: 0
-------------------------------------------
Batch: 1
-------------------------------------------
```

⚠️ **IMPORTANTE:** Dejar este proceso corriendo

### 9.4. Terminal 3 - Analytics Batch (Opcional)

**Esperar 2-3 minutos** después de iniciar el streaming, luego:

```bash
./scripts/run-batch-analytics.sh
```

**Qué hace:**
- 📊 Analiza distribución de ratings (global y por género)
- 🏆 Calcula Top-N películas por periodo
- 📈 Identifica películas trending
- 💾 Guarda resultados en HDFS `/outputs/analytics/`

---

## Paso 10: Verificar Sistema Completo

### 10.1. Probar Endpoints de la API

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

### 10.2. Abrir Dashboard

```bash
# Abrir en navegador (Linux)
xdg-open http://localhost:8501
```

O manualmente: **http://localhost:8501**

**Verificar que se vea:**
- ✅ Métricas en tiempo real actualizándose
- ✅ Gráficas de ratings por minuto
- ✅ Top películas
- ✅ Distribución de géneros

---

## Checklist Final

### Primera Ejecución Completada

- [ ] Requisitos instalados (Docker, Python)
- [ ] Permisos dados a scripts (`chmod +x`)
- [ ] Infraestructura iniciada (10 contenedores corriendo)
- [ ] Tests pasados (suite completa)
- [ ] Fair Scheduler configurado
- [ ] Directorios HDFS creados
- [ ] CSVs subidos a HDFS (6 archivos)
- [ ] Integridad verificada
- [ ] ETL Parquet ejecutado
- [ ] Features de contenido generadas
- [ ] Topics Kafka creados
- [ ] Generador de datos funcionando
- [ ] Streaming processor funcionando
- [ ] API respondiendo
- [ ] Dashboard mostrando métricas

### Estado Final Esperado

```
✅ Infraestructura: HDFS, YARN, Spark, Kafka
✅ Fair Scheduler: Configurado y funcionando
✅ Datos: CSV → Parquet → Features
✅ Generador Latente: Produciendo ratings sintéticos
✅ Streaming Processor: Procesando y agregando datos
✅ API: Respondiendo con métricas en tiempo real
✅ Dashboard: Mostrando visualizaciones actualizadas
```

---

## 🆘 Problemas Comunes en Primera Ejecución

### Contenedores no inician

```bash
./scripts/stop-system.sh
docker compose down --volumes  # Solo si quieres limpiar todo
./scripts/start-system.sh
```

### Puerto en uso

```bash
# Identificar proceso usando el puerto
sudo lsof -i :8080

# Matar proceso si es necesario
sudo kill -9 <PID>
```

### HDFS no accesible

```bash
# Reiniciar namenode
docker restart namenode
sleep 30
```

### ModuleNotFoundError: numpy

```bash
./scripts/instalar-dependencias-spark.sh
```

### Memoria insuficiente

```bash
# Verificar recursos
docker stats

# Si es necesario, ajustar en docker-compose.yml
# SPARK_WORKER_MEMORY=2G  (reducir de 4G)
```

---

## ⏭️ Siguiente Paso

Una vez completada la primera ejecución, consulta:
- **`GUIA_DESPLIEGUE_REGULAR.md`** - Para ejecuciones posteriores
- **`DOCUMENTACION.md`** - Para documentación técnica completa

---

**Tiempo total estimado de primera ejecución:** 45-60 minutos
