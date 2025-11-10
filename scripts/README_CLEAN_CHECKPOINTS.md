# 🧹 Script de Limpieza de Checkpoints

## Descripción

`clean-checkpoints.sh` es un script que **elimina checkpoints corruptos** de HDFS para solucionar errores de Spark Streaming como:

- ❌ `FileAlreadyExistsException`: Archivos de checkpoint duplicados
- ❌ `SparkConcurrentModificationException`: Múltiples queries usando mismo checkpoint
- ❌ `Checkpoint corrupted`: Estados inconsistentes

---

## 📋 Uso

```bash
./scripts/clean-checkpoints.sh [OPCIÓN]
```

### Opciones

| Opción | Descripción |
|--------|-------------|
| `all` | Limpia **todos** los checkpoints (default) |
| `streaming` | Solo checkpoints del **streaming processor** |
| `latent` | Solo checkpoints del **latent generator** |
| `batch` | Solo checkpoints del **batch analytics** |

---

## 🎯 Ejemplos

### 1. Limpiar todo (recomendado después de errores)
```bash
./scripts/clean-checkpoints.sh all
```

### 2. Solo limpiar streaming processor
```bash
./scripts/clean-checkpoints.sh streaming
```

### 3. Solo limpiar generador latente
```bash
./scripts/clean-checkpoints.sh latent
```

### 4. Ver ayuda
```bash
./scripts/clean-checkpoints.sh help
```

---

## 🔍 ¿Cuándo usar este script?

### Usa `clean-checkpoints.sh` cuando veas estos errores:

**Error 1: FileAlreadyExistsException**
```
rename destination /checkpoints/ratings_stream/processor/raw/offsets/6 already exists
```
✅ Solución: `./scripts/clean-checkpoints.sh streaming`

**Error 2: SparkConcurrentModificationException**
```
Multiple streaming queries are concurrently using hdfs://namenode:9000/checkpoints/...
```
✅ Solución: `./scripts/clean-checkpoints.sh all`

**Error 3: Checkpoint version mismatch**
```
Checkpoint was created with a different version of Spark
```
✅ Solución: `./scripts/clean-checkpoints.sh all`

---

## 📂 Checkpoints que limpia

### Streaming Processor (`streaming`)
- `/checkpoints/ratings_stream/processor/raw` - Raw ratings (HDFS)
- `/checkpoints/ratings_stream/processor/console_debug` - Debug console
- `/checkpoints/ratings_stream/processor/tumbling` - Tumbling window
- `/checkpoints/ratings_stream/processor/sliding` - Sliding window
- `/checkpoints/ratings_stream/processor/metrics_tumbling` - Métricas Kafka
- `/checkpoints/ratings_stream/processor/metrics_sliding` - Métricas Kafka

### Latent Generator (`latent`)
- `/checkpoints/latent_ratings` - Generador sintético

### Batch Analytics (`batch`)
- `/checkpoints/batch_analytics` - Análisis batch

---

## 🚀 Flujo típico después de limpiar

```bash
# 1. Limpiar checkpoints
./scripts/clean-checkpoints.sh all

# 2. Reiniciar sistema (opcional)
./scripts/start-system.sh

# 3. Generar ratings
./scripts/run-latent-generator.sh 100

# 4. Procesar streaming
./scripts/run-streaming-processor.sh

# 5. Analizar batch
./scripts/run-batch-analytics.sh
```

---

## ⚠️ Advertencias

- ⚠️ **Perderás el estado de las queries**: Volverán a procesar desde offset inicial
- ⚠️ **Detén las queries antes**: No limpies checkpoints mientras hay queries corriendo
- ⚠️ **Backup opcional**: Si necesitas el estado, haz backup antes

---

## 🔧 Verificación manual

Ver checkpoints actuales:
```bash
docker exec namenode hadoop fs -ls -R /checkpoints
```

Limpiar manualmente un checkpoint específico:
```bash
docker exec namenode hadoop fs -rm -r -f /checkpoints/ratings_stream/processor/raw
```

---

## 📊 Salida del script

El script muestra:
- ✅ Checkpoints eliminados correctamente
- ℹ️ Checkpoints que no existían (normal)
- ❌ Errores si HDFS no está disponible
- 📋 Estructura final de checkpoints
- 🚀 Próximos pasos recomendados
