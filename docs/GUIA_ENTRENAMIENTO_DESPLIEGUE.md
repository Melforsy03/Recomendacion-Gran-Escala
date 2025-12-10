# Guía de Entrenamiento y Despliegue - Sistema de Recomendación

**Autor:** Sistema de Recomendación a Gran Escala  
**Fecha:** 8 de diciembre de 2025  
**Versión:** 1.0

---

## 📋 Tabla de Contenidos

1. [Descripción General](#descripción-general)
2. [Prerequisitos](#prerequisitos)
3. [Arquitectura del Sistema](#arquitectura-del-sistema)
4. [Fase 1: Entrenamiento Local](#fase-1-entrenamiento-local)
5. [Fase 2: Despliegue a Contenedores](#fase-2-despliegue-a-contenedores)
6. [Fase 3: Pruebas y Validación](#fase-3-pruebas-y-validación)
7. [Fase 4: Simulación de Tráfico](#fase-4-simulación-de-tráfico)
8. [Troubleshooting](#troubleshooting)
9. [Referencia de APIs](#referencia-de-apis)

---

## Descripción General

Este sistema implementa un sistema de recomendación multi-modelo que combina:

- **ALS (Alternating Least Squares)**: Filtrado colaborativo con factorización matricial
- **Item-CF**: Filtrado colaborativo basado en similitud entre películas
- **Content-Based**: Recomendaciones basadas en features de películas
- **Hybrid**: Combinación ponderada de los modelos anteriores

### Flujo de Trabajo

```
Dataset/*.csv → Entrenamiento Local → trained_models/ → Docker Volumes → API → Recomendaciones
```

**Características clave:**
- ✅ Entrenamiento local (fuera de Docker)
- ✅ Modelos versionados con symlinks
- ✅ Despliegue via volúmenes Docker (read-only)
- ✅ API REST con cache LRU
- ✅ Fallback automático para usuarios nuevos
- ✅ Simulador de tráfico para pruebas

---

## Prerequisitos

### Software Requerido

| Software | Versión Mínima | Propósito |
|----------|----------------|-----------|
| Python   | 3.8+           | Entrenamiento local |
| Java     | 8+             | PySpark (backend) |
| Docker   | 20.10+         | Contenedores |
| Docker Compose | 2.0+     | Orquestación |

### Recursos de Hardware

- **RAM**: 8GB mínimo (16GB recomendado)
- **CPU**: 4 cores mínimo
- **Disco**: 10GB libres para modelos y logs

### Verificación de Prerequisitos

```bash
# Verificar Python
python3 --version

# Verificar Java
java -version

# Verificar Docker
docker --version
docker-compose --version

# Verificar memoria disponible
free -h
```

---

## Arquitectura del Sistema

### Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                   SISTEMA DE RECOMENDACIÓN                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐         ┌────────────────────┐   │
│  │  Dataset (Local)    │         │  Entrenamiento     │   │
│  │  ├─ rating.csv      │────────▶│  (Local Python)    │   │
│  │  ├─ movie.csv       │         │  ├─ train_als      │   │
│  │  ├─ genome_*.csv    │         │  ├─ train_itemcf   │   │
│  │  └─ ...             │         │  └─ train_content  │   │
│  └─────────────────────┘         └──────────┬─────────┘   │
│                                              │             │
│                                              ▼             │
│                                   ┌────────────────────┐   │
│                                   │  trained_models/   │   │
│                                   │  ├─ als/           │   │
│                                   │  ├─ item_cf/       │   │
│                                   │  ├─ content_based/ │   │
│                                   │  └─ hybrid/        │   │
│                                   └──────────┬─────────┘   │
│                                              │             │
│                                              │ (volume)    │
│                                              ▼             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │           CONTENEDORES DOCKER                        │ │
│  │  ┌──────────────────┐      ┌──────────────────────┐ │ │
│  │  │  API (FastAPI)   │      │  Dashboard          │ │ │
│  │  │  ├─ ALS Model    │◀────▶│  (Streamlit)        │ │ │
│  │  │  ├─ Cache LRU    │      │                      │ │ │
│  │  │  └─ Endpoints    │      └──────────────────────┘ │ │
│  │  └────────┬─────────┘                               │ │
│  │           │                                          │ │
│  │           ▼                                          │ │
│  │  ┌──────────────────┐                               │ │
│  │  │  HTTP Clients    │◀─── Simulador de Tráfico     │ │
│  │  └──────────────────┘                               │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Estructura de Directorios

```
Recomendacion-Gran-Escala/
├── Dataset/                          # Datos de entrada (local)
│   ├── rating.csv                    # ~20M ratings
│   ├── movie.csv                     # ~27K películas
│   ├── genome_scores.csv             # Scores de tags
│   └── genome_tags.csv               # Tags semánticos
│
├── movies/
│   ├── trained_models/               # Modelos entrenados
│   │   ├── als/
│   │   │   ├── model_latest → als_model_v1_20251208_152523/
│   │   │   └── als_model_v1_20251208_152523/
│   │   │       ├── spark_model/      # Modelo Spark MLlib
│   │   │       └── metadata.json     # Parámetros y métricas
│   │   ├── item_cf/
│   │   ├── content_based/
│   │   └── hybrid/
│   │
│   ├── api/                          # API REST
│   │   ├── routes/
│   │   │   ├── recommendations.py    # Endpoints de recs
│   │   │   └── metrics.py            # Endpoints de métricas
│   │   ├── services/
│   │   │   └── recommender_service.py # Lógica de negocio
│   │   └── app/
│   │       └── server.py             # FastAPI app
│   │
│   └── src/recommendation/
│       ├── models/                   # Implementación de modelos
│       │   ├── als_model.py
│       │   ├── item_cf.py
│       │   ├── content_based.py
│       │   └── hybrid_recommender.py
│       └── training/
│           └── train_local_all.py    # Script de entrenamiento
│
├── scripts/
│   ├── train_all_models.sh           # Entrenamiento automatizado
│   ├── copy_models_to_containers.sh  # Despliegue (volúmenes)
│   └── simulate_traffic.py           # Simulador de tráfico
│
├── logs/                             # Logs de simulaciones
│   └── traffic_simulation_*.jsonl
│
└── docker-compose.yml                # Orquestación de servicios
```

---

## Fase 1: Entrenamiento Local

### 1.1. Preparar Entorno

#### Opción A: Script Automatizado (Recomendado)

```bash
# Ejecutar script que crea venv, instala deps y entrena (omite existentes)
./scripts/train_all_models.sh

# Forzar re-entrenamiento de todos los modelos
./scripts/train_all_models.sh --force

# Entrenar solo modelos específicos
./scripts/train_all_models.sh --models=ALS,ITEM_CF
```

El script:
1. ✅ Crea entorno virtual en `.venv-training/`
2. ✅ Instala PySpark, pandas, numpy
3. ✅ Verifica Java y memoria
4. ✅ **Omite modelos ya entrenados** (usa `--force` para re-entrenar)
5. ✅ Ejecuta entrenamiento de modelos faltantes
6. ✅ Muestra resumen de métricas

**Tiempo estimado:** 30-60 minutos (primera vez), < 1 minuto (si ya existen)

#### Opción B: Manual

```bash
# Crear entorno virtual
python3 -m venv .venv-training

# Activar entorno
source .venv-training/bin/activate

# Instalar dependencias
pip install pyspark pandas numpy

# Ejecutar entrenamiento
python movies/src/recommendation/training/train_local_all.py
```

### 1.2. Configuración de Parámetros

Editar `movies/src/recommendation/training/train_local_all.py`:

```python
class Config:
    # Spark
    SPARK_MEMORY = "8g"        # Ajustar según RAM disponible
    SPARK_CORES = 4            # Ajustar según CPU
    
    # ALS
    ALS_RANK = 20              # Dimensiones latentes (10-50)
    ALS_MAX_ITER = 10          # Iteraciones (5-20)
    ALS_REG_PARAM = 0.1        # Regularización (0.01-1.0)
    
    # Item-CF
    ITEM_CF_MIN_COMMON_USERS = 5  # Mínimo de usuarios en común
    
    # Train/Test Split
    TRAIN_RATIO = 0.8          # 80% train, 20% test
```

### 1.3. Entrenar Modelos Específicos

```bash
# Solo ALS (omite si ya existe)
python movies/src/recommendation/training/train_local_all.py --models ALS

# ALS + Item-CF
python movies/src/recommendation/training/train_local_all.py --models ALS,ITEM_CF

# Todos los modelos (default)
python movies/src/recommendation/training/train_local_all.py --models ALS,ITEM_CF,CONTENT,HYBRID

# Forzar re-entrenamiento incluso si ya existe
python movies/src/recommendation/training/train_local_all.py --force

# Forzar solo para modelos específicos
python movies/src/recommendation/training/train_local_all.py --models ALS --force
```

**Nota:** Por defecto, el script **omite el entrenamiento** si ya existe un modelo válido. Usa `--force` para re-entrenar.

### 1.4. Verificar Modelos Entrenados

```bash
# Listar modelos
ls -lh movies/trained_models/*/model_latest

# Ver metadata de ALS
cat movies/trained_models/als/model_latest/metadata.json | jq .

# Ver métricas
cat movies/trained_models/als/model_latest/metadata.json | jq '.metrics'
```

**Output esperado:**

```json
{
  "metrics": {
    "rmse": 0.8234,
    "mae": 0.6123,
    "mse": 0.6780,
    "r2": 0.7456
  }
}
```

### 1.5. Estructura de Modelo Guardado

```
als_model_v1_20251208_152523/
├── spark_model/              # Modelo Spark MLlib (directorio)
│   ├── itemFactors/          # Factores de películas
│   ├── userFactors/          # Factores de usuarios
│   └── metadata/             # Metadata de Spark
├── metadata.json             # Parámetros de entrenamiento
└── model_info.json           # Info adicional
```

---

## Fase 2: Despliegue a Contenedores

### 2.1. Verificar Sistema Docker

```bash
# Verificar servicios corriendo
docker-compose ps

# Si no está corriendo, iniciar
docker-compose up -d

# Verificar logs
docker logs recs-api
```

### 2.2. Desplegar Modelos

Los modelos se montan automáticamente via volúmenes Docker (configurado en `docker-compose.yml`):

```yaml
api:
  volumes:
    - ./movies/trained_models:/app/trained_models:ro  # read-only
    - ./Dataset/movie.csv:/app/movies_metadata.csv:ro
```

**No es necesario copiar archivos manualmente.** Solo reiniciar el contenedor:

```bash
# Reiniciar API para cargar nuevos modelos
docker restart recs-api

# Monitorear logs de startup
docker logs -f recs-api
```

**O usar el script automatizado:**

```bash
./scripts/copy_models_to_containers.sh
```

El script:
1. ✅ Verifica que modelos existen
2. ✅ Verifica volúmenes montados
3. ✅ Reinicia contenedor API
4. ✅ Espera a que servicio esté listo
5. ✅ Verifica health check

### 2.3. Verificar Carga de Modelos

```bash
# Health check
curl http://localhost:8000/recommendations/health | jq .
```

**Output esperado:**

```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_version": "v1_20251208",
  "cache_stats": {
    "size": 0,
    "max_size": 1000,
    "ttl_hours": 1
  },
  "timestamp": "2025-12-08T10:30:00Z"
}
```

### 2.4. Logs de Startup

```bash
docker logs recs-api
```

**Output esperado:**

```
================================================================================
INICIALIZANDO SERVICIO DE RECOMENDACIONES
================================================================================
Creando SparkSession...
✓ Spark 3.4.1 inicializado
Cargando modelo ALS desde: /app/trained_models/als/model_latest/spark_model
✓ Modelo ALS cargado (versión: v1_20251208)
Cargando metadata de películas...
✓ Metadata cargada: 27,278 películas
Calculando top películas populares...
✓ Top 100 películas populares calculadas
================================================================================
✅ SERVICIO DE RECOMENDACIONES LISTO
================================================================================
```

---

## Fase 3: Pruebas y Validación

### 3.1. Pruebas Básicas con cURL

#### Recomendaciones para Usuario

```bash
# Top-10 recomendaciones para usuario 123
curl "http://localhost:8000/recommendations/recommend/123?n=10" | jq .
```

**Response esperado:**

```json
{
  "user_id": 123,
  "recommendations": [
    {
      "movie_id": 318,
      "title": "The Shawshank Redemption (1994)",
      "genres": ["Crime", "Drama"],
      "predicted_rating": 4.85,
      "rank": 1
    },
    {
      "movie_id": 858,
      "title": "The Godfather (1972)",
      "genres": ["Crime", "Drama"],
      "predicted_rating": 4.78,
      "rank": 2
    }
    // ... 8 más
  ],
  "timestamp": "2025-12-08T10:30:00Z",
  "model_version": "v1_20251208",
  "source": "model"
}
```

#### Predicción de Rating

```bash
# Predecir rating de usuario 123 para película 456
curl -X POST "http://localhost:8000/recommendations/predict" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 123, "movie_id": 456}' | jq .
```

**Response esperado:**

```json
{
  "user_id": 123,
  "movie_id": 456,
  "title": "The Matrix (1999)",
  "genres": ["Action", "Sci-Fi", "Thriller"],
  "predicted_rating": 4.65,
  "timestamp": "2025-12-08T10:30:00Z",
  "model_version": "v1_20251208"
}
```

#### Películas Similares

```bash
# Top-10 películas similares a película 1 (Toy Story)
curl "http://localhost:8000/recommendations/similar/1?n=10" | jq .
```

**Response esperado:**

```json
{
  "movie_id": 1,
  "similar_movies": [
    {
      "movie_id": 3114,
      "title": "Toy Story 2 (1999)",
      "genres": ["Animation", "Children", "Comedy"],
      "similarity": 0.92,
      "rank": 1
    },
    {
      "movie_id": 78499,
      "title": "Toy Story 3 (2010)",
      "genres": ["Animation", "Children", "Comedy"],
      "similarity": 0.88,
      "rank": 2
    }
    // ... 8 más
  ],
  "timestamp": "2025-12-08T10:30:00Z",
  "model_version": "v1_20251208"
}
```

### 3.2. Prueba de Fallback (Usuario Nuevo)

```bash
# Usuario sin historial (ID muy alto, fuera del training set)
curl "http://localhost:8000/recommendations/recommend/999999?n=10" | jq .
```

**Response esperado:**

```json
{
  "user_id": 999999,
  "recommendations": [
    // Top 10 películas más populares (fallback)
  ],
  "source": "fallback_popular",
  "model_version": "v1_20251208"
}
```

### 3.3. Prueba de Cache

```bash
# Primera petición (MISS)
time curl "http://localhost:8000/recommendations/recommend/123?n=10"

# Segunda petición (HIT - debería ser más rápida)
time curl "http://localhost:8000/recommendations/recommend/123?n=10"
```

**Verificar logs:**

```bash
docker logs recs-api | grep "Cache"
```

**Output esperado:**

```
Cache MISS: user=123, n=10
Cache SET: user=123, n=10, size=1
Cache HIT: user=123, n=10
```

### 3.4. Documentación Interactiva (Swagger)

```bash
# Abrir en navegador
http://localhost:8000/docs
```

Interfaz interactiva con:
- 📖 Documentación completa de endpoints
- 🔍 Explorador de schemas
- 🧪 Probador interactivo ("Try it out")

---

## Fase 4: Simulación de Tráfico

### 4.1. Configuración del Simulador

El simulador genera tráfico realista:

- **80%** usuarios existentes (IDs 1-270,000)
- **20%** usuarios nuevos (IDs 300,000-400,000, fallback)
- Rate configurable (req/s)
- Duración configurable

### 4.2. Ejecutar Simulación Básica

```bash
# Instalar dependencia (si no existe)
pip install aiohttp

# Simulación: 10 req/s durante 60 segundos
python scripts/simulate_traffic.py --rate 10 --duration 60
```

**Output esperado:**

```
================================================================================
SIMULADOR DE TRÁFICO - SISTEMA DE RECOMENDACIÓN
================================================================================

⚙️  Configuración:
  Rate: 10.0 req/s
  Duración: 60s (1.0 min)
  Total esperado: ~600 peticiones
  Endpoint: http://localhost:8000

================================================================================

📝 Logs: logs/traffic_simulation_20251208_103000.jsonl
🔍 Verificando API...
✅ API disponible (latency: 45ms)
   Versión del modelo: v1_20251208

🚀 Iniciando simulación...

[100.0%] Requests: 602 | Success: 98.5% | Avg Latency: 123ms | P95: 245ms

⏳ Esperando a que terminen las peticiones pendientes...
✅ Simulación completada

📊 Métricas guardadas: logs/traffic_simulation_20251208_103000.json

================================================================================
RESUMEN DE MÉTRICAS
================================================================================

📊 Peticiones:
  Total:     602
  Exitosas:  593 (98.5%)
  Fallidas:  9
  Rate real: 10.0 req/s

⏱️  Latencia:
  Mínima:    45 ms
  Media:     123 ms
  Mediana:   110 ms
  P95:       245 ms
  P99:       380 ms
  Máxima:    520 ms
  Desv. Est: 67 ms

================================================================================
```

### 4.3. Simulaciones Avanzadas

#### Alta Carga

```bash
# 100 req/s durante 5 minutos
python scripts/simulate_traffic.py --rate 100 --duration 300
```

#### Larga Duración

```bash
# 50 req/s durante 1 hora
python scripts/simulate_traffic.py --rate 50 --duration 3600
```

#### URL Personalizada

```bash
# Probar contra servidor remoto
python scripts/simulate_traffic.py --url http://production-api:8000 --rate 20 --duration 120
```

### 4.4. Análisis de Resultados

Los resultados se guardan en dos formatos:

#### JSONL (Logs Detallados)

```bash
# Ver últimas 10 peticiones
tail -n 10 logs/traffic_simulation_20251208_103000.jsonl | jq .
```

**Formato:**

```json
{
  "timestamp": "2025-12-08T10:30:45.123Z",
  "request": {
    "endpoint": "/recommendations/recommend/12345",
    "params": {"n": 10},
    "user_id": 12345,
    "n": 10
  },
  "response": {
    "success": true,
    "latency": 0.123,
    "status": 200
  }
}
```

#### JSON (Métricas Agregadas)

```bash
# Ver resumen de métricas
cat logs/traffic_simulation_20251208_103000.json | jq .
```

**Formato:**

```json
{
  "configuration": {
    "rate": 10,
    "duration": 60,
    "api_base_url": "http://localhost:8000"
  },
  "execution": {
    "start_time": "2025-12-08T10:30:00Z",
    "end_time": "2025-12-08T10:31:00Z",
    "actual_duration": 60.12
  },
  "requests": {
    "total": 602,
    "successful": 593,
    "failed": 9,
    "success_rate": 98.5,
    "actual_rate": 10.02
  },
  "latency": {
    "min": 0.045,
    "max": 0.520,
    "mean": 0.123,
    "median": 0.110,
    "p50": 0.110,
    "p95": 0.245,
    "p99": 0.380,
    "stdev": 0.067
  },
  "errors": {
    "Timeout": 5,
    "HTTP 503": 4
  }
}
```

### 4.5. Métricas Clave a Monitorear

| Métrica | Valor Objetivo | Acción si se excede |
|---------|----------------|---------------------|
| Success Rate | > 99% | Investigar errores |
| P95 Latency | < 500ms | Optimizar cache/modelo |
| P99 Latency | < 1000ms | Escalar recursos |
| Throughput | Rate solicitado ±5% | Verificar cuellos de botella |

---

## Troubleshooting

### Problema: Modelo no carga en API

**Síntomas:**

```
❌ ERROR: Modelo ALS no encontrado: /app/trained_models/als/model_latest/spark_model
```

**Solución:**

```bash
# 1. Verificar que modelos existen localmente
ls -lh movies/trained_models/als/model_latest

# 2. Verificar volumen montado en contenedor
docker inspect recs-api | jq '.[0].Mounts[] | select(.Destination == "/app/trained_models")'

# 3. Verificar contenido dentro del contenedor
docker exec recs-api ls -lh /app/trained_models/als/

# 4. Reiniciar contenedor
docker restart recs-api
```

### Problema: API devuelve 503 Service Unavailable

**Síntomas:**

```bash
curl http://localhost:8000/recommendations/recommend/123
# {"detail":"Servicio de recomendaciones no disponible"}
```

**Solución:**

```bash
# 1. Ver logs detallados
docker logs recs-api | tail -n 50

# 2. Verificar health check
curl http://localhost:8000/recommendations/health | jq .

# 3. Verificar memoria del contenedor
docker stats recs-api --no-stream

# 4. Si falta memoria, ajustar en docker-compose.yml
# services:
#   api:
#     deploy:
#       resources:
#         limits:
#           memory: 4G
```

### Problema: Latencias altas (>1s)

**Solución:**

```bash
# 1. Verificar tamaño de cache
curl http://localhost:8000/recommendations/health | jq '.cache_stats'

# 2. Aumentar tamaño de cache en recommender_service.py
# CACHE_MAX_SIZE = 5000  # Default: 1000

# 3. Pre-calcular recomendaciones para usuarios más activos
# (Implementación futura)

# 4. Verificar recursos de Spark
# SPARK_MEMORY = "4g"  # En recommender_service.py
```

### Problema: Entrenamiento falla por falta de memoria

**Síntomas:**

```
Exception: Java heap space
```

**Solución:**

```bash
# Editar train_local_all.py
# class Config:
#     SPARK_MEMORY = "4g"  # Reducir de 8g a 4g
#     SPARK_CORES = 2      # Reducir de 4 a 2

# Reducir tamaño del dataset para pruebas
# train_df = train_df.sample(fraction=0.1)  # Solo 10% de datos
```

### Problema: Simulador muestra errores de timeout

**Solución:**

```bash
# 1. Verificar que API está respondiendo
curl http://localhost:8000/recommendations/health

# 2. Reducir rate de peticiones
python scripts/simulate_traffic.py --rate 5 --duration 60

# 3. Aumentar timeout en simulate_traffic.py
# REQUEST_TIMEOUT = 60  # Default: 30

# 4. Verificar recursos del sistema
htop
```

---

## Referencia de APIs

### Endpoints de Recomendaciones

| Endpoint | Método | Descripción | Parámetros |
|----------|--------|-------------|------------|
| `/recommendations/recommend/{user_id}` | GET | Top-N recomendaciones | `n` (int, default=10, max=100), `use_cache` (bool) |
| `/recommendations/predict` | POST | Predecir rating | Body: `{"user_id": int, "movie_id": int}` |
| `/recommendations/similar/{movie_id}` | GET | Películas similares | `n` (int, default=10, max=50) |
| `/recommendations/health` | GET | Health check | - |
| `/recommendations/` | GET | Info del servicio | - |

### Códigos de Estado HTTP

| Código | Significado | Acción |
|--------|-------------|--------|
| 200 | OK | Éxito |
| 400 | Bad Request | Verificar parámetros |
| 404 | Not Found | Usuario/película no existe |
| 500 | Internal Server Error | Ver logs del servidor |
| 503 | Service Unavailable | Modelo no cargado, reiniciar API |

### Formato de Respuestas

Todas las respuestas incluyen:

- `timestamp`: ISO 8601 timestamp
- `model_version`: Versión del modelo usado

#### Recomendaciones

```json
{
  "user_id": 123,
  "recommendations": [
    {
      "movie_id": 318,
      "title": "The Shawshank Redemption (1994)",
      "genres": ["Crime", "Drama"],
      "predicted_rating": 4.85,
      "rank": 1
    }
  ],
  "timestamp": "2025-12-08T10:30:00Z",
  "model_version": "v1_20251208",
  "source": "model"  // "model", "cache", o "fallback_popular"
}
```

#### Predicción

```json
{
  "user_id": 123,
  "movie_id": 456,
  "title": "The Matrix (1999)",
  "genres": ["Action", "Sci-Fi"],
  "predicted_rating": 4.65,
  "timestamp": "2025-12-08T10:30:00Z",
  "model_version": "v1_20251208"
}
```

---

## Próximos Pasos (Roadmap)

### Corto Plazo

- [ ] Pre-cálculo batch de top-N recomendaciones
- [ ] Métricas de negocio en tiempo real (CTR, diversity)
- [ ] A/B testing framework

### Mediano Plazo

- [ ] Reentrenamiento automático (detección de drift)
- [ ] Integración de Item-CF y Content-Based en API
- [ ] Modelo híbrido configurable por usuario

### Largo Plazo

- [ ] Reentrenamiento incremental con datos streaming
- [ ] Serving optimizado con FAISS (ANN search)
- [ ] Multi-tenancy y personalización por contexto

---

## Referencias

- **PySpark MLlib**: https://spark.apache.org/docs/latest/ml-guide.html
- **ALS Algorithm**: https://spark.apache.org/docs/latest/ml-collaborative-filtering.html
- **MovieLens Dataset**: https://grouplens.org/datasets/movielens/

---

**¿Preguntas o problemas?** Ver logs detallados: `docker logs -f recs-api`
