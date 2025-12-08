# 📦 Guía: Importar Modelo ALS desde Kaggle

Guía paso a paso para descargar, extraer y usar modelos entrenados en Kaggle.

---

## 🎯 Opción 1: Usar el Script Automático (RECOMENDADO)

### Paso 1: Descargar el modelo de Kaggle

Después de entrenar en Kaggle:
1. Ve a **Output** en el panel derecho
2. Busca el archivo `.tar.gz` (ej: `als_model_v1_20251208_143022.tar.gz`)
3. Descárgalo a tu carpeta de Descargas

### Paso 2: Ejecutar el script de importación

```bash
cd /home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala

# Opción A: Dejar que el script asigne el nombre automáticamente
./scripts/import_kaggle_model.sh ~/Downloads/als_model_v1_20251208.tar.gz

# Opción B: Especificar un nombre personalizado
./scripts/import_kaggle_model.sh ~/Downloads/als_model.tar.gz model_kaggle_produccion
```

**¡Listo!** El script hace todo automáticamente:
- ✅ Extrae el modelo
- ✅ Lo mueve a `movies/trained_models/als/`
- ✅ Crea symlink `model_latest`
- ✅ Verifica la estructura
- ✅ Te muestra cómo usarlo

### Paso 3: Usar el modelo

```python
from pyspark.sql import SparkSession
from movies.src.recommendation.models.als_model import ALSRecommender

spark = SparkSession.builder \
    .appName("Recommendations") \
    .config("spark.driver.memory", "4g") \
    .getOrCreate()

# Cargar modelo (usa automáticamente el más reciente)
recommender = ALSRecommender(
    spark,
    model_path="movies/trained_models/als/model_latest"
)

# Generar recomendaciones
recommendations = recommender.recommend_for_user(user_id=123, n=10)

for rec in recommendations:
    print(f"Película {rec['movieId']}: Score {rec['score']:.2f}")
```

---

## 🔧 Opción 2: Manual (Paso a Paso)

Si prefieres hacerlo manualmente:

### Paso 1: Preparar el directorio

```bash
cd /home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala

# Verificar que existe el directorio
ls movies/trained_models/als/
```

### Paso 2: Copiar el archivo .tar.gz

```bash
# Copiar desde Descargas
cp ~/Downloads/als_model_v1_20251208.tar.gz movies/trained_models/als/
```

### Paso 3: Extraer el modelo

```bash
cd movies/trained_models/als/

# Extraer
tar -xzf als_model_v1_20251208.tar.gz

# Verificar
ls -l
```

Deberías ver algo como:
```
drwxrwxr-x als_model_v1_20251208/
-rw-rw-r-- als_model_v1_20251208.tar.gz
```

### Paso 4: Crear symlink model_latest

```bash
# Crear o actualizar symlink
ln -sf als_model_v1_20251208 model_latest

# Verificar
ls -l model_latest
# Debería mostrar: model_latest -> als_model_v1_20251208
```

### Paso 5: Verificar estructura del modelo

```bash
cd model_latest

# Verificar archivos necesarios
ls -la
```

Debe contener al menos:
```
spark_model/          # Modelo de Spark (REQUERIDO)
metadata.json         # Metadatos (opcional pero recomendado)
metrics.json          # Métricas de evaluación (opcional)
```

### Paso 6: Limpiar archivo .tar.gz (opcional)

```bash
cd ..
rm als_model_v1_20251208.tar.gz
```

---

## 🚀 Ejemplos de Uso

### Ejemplo 1: Recomendaciones simples

```python
from movies.src.recommendation.models.als_model import ALSRecommender
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("Test").getOrCreate()

# Cargar modelo
recommender = ALSRecommender(
    spark,
    model_path="movies/trained_models/als/model_latest"
)

# Top-10 para usuario
recs = recommender.recommend_for_user(user_id=123, n=10)
print(recs)
```

### Ejemplo 2: Predecir rating específico

```python
# ¿Qué rating daría el usuario 123 a la película 456?
rating = recommender.predict_rating(user_id=123, movie_id=456)
print(f"Rating predicho: {rating:.2f}/5.0")
```

### Ejemplo 3: Batch predictions

```python
# Predecir para múltiples pares usuario-película
pairs = [(123, 456), (123, 789), (456, 123)]
predictions_df = recommender.batch_predict(pairs)
predictions_df.show()
```

