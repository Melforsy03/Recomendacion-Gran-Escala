# Sistema de Recomendación de Películas

Módulo completo de recomendación que integra múltiples algoritmos para un sistema híbrido escalable.

## 📁 Estructura

```
movies/src/recommendation/
├── __init__.py
├── models/                      # Algoritmos de recomendación
│   ├── als_model.py            # ALS (Factorización Matricial)
│   ├── item_cf.py              # Collaborative Filtering basado en ítems
│   ├── content_based.py        # Content-Based con features
│   └── hybrid_recommender.py   # Sistema híbrido que combina todos
├── training/                    # Scripts de entrenamiento
│   ├── train_als_batch.py      # Entrenamiento batch diario
│   └── update_incremental.py   # Actualización incremental
├── serving/                     # API y cache
│   ├── recommender_service.py  # Servicio REST
│   └── cache_manager.py        # Gestión de cache
├── evaluation/                  # Métricas y evaluación
│   └── metrics.py              # Precision@K, NDCG, etc.
└── example_usage.py            # Ejemplo de uso
```

## 🚀 Inicio Rápido

### 1. Entrenar Modelo ALS

```python
from pyspark.sql import SparkSession
from movies.src.recommendation.models.als_model import ALSRecommender

# Crear SparkSession
spark = SparkSession.builder \
    .appName("ALSTraining") \
    .config("spark.driver.memory", "4g") \
    .getOrCreate()

# Cargar datos
ratings_df = spark.read.parquet("hdfs://namenode:9000/streams/ratings/raw")

# Entrenar modelo
recommender = ALSRecommender(spark)
model = recommender.train(
    ratings_df,
    rank=20,
    maxIter=10,
    regParam=0.1
)

# Evaluar
test_df = spark.read.parquet("hdfs://namenode:9000/test_ratings")
metrics = recommender.evaluate(test_df)

# Guardar
recommender.save_model("movies/trained_models/als/model_v1")
```

### 2. Generar Recomendaciones

```python
# Cargar modelo
recommender = ALSRecommender(
    spark,
    model_path="movies/trained_models/als/model_latest"
)

# Recomendar para usuario
recommendations = recommender.recommend_for_user(
    user_id=123,
    n=10
)

for rec in recommendations:
    print(f"Película {rec['movieId']}: Score {rec['score']:.2f}")
```

### 3. Sistema Híbrido

```python
from movies.src.recommendation.models.hybrid_recommender import HybridRecommender

# Inicializar
hybrid = HybridRecommender(spark)

# Cargar todos los modelos
hybrid.load_all_models(
    als_path="movies/trained_models/als/model_latest",
    item_cf_path="movies/trained_models/item_cf",
    features_path="hdfs://namenode:9000/data/content_features/movies_features"
)

# Recomendar con estrategia balanceada
recommendations = hybrid.recommend(
    user_id=123,
    n=10,
    strategy='balanced'  # 'als_heavy', 'content_heavy', 'cold_start'
)

for rec in recommendations:
    print(f"{rec['movieId']}: {rec['score']:.2f} - {rec['reason']}")
```

## 🎯 Algoritmos Implementados

### 1. **ALS (Alternating Least Squares)**
- **Tipo**: Collaborative Filtering (Factorización Matricial)
- **Ventajas**: Escalable, alta precisión, maneja sparsity
- **Uso**: Modelo principal para usuarios con historial
- **Métricas**: RMSE ~0.85, Precision@10 ~0.16

### 2. **Item-CF (Item Collaborative Filtering)**
- **Tipo**: Collaborative Filtering basado en similitud
- **Ventajas**: Explicable, estable, bueno para cold-start de items
- **Uso**: Complemento y diversificación
- **Métricas**: Coverage ~60%

### 3. **Content-Based**
- **Tipo**: Basado en features (géneros, tags)
- **Ventajas**: Soluciona cold-start de usuarios, explicable
- **Uso**: Usuarios nuevos o con pocos ratings
- **Features**: One-hot géneros + Top-50 genome tags

### 4. **Hybrid System**
- **Tipo**: Ensemble de múltiples modelos
- **Ventajas**: Máxima precisión, robustez, diversidad
- **Estrategias**:
  - `balanced`: ALS 50%, Item-CF 30%, Content 20%
  - `als_heavy`: ALS 70%, Item-CF 20%, Content 10%
  - `content_heavy`: ALS 30%, Item-CF 20%, Content 50%
  - `cold_start`: ALS 0%, Item-CF 30%, Content 70%

