# Scripts - Sistema de Recomendación

Colección de scripts para entrenar, desplegar y probar el sistema de recomendación.

---

## 📋 Scripts Disponibles

### 🎯 Entrenamiento

#### `train_all_models.sh`
Entrena todos los modelos de recomendación localmente (omite existentes).

**Uso:**
```bash
# Entrena solo modelos faltantes (default)
./scripts/train_all_models.sh

# Forzar re-entrenamiento de todos
./scripts/train_all_models.sh --force

# Entrenar modelos específicos
./scripts/train_all_models.sh --models=ALS,ITEM_CF
```

**Características:**
- ✅ Crea entorno virtual automáticamente
- ✅ Instala dependencias (PySpark, pandas, numpy)
- ✅ **Omite modelos ya entrenados** (usa `--force` para re-entrenar)
- ✅ Entrena ALS, Item-CF, Content-Based, Hybrid
- ✅ Versiona modelos con timestamps
- ✅ Actualiza symlinks `model_latest`

**Tiempo:** 30-60 minutos (primera vez), < 1 minuto (si ya existen)

**Output:** `movies/trained_models/{als,item_cf,content_based,hybrid}/`

---

### 🚀 Despliegue

#### `copy_models_to_containers.sh`
Verifica volúmenes montados y reinicia API para cargar modelos.

**Uso:**
```bash
./scripts/copy_models_to_containers.sh
```

**Características:**
- ✅ Verifica modelos locales
- ✅ Verifica volúmenes Docker
- ✅ Reinicia contenedor API
- ✅ Espera a que servicio esté ready
- ✅ Verifica health check

**Nota:** Los modelos se montan automáticamente via volúmenes, no se copian manualmente.

---

### 🧪 Pruebas

#### `simulate_traffic.py`
Simula tráfico HTTP realista para pruebas de carga.

**Uso básico:**
```bash
# 10 req/s durante 60 segundos
python scripts/simulate_traffic.py --rate 10 --duration 60
```

**Uso avanzado:**
```bash
# Alta carga: 100 req/s durante 5 minutos
python scripts/simulate_traffic.py --rate 100 --duration 300

# Larga duración: 50 req/s durante 1 hora
python scripts/simulate_traffic.py --rate 50 --duration 3600

# URL personalizada
python scripts/simulate_traffic.py --url http://api:8000 --rate 20 --duration 120
```

**Output:**
- Logs detallados: `logs/traffic_simulation_TIMESTAMP.jsonl`
- Métricas agregadas: `logs/traffic_simulation_TIMESTAMP.json`

**Métricas reportadas:**
- Total de peticiones
- Success rate
- Latencias (min, mean, p50, p95, p99, max)
- Throughput real
- Errores por tipo

---

## 🔄 Workflow Completo

### 1. Entrenar Modelos
```bash
./scripts/train_all_models.sh
```

### 2. Iniciar Sistema Docker
```bash
docker-compose up -d
```

### 3. Verificar Deployment
```bash
./scripts/copy_models_to_containers.sh
```

### 4. Probar API
```bash
# Health check
curl http://localhost:8000/recommendations/health

# Recomendaciones
curl "http://localhost:8000/recommendations/recommend/123?n=10"
```

### 5. Simular Tráfico
```bash
python scripts/simulate_traffic.py --rate 50 --duration 300
```

---

## 📊 Análisis de Logs

### Ver logs de entrenamiento
```bash
# Logs del script
cat .venv-training/training.log

# Métricas del modelo
cat movies/trained_models/als/model_latest/metadata.json | jq .metrics
```

### Ver logs de API
```bash
# Logs en tiempo real
docker logs -f recs-api

# Últimas 50 líneas
docker logs recs-api --tail 50

# Buscar errores
docker logs recs-api | grep ERROR
```

### Analizar resultados de simulación
```bash
# Ver resumen
cat logs/traffic_simulation_*.json | jq '.requests, .latency'

# Ver peticiones fallidas
cat logs/traffic_simulation_*.jsonl | jq 'select(.response.success == false)'

# Calcular percentiles
cat logs/traffic_simulation_*.jsonl | jq '.response.latency' | sort -n
```

---

## 🔧 Configuración

### Parámetros de Entrenamiento

Editar `movies/src/recommendation/training/train_local_all.py`:

```python
class Config:
    # Spark
    SPARK_MEMORY = "8g"        # Ajustar según RAM
    SPARK_CORES = 4            # Ajustar según CPU
    
    # ALS
    ALS_RANK = 20              # Dimensiones latentes
    ALS_MAX_ITER = 10          # Iteraciones
    ALS_REG_PARAM = 0.1        # Regularización
    
    # Split
    TRAIN_RATIO = 0.8          # 80% train, 20% test
```

### Parámetros de API

Editar `movies/api/services/recommender_service.py`:

```python
class RecommenderConfig:
    # Cache
    CACHE_MAX_SIZE = 1000      # Usuarios en cache
    CACHE_TTL_HOURS = 1        # TTL en horas
    
    # Spark
    SPARK_MEMORY = "2g"        # Memoria para Spark local
    SPARK_CORES = 2            # Cores para Spark local
    
    # Fallback
    TOP_POPULAR_N = 100        # Películas populares
```

### Parámetros de Simulador

Editar `scripts/simulate_traffic.py`:

```python
class Config:
    # Distribución
    EXISTING_USERS_RATIO = 0.8  # 80% usuarios existentes
    NEW_USERS_RATIO = 0.2        # 20% nuevos (fallback)
    
    # Rango de IDs
    MIN_USER_ID = 1
    MAX_USER_ID = 270_000
    
    # Timeouts
    REQUEST_TIMEOUT = 30         # Segundos
```

---

## ⚠️ Troubleshooting

### Script de entrenamiento falla

```bash
# Verificar Java
java -version

# Verificar memoria
free -h

# Verificar datos
ls -lh Dataset/rating.csv

# Reducir memoria si es necesario
# Editar SPARK_MEMORY en train_local_all.py
```

### API no carga modelos

```bash
# Verificar modelos existen
ls -lh movies/trained_models/*/model_latest

# Verificar volumen montado
docker inspect recs-api | jq '.[0].Mounts'

# Verificar logs
docker logs recs-api | grep "INICIALIZANDO"

# Reiniciar
docker restart recs-api
```

### Simulador muestra timeouts

```bash
# Verificar API
curl http://localhost:8000/recommendations/health

# Reducir rate
python scripts/simulate_traffic.py --rate 5 --duration 60

# Verificar recursos
docker stats recs-api
```

---

## 📚 Documentación Completa

Ver: [`docs/GUIA_ENTRENAMIENTO_DESPLIEGUE.md`](../docs/GUIA_ENTRENAMIENTO_DESPLIEGUE.md)

---

## 🎯 Métricas Objetivo

| Métrica | Objetivo | Script |
|---------|----------|--------|
| RMSE (ALS) | < 0.85 | `train_all_models.sh` |
| Success Rate | > 99% | `simulate_traffic.py` |
| P95 Latency | < 500ms | `simulate_traffic.py` |
| Throughput | Rate solicitado ±5% | `simulate_traffic.py` |

---

**Última actualización:** 8 de diciembre de 2025
