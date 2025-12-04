# 📚 Documentación Técnica - Sistema de Recomendación a Gran Escala

**Sistema de Recomendación de Películas en Gran Escala**  
**Versión:** 1.0  
**Última actualización:** Diciembre 2025  
**Repositorio:** Melforsy03/Recomendacion-Gran-Escala  
**Branch:** dev_abraham

---

## 📋 Tabla de Contenidos

1. [Descripción General](#1-descripción-general)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Componentes](#3-componentes)
4. [Configuración](#4-configuración)
5. [API REST](#5-api-rest)
6. [Flujo de Datos](#6-flujo-de-datos)
7. [Scripts Disponibles](#7-scripts-disponibles)
8. [Interfaces Web](#8-interfaces-web)
9. [Persistencia y Volúmenes](#9-persistencia-y-volúmenes)
10. [Fair Scheduler](#10-fair-scheduler)
11. [Consumo de Recursos](#11-consumo-de-recursos)
12. [Seguridad](#12-seguridad)
13. [Estructura del Proyecto](#13-estructura-del-proyecto)

---

## 1. Descripción General

### 1.1. Propósito

Sistema de recomendación de películas a gran escala que implementa:

- **Procesamiento Batch:** ETL, entrenamiento de modelos ALS
- **Procesamiento Streaming:** Agregaciones en tiempo real con ventanas
- **Visualización:** Dashboard interactivo con métricas en tiempo real
- **API REST:** Acceso programático a las métricas y recomendaciones

### 1.2. Dataset

Utiliza el dataset **MovieLens** con aproximadamente:

- ~32 millones de registros totales
- 6 archivos CSV: movies, ratings, tags, genome_tags, genome_scores, links

### 1.3. Tecnologías

| Componente | Tecnología | Versión |
|------------|------------|---------|
| Almacenamiento Distribuido | Apache HDFS | 3.2.1 |
| Gestión de Recursos | Apache YARN | 3.2.1 |
| Procesamiento | Apache Spark | 3.4.1 |
| Mensajería | Apache Kafka | 3.5 |
| Coordinación | Apache Zookeeper | 3.9 |
| API | FastAPI | 0.100+ |
| Dashboard | Streamlit | 1.25+ |
| Contenedores | Docker | 20.10+ |

---

## 2. Arquitectura del Sistema

### 2.1. Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CAPA DE PRESENTACIÓN                        │
├─────────────────────────────────┬───────────────────────────────────┤
│     Streamlit Dashboard         │           FastAPI                 │
│     (http://localhost:8501)     │     (http://localhost:8000)       │
└─────────────────────────────────┴───────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        CAPA DE MENSAJERÍA                          │
├─────────────────────────────────────────────────────────────────────┤
│                         Apache Kafka                                │
│              Topics: ratings (6 particiones)                        │
│                       metrics (3 particiones)                       │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     CAPA DE PROCESAMIENTO                          │
├───────────────────────┬─────────────────────────────────────────────┤
│  Spark Streaming      │              Spark Batch                    │
│  - Latent Generator   │              - ETL Pipeline                 │
│  - Stream Processor   │              - Feature Engineering          │
│  - Metrics Publisher  │              - ALS Model Training           │
│                       │              - Batch Analytics              │
└───────────────────────┴─────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     CAPA DE ALMACENAMIENTO                         │
├─────────────────────────────────────────────────────────────────────┤
│                         Apache HDFS                                 │
│  /data/movielens/csv/      - Datos CSV originales                  │
│  /data/movielens_parquet/  - Datos en formato Parquet              │
│  /data/content_features/   - Features de contenido                  │
│  /models/als/              - Modelo ALS entrenado                   │
│  /streams/ratings/         - Agregaciones de streaming              │
│  /outputs/analytics/       - Resultados de análisis batch           │
│  /checkpoints/             - Checkpoints de Spark Streaming         │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2. Flujo de Datos Completo

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
                         │ Dashboard    │
                         └──────────────┘
```

---

## 3. Componentes

### 3.1. Infraestructura Docker

| Contenedor | Imagen | Puertos | Descripción |
|------------|--------|---------|-------------|
| `namenode` | bde2020/hadoop-namenode:2.0.0-hadoop3.2.1-java8 | 9870, 9000 | HDFS NameNode |
| `datanode` | bde2020/hadoop-datanode:2.0.0-hadoop3.2.1-java8 | 9864 | HDFS DataNode |
| `resourcemanager` | bde2020/hadoop-resourcemanager:2.0.0-hadoop3.2.1-java8 | 8088 | YARN ResourceManager |
| `nodemanager` | bde2020/hadoop-nodemanager:2.0.0-hadoop3.2.1-java8 | 8042 | YARN NodeManager |
| `spark-master` | bitnami/spark:3.4.1 | 8080, 7077 | Spark Master |
| `spark-worker` | bitnami/spark:3.4.1 | 8081 | Spark Worker |
| `zookeeper` | confluentinc/cp-zookeeper:7.5.0 | 2181 | Zookeeper |
| `kafka` | confluentinc/cp-kafka:7.5.0 | 9092, 9093 | Kafka Broker |
| `recs-api` | Custom (FastAPI) | 8000 | API REST |
| `recs-dashboard` | Custom (Streamlit) | 8501 | Dashboard |

### 3.2. Jobs de Spark

#### Latent Generator (`latent_generator.py`)

- **Función:** Genera ratings sintéticos basados en factorización matricial
- **Pool:** `generator` (prioridad baja)
- **Recursos:** 1 core, 512MB RAM
- **Output:** Topic Kafka `ratings`

#### Streaming Processor (`ratings_stream_processor.py`)

- **Función:** Procesa ratings en tiempo real con ventanas
- **Pool:** `streaming` (prioridad alta)
- **Recursos:** 2 cores, 1GB RAM
- **Ventanas:**
  - Tumbling: 1 minuto
  - Sliding: 5 minutos
- **Output:** HDFS + Topic Kafka `metrics`

#### Batch Analytics (`batch_analytics.py`)

- **Función:** Análisis histórico y trending
- **Pool:** `batch` (prioridad media)
- **Recursos:** 2 cores, 1GB RAM
- **Output:** HDFS `/outputs/analytics/`

### 3.3. ETL Pipeline

1. **etl_movielens.py:** Convierte CSV a Parquet con schemas tipados
2. **generate_content_features.py:** Genera vectores de features (géneros + genome tags)

---

## 4. Configuración

### 4.1. Archivos de Configuración

| Archivo | Ubicación | Descripción |
|---------|-----------|-------------|
| `docker-compose.yml` | Raíz | Definición de servicios Docker |
| `fairscheduler.xml` | Raíz | Configuración Fair Scheduler Spark |
| `core-site.xml` | hadoop-conf/ | Configuración core de Hadoop |
| `hdfs-site.xml` | hadoop-conf/ | Configuración HDFS |
| `yarn-site.xml` | hadoop-conf/ | Configuración YARN |

### 4.2. Variables de Entorno Principales

#### Spark Worker

```yaml
SPARK_MODE: worker
SPARK_MASTER_URL: spark://spark-master:7077
SPARK_WORKER_MEMORY: 4G
SPARK_WORKER_CORES: 4
```

#### Kafka

```yaml
KAFKA_BROKER_ID: 1
KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092,PLAINTEXT_HOST://localhost:9093
```

### 4.3. Configuración de Spark Submit

```bash
spark-submit \
  --master spark://spark-master:7077 \
  --deploy-mode client \
  --conf spark.scheduler.mode=FAIR \
  --conf spark.scheduler.allocation.file=/opt/spark/conf/fairscheduler.xml \
  --conf spark.scheduler.pool=<pool_name> \
  --executor-memory 1G \
  --total-executor-cores 2 \
  <script.py>
```

---

## 5. API REST

### 5.1. Endpoints Disponibles

#### Health Check

```http
GET /metrics/health
```

**Response:**

```json
{
  "status": "healthy",
  "last_update": "2025-12-03T10:00:00.000Z",
  "metrics_available": true
}
```

#### Resumen de Métricas

```http
GET /metrics/summary
```

**Response:**

```json
{
  "window_start": "2025-12-03T09:59:00.000Z",
  "window_end": "2025-12-03T10:00:00.000Z",
  "window_type": "tumbling_1min",
  "total_ratings": 6000,
  "avg_rating": 3.50,
  "p50_rating": 3.5,
  "p95_rating": 4.5,
  "timestamp": "2025-12-03T10:00:24.000Z",
  "last_update": "2025-12-03T10:00:24.000Z"
}
```

#### Top-N Películas

```http
GET /metrics/topn?limit=10
```

**Response:**

```json
{
  "window_start": "2025-12-03T09:59:00.000Z",
  "window_end": "2025-12-03T10:00:00.000Z",
  "movies": [32518, 103135, 68435, 87191, 74226],
  "timestamp": "2025-12-03T10:00:24.000Z",
  "count": 5
}
```

#### Métricas por Género

```http
GET /metrics/genres
```

**Response:**

```json
{
  "window_start": "2025-12-03T09:59:00.000Z",
  "window_end": "2025-12-03T10:00:00.000Z",
  "genres": {
    "Action": {"count": 150, "avg_rating": 3.8},
    "Comedy": {"count": 200, "avg_rating": 3.5}
  },
  "timestamp": "2025-12-03T10:00:24.000Z"
}
```

#### Historial de Métricas

```http
GET /metrics/history?limit=50
```

**Response:**

```json
{
  "count": 50,
  "history": [
    {"type": "summary", "timestamp": "...", "data": {...}},
    {"type": "topn", "timestamp": "...", "data": {...}}
  ]
}
```

### 5.2. Documentación Interactiva

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## 6. Flujo de Datos

### 6.1. Pipeline Batch (Primera Ejecución)

```
CSV Files → HDFS → ETL (Parquet) → Features → HDFS
```

**Fases:**

1. **Fase 3:** ETL CSV → Parquet
2. **Fase 4:** Feature Engineering

### 6.2. Pipeline Streaming (Ejecución Continua)

```
Latent Generator → Kafka (ratings) → Stream Processor → Kafka (metrics) → API → Dashboard
                                                     ↓
                                                   HDFS
```

**Componentes:**

1. **Latent Generator:** Produce ratings sintéticos
2. **Streaming Processor:** Consume, agrega, publica métricas
3. **API Consumer:** Consume métricas de Kafka
4. **Dashboard:** Visualiza métricas en tiempo real

---

## 7. Scripts Disponibles

### 7.1. Scripts de Inicio

| Script | Descripción | Uso |
|--------|-------------|-----|
| `start-system.sh` | Inicia toda la infraestructura | `./scripts/start-system.sh` |
| `run-latent-generator.sh` | Inicia generador de ratings | `./scripts/run-latent-generator.sh 100` |
| `run-streaming-processor.sh` | Inicia procesador streaming | `./scripts/run-streaming-processor.sh` |
| `run-batch-analytics.sh` | Ejecuta analytics batch | `./scripts/run-batch-analytics.sh` |
| `quickstart.sh` | Inicio rápido completo | `./scripts/quickstart.sh` |

### 7.2. Scripts de Verificación

| Script | Descripción | Uso |
|--------|-------------|-----|
| `check-spark-resources.sh` | Ver recursos de Spark | `./scripts/check-spark-resources.sh` |
| `check-status.sh` | Estado de servicios | `./scripts/check-status.sh` |
| `run-all-tests.sh` | Suite completa de tests | `./scripts/run-all-tests.sh` |
| `verify_fase9_system.sh` | Verificación completa | `./scripts/verify_fase9_system.sh` |

### 7.3. Scripts de Mantenimiento

| Script | Descripción | Uso |
|--------|-------------|-----|
| `stop-system.sh` | Detener todo el sistema | `./scripts/stop-system.sh` |
| `clean-checkpoints.sh` | Limpiar checkpoints | `./scripts/clean-checkpoints.sh all` |
| `spark-job-manager.sh` | Gestión de jobs Spark | `./scripts/spark-job-manager.sh list` |
| `instalar-dependencias-spark.sh` | Instalar deps Python | `./scripts/instalar-dependencias-spark.sh` |

### 7.4. Scripts de Utilidad

| Script | Descripción | Uso |
|--------|-------------|-----|
| `recsys-utils.sh` | Utilidades generales HDFS/Kafka | `source ./scripts/recsys-utils.sh` |
| `verify_csv_integrity.py` | Verificar integridad CSV | `spark-submit scripts/verify_csv_integrity.py` |

---

## 8. Interfaces Web

| Servicio | URL | Puerto | Descripción |
|----------|-----|--------|-------------|
| Dashboard Streamlit | `localhost:8501` | 8501 | Visualizaciones en tiempo real |
| API Docs (Swagger) | `localhost:8000/docs` | 8000 | Documentación interactiva API |
| API Health | `localhost:8000/metrics/health` | 8000 | Estado del sistema |
| Spark Master UI | `localhost:8080` | 8080 | Jobs y recursos Spark |
| Spark Worker UI | `localhost:8081` | 8081 | Estado del worker |
| HDFS NameNode | `localhost:9870` | 9870 | Explorador de archivos |
| YARN ResourceManager | `localhost:8088` | 8088 | Gestor de recursos |
| YARN NodeManager | `localhost:8042` | 8042 | Estado del node |

---

## 9. Persistencia y Volúmenes

### 9.1. Volúmenes Docker

Los siguientes datos persisten entre reinicios:

| Volumen | Contenedor | Descripción |
|---------|------------|-------------|
| `namenode_data` | namenode | Metadatos HDFS |
| `datanode_data` | datanode | Datos HDFS |
| `spark_master_data` | spark-master | Checkpoints Spark |
| `spark_worker_data` | spark-worker | Logs de trabajo |
| `kafka_data` | kafka | Datos de topics |
| `zookeeper_data` | zookeeper | Estado del cluster |
| `spark-ivy-cache` | spark-* | Caché de dependencias |
| `spark-pip-cache` | spark-* | Caché de paquetes Python |

### 9.2. Estructura HDFS

```
/
├── data/
│   ├── movielens/
│   │   └── csv/           # Datos CSV originales
│   ├── movielens_parquet/ # Datos en Parquet
│   └── content_features/  # Features de películas
├── streams/
│   └── ratings/           # Agregaciones de streaming
├── outputs/
│   └── analytics/         # Resultados batch
└── checkpoints/           # Checkpoints Streaming
```

---

## 10. Fair Scheduler

### 10.1. Configuración de Pools

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

### 10.2. Distribución de Recursos

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

### 10.3. Verificación

```bash
# Verificar configuración en contenedores
docker exec spark-master cat /opt/spark/conf/fairscheduler.xml
docker exec spark-worker cat /opt/spark/conf/fairscheduler.xml
```

---

## 11. Consumo de Recursos

### 11.1. Recursos por Servicio

| Servicio | CPU | RAM | Descripción |
|----------|-----|-----|-------------|
| HDFS (namenode + datanode) | 0.5 cores | 2GB | Almacenamiento distribuido |
| YARN (RM + NM) | 0.5 cores | 2GB | Gestión de recursos |
| Spark Master | 0.5 cores | 512MB | Coordinador Spark |
| Spark Worker | 4-6 cores | 4GB | Ejecutor de trabajos |
| Kafka + Zookeeper | 1 core | 2GB | Mensajería |
| API + Dashboard | 0.5 cores | 1GB | Visualización |
| **TOTAL** | **~8-10 cores** | **~12GB** | |

### 11.2. Requisitos Mínimos

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| RAM | 8 GB | 12-16 GB |
| CPU | 4 cores | 6-8 cores |
| Disco | 20 GB | 50+ GB |

### 11.3. Métricas de Rendimiento

| Componente | Métrica | Valor Esperado |
|------------|---------|----------------|
| Latent Generator | Throughput | ~10-20 ratings/segundo |
| Streaming Processor | Latencia | <1 segundo por batch |
| Streaming Processor | Throughput | 100+ ratings/segundo |
| Batch Analytics | Duración | 30-60 segundos |
| Dashboard | Actualización | Cada 5 segundos |

---

## 12. Seguridad

### 12.1. Estado Actual

⚠️ **Este sistema es para desarrollo/demostración.**

- Sin autenticación en servicios
- Sin encriptación de datos
- Puertos expuestos sin firewall

### 12.2. Recomendaciones para Producción

- [ ] Implementar autenticación en API
- [ ] Habilitar SSL/TLS en todas las comunicaciones
- [ ] Configurar Kerberos para Hadoop
- [ ] Implementar network policies
- [ ] Usar secrets management (Vault, etc.)
- [ ] Configurar firewalls y ACLs
- [ ] Habilitar auditoría y logging

---

## 13. Estructura del Proyecto

```
Recomendacion-Gran-Escala/
├── docker-compose.yml          # Definición de servicios
├── fairscheduler.xml           # Configuración Fair Scheduler
├── requirements.txt            # Dependencias Python
├── README.md                   # Documentación principal
│
├── Dataset/                    # Datos MovieLens
│   ├── movie.csv
│   ├── rating.csv
│   ├── tag.csv
│   ├── genome_tags.csv
│   ├── genome_scores.csv
│   └── link.csv
│
├── docs/                       # Documentación
│   ├── DOCUMENTACION.md        # Este archivo
│   ├── GUIA_DESPLIEGUE_INICIAL_UNICO.md
│   └── GUIA_DESPLIEGUE_REGULAR.md
│
├── hadoop-conf/                # Configuración Hadoop
│   ├── core-site.xml
│   ├── hdfs-site.xml
│   └── yarn-site.xml
│
├── movies/                     # Código principal
│   ├── api/                    # API FastAPI
│   │   ├── Dockerfile
│   │   └── main.py
│   ├── dashboard/              # Dashboard Streamlit
│   │   ├── Dockerfile
│   │   └── app.py
│   └── src/
│       ├── etl/                # Pipeline ETL
│       ├── features/           # Feature Engineering
│       ├── models/             # Modelos ML
│       └── streaming/          # Procesamiento Streaming
│
├── scripts/                    # Scripts de gestión
│   ├── start-system.sh
│   ├── stop-system.sh
│   ├── run-latent-generator.sh
│   ├── run-streaming-processor.sh
│   ├── run-batch-analytics.sh
│   ├── check-spark-resources.sh
│   ├── spark-job-manager.sh
│   └── ...
│
└── tests/                      # Scripts de prueba
    ├── test-connectivity.sh
    ├── test-hdfs.sh
    ├── test-kafka.sh
    └── ...
```

---

## Documentación Adicional

Para más información, consultar:

- **Primera Ejecución:** `docs/GUIA_DESPLIEGUE_INICIAL_UNICO.md`
- **Ejecuciones Regulares:** `docs/GUIA_DESPLIEGUE_REGULAR.md`
- **Comandos Rápidos:** `COMANDOS_RAPIDOS.md` (raíz del proyecto)

---

**Mantenido por:** Equipo de Desarrollo  
**Última actualización:** Diciembre 2025
