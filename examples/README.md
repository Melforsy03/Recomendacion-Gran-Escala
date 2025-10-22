# Ejemplos de uso del sistema

Este directorio contiene ejemplos de código para trabajar con el sistema de Big Data.

## Archivos

### 1. batch_processing.py
Ejemplo de procesamiento batch con Spark. Muestra cómo:
- Crear DataFrames
- Realizar agregaciones
- Calcular estadísticas
- Guardar resultados en HDFS

**Ejecución:**
```bash
# Copiar al contenedor
docker cp batch_processing.py spark-master:/tmp/

# Ejecutar
docker exec spark-master spark-submit \
    --master spark://spark-master:7077 \
    /tmp/batch_processing.py
```

### 2. streaming_recommendation.py
Ejemplo de Spark Streaming con Kafka. Muestra cómo:
- Leer datos desde Kafka en tiempo real
- Procesar streams con ventanas de tiempo
- Detectar items trending
- Calcular estadísticas en tiempo real

**Ejecución:**
```bash
# 1. Crear el topic en Kafka
docker exec kafka kafka-topics --create \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 3 \
    --topic ratings

# 2. Copiar al contenedor
docker cp streaming_recommendation.py spark-master:/tmp/

# 3. Ejecutar (con -u root para descargar dependencias de Maven)
docker exec -u root spark-master spark-submit \
    --master spark://spark-master:7077 \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1 \
    /tmp/streaming_recommendation.py
```

### 3. kafka_producer.py
Productor de datos simulados para Kafka. Genera ratings aleatorios para testing.

**Ejecución:**
```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python kafka_producer.py
```

## Flujo de trabajo completo

### Opción 1: Procesamiento Batch

```bash
# 1. Ejecutar el procesamiento batch
docker cp batch_processing.py spark-master:/tmp/
docker exec spark-master spark-submit \
    --master spark://spark-master:7077 \
    /tmp/batch_processing.py
```

### Opción 2: Streaming en tiempo real

```bash
# Terminal 1: Iniciar el consumidor Spark Streaming
docker cp streaming_recommendation.py spark-master:/tmp/
docker exec spark-master spark-submit \
    --master spark://spark-master:7077 \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1 \
    /tmp/streaming_recommendation.py

# Terminal 2: Ejecutar el productor de datos
pip install -r requirements.txt
python kafka_producer.py
```

## Formato de datos

Los ejemplos esperan datos en formato JSON:

```json
{
    "user_id": "user1",
    "item_id": "item1",
    "rating": 4.5,
    "timestamp": "2025-10-22T10:00:00.000Z"
}
```

## Personalización

Puedes modificar estos ejemplos para:
- Cambiar el esquema de datos
- Añadir más análisis
- Integrar con tu modelo de recomendación
- Guardar resultados en diferentes formatos
- Implementar diferentes algoritmos

## Próximos pasos

1. Ejecuta los ejemplos para familiarizarte con el sistema
2. Modifica el código según tus necesidades
3. Implementa tu propio modelo de recomendación
4. Integra con fuentes de datos reales
