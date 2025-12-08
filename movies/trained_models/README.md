# Modelos Entrenados

Este directorio almacena los modelos de recomendación entrenados.

## 📁 Estructura

```
trained_models/
├── als/                    # Modelos ALS (Spark MLlib)
│   ├── model_v1_20251208/
│   ├── model_v2_20251209/
│   └── model_latest -> model_v2_20251209
├── item_cf/                # Matrices de similitud Item-CF
│   └── similarity_matrix/
└── content_based/          # Features de contenido
    └── movie_features/
```

## 🚀 Uso

### Cargar Modelo ALS

```python
from movies.src.recommendation.models.als_model import ALSRecommender

recommender = ALSRecommender(
    spark,
    model_path="movies/trained_models/als/model_latest"
)

recommendations = recommender.recommend_for_user(user_id=123, n=10)
```

### Importar Modelo de Kaggle

1. Descargar modelo desde Kaggle (archivo `.tar.gz`)
2. Extraer en `trained_models/als/`:
   ```bash
   cd movies/trained_models/als
   tar -xzf ~/Downloads/als_model_v1_*.tar.gz
   ```
3. Crear symlink a `model_latest`:
   ```bash
   ln -sf als_model_v1_20251208 model_latest
   ```

## 📦 Convenciones de Nombrado

- **ALS**: `als_model_v{version}_{YYYYMMDD}_{HHMMSS}`
- **Item-CF**: `similarity_matrix_{YYYYMMDD}`
- **Symlink**: Siempre mantener `model_latest` apuntando al modelo más reciente

## 🔄 Versionado

Los modelos se versionan automáticamente con:
- Número de versión incremental
- Timestamp de entrenamiento
- Métricas de evaluación (en `metrics.json`)

## 🗑️ Limpieza

Para mantener solo las últimas 5 versiones:

```bash
# Script automático en training/cleanup_old_models.sh
./scripts/cleanup_old_models.sh --keep 5
```

## 📊 Metadatos

Cada modelo incluye:
- `metrics.json`: RMSE, MAE, Precision@K, etc.
- `model_info.txt`: Parámetros de entrenamiento
- `checksum.md5`: Validación de integridad