### Ejemplo 4: Usar el script de ejemplo

```bash
# Ejecutar ejemplo completo
python movies/src/recommendation/example_usage.py
```

---

## 📊 Gestión de Versiones

### Ver modelos disponibles

```bash
ls -lh movies/trained_models/als/
```

Ejemplo de salida:
```
drwxrwxr-x als_model_v1_20251208/
drwxrwxr-x als_model_v2_20251209/
lrwxrwxrwx model_latest -> als_model_v2_20251209
```

### Cambiar a otra versión

```bash
cd movies/trained_models/als/

# Cambiar symlink a versión anterior
ln -sf als_model_v1_20251208 model_latest
```

### Eliminar versiones antiguas

```bash
# Eliminar una versión específica
rm -rf movies/trained_models/als/als_model_v1_20251208/

# Mantener solo las últimas 3 versiones
cd movies/trained_models/als/
ls -t | grep als_model_v | tail -n +4 | xargs rm -rf
```

---

## 🔍 Verificación y Troubleshooting

### Verificar que el modelo está correcto

```bash
# Ver metadatos
cat movies/trained_models/als/model_latest/metadata.json | python -m json.tool

# Verificar estructura de Spark
ls movies/trained_models/als/model_latest/spark_model/
```

### Problemas comunes

#### ❌ Error: "FileNotFoundError: No such file or directory"

**Causa**: La ruta del modelo es incorrecta

**Solución**:
```bash
# Verificar ruta absoluta
pwd
ls movies/trained_models/als/model_latest/
```

Usar ruta absoluta en Python:
```python
model_path = "/home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala/movies/trained_models/als/model_latest"
```

#### ❌ Error: "Symlink is broken"

**Causa**: El symlink apunta a un directorio que no existe

**Solución**:
```bash
cd movies/trained_models/als/
rm model_latest
ln -sf als_model_v1_20251208 model_latest
```

#### ❌ Error: "Model files are corrupted"

**Causa**: El archivo .tar.gz no se descargó completamente o está corrupto

**Solución**:
1. Volver a descargar desde Kaggle
2. Verificar tamaño del archivo
3. Volver a extraer

---

## 📁 Estructura Final Esperada

```
movies/trained_models/als/
├── als_model_v1_20251208/          # Modelo descargado de Kaggle
│   ├── spark_model/                # Modelo Spark MLlib
│   │   ├── data/
│   │   ├── metadata/
│   │   └── itemFactors/
│   ├── metadata.json               # Info del entrenamiento
│   ├── metrics.json                # RMSE, MAE, etc.
│   └── checksum.txt                # Validación
├── als_model_v2_20251209/          # Versión más reciente
│   └── ...
├── model_latest -> als_model_v2_20251209  # Symlink al más reciente
└── .gitkeep                        # Mantiene directorio en Git
```

---

## 💡 Tips Avanzados

### Tip 1: Automatizar descarga desde Kaggle API

```bash
# Instalar Kaggle CLI
pip install kaggle

# Configurar credenciales (~/.kaggle/kaggle.json)
kaggle kernels output <tu-usuario>/<notebook-name> -p ~/Downloads/

# Importar automáticamente
./scripts/import_kaggle_model.sh ~/Downloads/als_model_*.tar.gz
```

### Tip 2: Usar variables de entorno

```python
import os

MODEL_PATH = os.environ.get(
    'ALS_MODEL_PATH',
    'movies/trained_models/als/model_latest'
)

recommender = ALSRecommender(spark, model_path=MODEL_PATH)
```

### Tip 3: Validar modelo antes de usar

```python
def validate_model(model_path):
    """Valida que el modelo tiene la estructura correcta"""
    import os
    
    required_files = [
        'spark_model',
        'metadata.json'
    ]
    
    for file in required_files:
        path = os.path.join(model_path, file)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Falta archivo: {file}")
    
    print("✓ Modelo válido")

# Usar
validate_model("movies/trained_models/als/model_latest")
```

---

## 📞 Soporte

Si tienes problemas:

1. Verifica la estructura con: `ls -la movies/trained_models/als/model_latest/`
2. Revisa los logs de Spark
3. Ejecuta el ejemplo: `python movies/src/recommendation/example_usage.py`
4. Consulta el README principal: `movies/src/recommendation/README.md`

---

**Última actualización**: Diciembre 2025  
**Mantenido por**: Sistema de Recomendación PGVD