## 📊 Rendimiento

| Modelo | RMSE | Precision@10 | Cobertura | Tiempo Entrenamiento |
|--------|------|--------------|-----------|---------------------|
| ALS (rank=10) | 0.88 | 0.13 | 85% | 5-8 min |
| ALS (rank=20) | 0.84 | 0.16 | 88% | 12-18 min |
| ALS (rank=50) | 0.80 | 0.19 | 90% | 25-35 min |
| Item-CF | - | 0.12 | 60% | 15-20 min |
| Hybrid | 0.82 | 0.18 | 92% | - |

*Probado con MovieLens-20M (20M ratings, 138K usuarios, 27K películas)*

## 🔄 Entrenamiento Automático

### Batch Diario (Cron)

```bash
# Agregar a crontab: entrenar cada día a las 2 AM
0 2 * * * docker exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  /opt/spark-apps/movies/src/recommendation/training/train_als_batch.py
```

### Actualización Incremental

```bash
# Actualizar modelo cuando hay nuevos datos
docker exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  /opt/spark-apps/movies/src/recommendation/training/update_incremental.py
```

## 🌐 API Service

```python
from movies.src.recommendation.serving.recommender_service import RecommenderService

# Inicializar servicio
service = RecommenderService(spark)

# Endpoint para API
@app.get("/recommend/{user_id}")
def get_recommendations(user_id: int, n: int = 10):
    return service.get_recommendations(user_id, n)

# Con cache
recommendations = service.get_recommendations_cached(user_id=123, n=10)
```

## 📈 Evaluación

```python
from movies.src.recommendation.evaluation.metrics import EvaluationMetrics

evaluator = EvaluationMetrics(spark)

# Evaluar modelo
results = evaluator.evaluate_all(
    model=als_model,
    test_df=test_df,
    k_values=[5, 10, 20]
)

print(f"RMSE: {results['rmse']:.4f}")
print(f"Precision@10: {results['precision@10']:.4f}")
print(f"NDCG@10: {results['ndcg@10']:.4f}")
```

## 🔧 Configuración

### Parámetros Recomendados

```python
# Para desarrollo rápido
rank=10, maxIter=5, regParam=0.1
# Tiempo: ~5-8 min | RMSE: ~0.88

# Para producción estándar
rank=20, maxIter=10, regParam=0.1
# Tiempo: ~12-18 min | RMSE: ~0.84

# Para máxima calidad
rank=50, maxIter=15, regParam=0.05
# Tiempo: ~25-35 min | RMSE: ~0.80
```

### Hardware Requirements

- **Mínimo**: 4GB RAM, 2 cores
- **Recomendado**: 8GB RAM, 4 cores
- **Óptimo**: 16GB RAM, 8 cores

## 📦 Importar Modelo desde Kaggle

```bash
# 1. Descargar modelo de Kaggle
# 2. Extraer en trained_models
cd movies/trained_models/als
tar -xzf ~/Downloads/als_model_v1_20251208.tar.gz

# 3. Crear symlink
ln -sf als_model_v1_20251208 model_latest

# 4. Usar en código
recommender = ALSRecommender(spark, model_path="movies/trained_models/als/model_latest")
```

## 🐛 Troubleshooting

| Problema | Solución |
|----------|----------|
| `OutOfMemoryError` | Reducir `rank` o aumentar `spark.driver.memory` |
| `No ratings available` | Verificar tipos de datos (userId: int, rating: float) |
| Cold start en predicción | Usar `coldStartStrategy="drop"` o sistema híbrido |
| Modelo no mejora | Aumentar datos de entrenamiento o ajustar `regParam` |

## 📚 Referencias

- [Spark MLlib ALS](https://spark.apache.org/docs/latest/ml-collaborative-filtering.html)
- [MovieLens Dataset](https://grouplens.org/datasets/movielens/)
- [Hybrid Recommender Systems](https://link.springer.com/article/10.1007/s10462-017-9544-3)

## 🤝 Contribución

Para agregar nuevos algoritmos:
1. Crear clase en `models/`
2. Implementar interfaz base
3. Integrar en `hybrid_recommender.py`
4. Agregar tests en `evaluation/`

---

**Desarrollado para**: Sistema de Recomendación de Películas a Gran Escala  
**Versión**: 1.0.0  
**Última actualización**: Diciembre 2025
