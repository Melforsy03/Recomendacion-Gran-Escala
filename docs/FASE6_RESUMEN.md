# FASE 6: Topics Kafka y Esquema de Eventos - RESUMEN

## 📋 Información General

- **Fase**: 6 - Topics Kafka y Esquema de Eventos
- **Fecha de Ejecución**: 29 de octubre de 2025
- **Duración**: ~5 minutos (incluyendo pruebas)
- **Estado**: ✅ COMPLETADA Y VERIFICADA

---

## 🎯 Objetivos

1. **Crear topics Kafka** para streaming de ratings y métricas
2. **Definir esquema JSON** para eventos de ratings
3. **Implementar producer hello world** para envío de eventos
4. **Implementar consumer hello world** para consumo y validación
5. **Verificar infraestructura** de streaming completa

---

## 🛠️ Implementación

### 1. Topics Creados

#### Topic: `ratings` (Input)
```yaml
Propósito: Recibir ratings de usuarios en tiempo real
Particiones: 6
Replication Factor: 1
Retention: 7 días (604800000 ms)
Compression: LZ4
Key: userId (para particionamiento consistente)
```

#### Topic: `metrics` (Output)
```yaml
Propósito: Publicar métricas de streaming
Particiones: 3
Replication Factor: 1
Retention: 30 días (2592000000 ms)
Compression: GZIP
```

### 2. Esquema JSON de Eventos

**Estructura del evento `ratings`**:
```json
{
  "userId": 44176,
  "movieId": 21373,
  "rating": 3.5,
  "timestamp": 1761763121809
}
```

**Validaciones implementadas**:
- `userId`: int > 0, rango 1-138,493
- `movieId`: int > 0, rango 1-131,262
- `rating`: double ∈ {0.5, 1.0, 1.5, ..., 5.0}
- `timestamp`: long > 0 (Unix epoch en milisegundos)

### 3. Archivos Implementados

```
movies/src/streaming/
├── create_kafka_topics.py          # 340 líneas - Creación y validación de topics
├── kafka_producer_hello.py         # 280 líneas - Producer de prueba
├── kafka_consumer_hello.py         # 335 líneas - Consumer con validación
└── README_FASE6.md                 # 450 líneas - Documentación completa

scripts/
└── verify_kafka_phase6.sh          # 180 líneas - Script de verificación

requirements.txt                     # +kafka-python>=2.0.2
```

### 4. Características del Producer

**Archivo**: `kafka_producer_hello.py`

- ✅ Generación de ratings sintéticos aleatorios
- ✅ Validación de esquema antes de enviar
- ✅ Particionamiento por `userId` (key)
- ✅ Compresión LZ4
- ✅ Acks='all' para confiabilidad
- ✅ Estadísticas de envío (throughput, éxito/fallo)
- ✅ CLI con argumentos `--count` y `--delay`

**Ejemplo de uso**:
```bash
python3 kafka_producer_hello.py --count 10 --delay 0.3
```

### 5. Características del Consumer

**Archivo**: `kafka_consumer_hello.py`

- ✅ Consumo desde topic `ratings`
- ✅ Validación de esquema en mensajes recibidos
- ✅ Estadísticas detalladas (válidos/inválidos)
- ✅ Distribución de ratings visualizada
- ✅ Consumer group para tracking de offsets
- ✅ Signal handling (Ctrl+C graceful)
- ✅ CLI con `--max-messages`, `--timeout`, `--reset`

**Ejemplo de uso**:
```bash
python3 kafka_consumer_hello.py --max-messages 10 --timeout 10
```

---

## ✅ Resultados de Verificación

### Prueba Producer (10 mensajes)

```
======================================================================
📊 RESUMEN DE ENVÍO
======================================================================

✅ Mensajes enviados: 10
❌ Mensajes fallidos: 0
📈 Total: 10
⏱️  Tiempo total: 2.76 segundos
🚀 Throughput: 3.63 mensajes/seg
✓  Tasa de éxito: 100.0%
```

**Distribución por partición**:
- Partition 0: 3 mensajes (offsets 0-2)
- Partition 2: 2 mensajes (offsets 0-1)
- Partition 3: 1 mensaje (offset 0)
- Partition 4: 3 mensajes (offsets 0-2)
- Partition 5: 1 mensaje (offset 0)

### Prueba Consumer (10 mensajes)

```
======================================================================
📊 RESUMEN DE CONSUMO
======================================================================

📈 Mensajes procesados:
   Total: 10
   Válidos: 10 (100.0%)
   Inválidos: 0
   Errores de deserialización: 0
   Errores de procesamiento: 0

⏱️  Duración: 3.29 segundos
🚀 Throughput: 3.04 mensajes/seg

⭐ Distribución de ratings:
   0.5: █ (1)    1.0: █ (1)    1.5: ██ (2)
   2.0: █ (1)    3.5: █ (1)    4.0: █ (1)
   4.5: ██ (2)   5.0: █ (1)
```

### Verificación de Offsets

**Consumer Group**: `ratings-consumer-hello-world`

```
PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
0          3               3               0
1          0               0               0
2          2               2               0
3          1               1               0
4          3               3               0
5          1               1               0

Total LAG: 0 (todos los mensajes consumidos)
```

---

## 📊 Métricas de Performance

| Métrica | Producer | Consumer |
|---------|----------|----------|
| **Mensajes procesados** | 10 | 10 |
| **Duración** | 2.76 s | 3.29 s |
| **Throughput** | 3.63 msg/s | 3.04 msg/s |
| **Tasa de éxito** | 100% | 100% |
| **Errores** | 0 | 0 |
| **Latencia end-to-end** | ~3 segundos | - |

---

## 🔧 Dependencias Instaladas

### Python Packages (Spark containers)

```bash
pip install kafka-python>=2.0.2  # Cliente Kafka para Python
pip install lz4>=4.3.3           # Compresión LZ4
pip install python-snappy        # Compresión Snappy
```

**Instalación ejecutada**:
```bash
docker exec -u root spark-master pip install kafka-python lz4 python-snappy
docker exec -u root spark-worker pip install kafka-python lz4 python-snappy
```

---

## 🎓 Lecciones Aprendidas

### 1. Librerías de Compresión

**Problema encontrado**:
```
❌ Error creando producer: Libraries for lz4 compression codec not found
```

**Solución**:
- Instalar `lz4` y `python-snappy` además de `kafka-python`
- Las librerías de compresión no vienen incluidas por defecto
- Necesarias para producer con `compression_type='lz4'`

### 2. Particionamiento Consistente

- Uso de `userId` como **key** del mensaje
- Garantiza que ratings del mismo usuario vayan a la misma partición
- Facilita procesamiento con estado (stateful streaming)
- Permite paralelismo sin conflictos de usuarios

### 3. Validación de Esquema

- **Doble validación**: producer (antes de enviar) + consumer (al recibir)
- Previene mensajes malformados en el topic
- **Resultado**: 100% de mensajes válidos en pruebas
- Rating con incrementos de 0.5 evita valores inválidos como 3.7 o 4.3

### 4. Consumer Group Offsets

- Consumer group automáticamente rastrea offsets
- Permite reanudar consumo desde última posición
- LAG=0 indica que todos los mensajes fueron consumidos
- Útil para monitoreo y troubleshooting

### 5. Topics Pre-existentes

- Topics ya existían de ejecución anterior
- `TopicAlreadyExistsError` es esperado, no fatal
- Configuraciones pueden diferir (6 vs 3 particiones para `ratings`)
- En producción: usar scripts idempotentes

---

## 🚀 Próximos Pasos - Fase 7

### Spark Structured Streaming para Recomendaciones

**Objetivo**: Consumir ratings en tiempo real y generar recomendaciones usando modelo ALS de Fase 5

**Componentes a implementar**:

1. **Streaming Consumer**
   ```python
   # spark_streaming_recommendations.py
   - Leer topic 'ratings' con Spark Structured Streaming
   - Procesar micro-batches cada 10 segundos
   - Checkpointing en HDFS
   ```

2. **Model Loader**
   ```python
   # model_loader.py
   - Cargar modelo ALS desde HDFS
   - Cache de modelo en memoria
   - Validación de versión del modelo
   ```

3. **Recommendation Generator**
   ```python
   # recommendation_generator.py
   - Generar top-10 recomendaciones por usuario
   - Filtrar películas ya vistas
   - Calcular scores de confianza
   ```

4. **Metrics Publisher**
   ```python
   # metrics_publisher.py
   - Publicar métricas en topic 'metrics'
   - Rastrear: throughput, latencia, RMSE, cobertura
   - Formato JSON para dashboard
   ```

**Métricas esperadas**:
- Throughput: ratings procesados/segundo
- Latencia: end-to-end (rating → recomendación)
- RMSE: error de predicción vs ratings reales
- Cobertura: % de usuarios con recomendaciones

---

## 📁 Estructura de Archivos Actualizada

```
Recomendacion-Gran-Escala/
├── docs/
│   ├── FASE6_RESUMEN.md           # ← Este archivo
│   ├── FASE6_VERIFICACION.md      # Resultados de pruebas
│   └── ...
├── movies/src/streaming/
│   ├── create_kafka_topics.py     # Admin client Kafka
│   ├── kafka_producer_hello.py    # Producer de prueba
│   ├── kafka_consumer_hello.py    # Consumer de prueba
│   └── README_FASE6.md            # Documentación técnica
├── scripts/
│   └── verify_kafka_phase6.sh     # Script de verificación
├── shared/streaming/               # Scripts copiados para Docker
│   ├── create_kafka_topics.py
│   ├── kafka_producer_hello.py
│   └── kafka_consumer_hello.py
└── requirements.txt                # +kafka-python>=2.0.2
```

---

## ✅ Criterios de Aceptación

| # | Criterio | Estado | Evidencia |
|---|----------|--------|-----------|
| 1 | Topics `ratings` y `metrics` creados | ✅ | `kafka-topics --list` |
| 2 | Esquema JSON definido y documentado | ✅ | README_FASE6.md |
| 3 | Validación de esquema implementada | ✅ | 10/10 mensajes válidos |
| 4 | Producer hello world funcional | ✅ | 10 mensajes enviados, 0 errores |
| 5 | Consumer hello world funcional | ✅ | 10 mensajes consumidos, LAG=0 |
| 6 | Particionamiento por userId | ✅ | 5 particiones activas |
| 7 | Script de verificación | ✅ | verify_kafka_phase6.sh |
| 8 | Documentación completa | ✅ | README + RESUMEN + VERIFICACION |

**Todos los criterios cumplidos**: ✅ **8/8 (100%)**

---

## 🐳 Servicios Docker Activos

```
CONTAINER          IMAGE                              STATUS    PORTS
kafka             confluentinc/cp-kafka:6.2.0        Up        9092, 9093
zookeeper         confluentinc/cp-zookeeper:6.2.0    Up        2181
spark-master      apache/spark:3.4.1                 Up        7077, 8080, 4040
spark-worker      apache/spark:3.4.1                 Up        8081
namenode          bde2020/hadoop-namenode:2.0.0      Up        9000, 9870
datanode          bde2020/hadoop-datanode:2.0.0      Up        9864
resourcemanager   bde2020/hadoop-resourcemanager     Up        8032, 8088
nodemanager       bde2020/hadoop-nodemanager         Up        8042
recs-api          recomendacion-gran-escala-api      Up        8000
```

---

## 📚 Comandos de Referencia

### Iniciar Kafka
```bash
docker compose up -d zookeeper kafka
sleep 30  # Esperar inicialización
```

### Instalar Dependencias
```bash
docker exec -u root spark-master pip install kafka-python lz4 python-snappy
```

### Crear Topics
```bash
docker exec spark-master python3 /opt/spark/work-dir/streaming/create_kafka_topics.py
```

### Listar Topics
```bash
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

### Describir Topic
```bash
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --describe --topic ratings
```

### Ejecutar Producer
```bash
docker exec spark-master python3 /opt/spark/work-dir/streaming/kafka_producer_hello.py \
  --count 10 --delay 0.3
```

### Ejecutar Consumer
```bash
docker exec spark-master python3 /opt/spark/work-dir/streaming/kafka_consumer_hello.py \
  --max-messages 10 --timeout 10
```

### Ver Offsets
```bash
docker exec kafka kafka-run-class kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 --topic ratings
```

### Ver Consumer Groups
```bash
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --list
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 \
  --describe --group ratings-consumer-hello-world
```

### Verificación Completa
```bash
./scripts/verify_kafka_phase6.sh
```

---

## 🔍 Troubleshooting

### Problema: Error de compresión LZ4
```
❌ Libraries for lz4 compression codec not found
```
**Solución**: `pip install lz4 python-snappy`

### Problema: Topics ya existen
```
❌ TopicAlreadyExistsError
```
**Solución**: Esperado, verificar con `kafka-topics --describe`

### Problema: Consumer no recibe mensajes
```
⏱️  Timeout: 30s sin mensajes nuevos
```
**Solución**: 
1. Verificar offsets con `GetOffsetShell`
2. Resetear consumer group: `--reset-offsets --to-earliest`
3. Verificar que producer envió mensajes

### Problema: Kafka no arranca
```
❌ Error creando producer: NoBrokersAvailable
```
**Solución**:
1. `docker compose up -d kafka`
2. Esperar ~30 segundos
3. Verificar logs: `docker logs kafka --tail 50`

---

## 📊 Comparación con Diseño Original

| Aspecto | Diseño (Fase 6) | Implementado | Estado |
|---------|----------------|--------------|--------|
| Topic ratings | 3 particiones | 6 particiones | ⚠️ Diferente |
| Topic metrics | 1 partición | 3 particiones | ⚠️ Diferente |
| Esquema JSON | Definido | Implementado + Validación | ✅ Mejorado |
| Producer | Hello world | CLI + Stats + Validación | ✅ Mejorado |
| Consumer | Hello world | CLI + Stats + Distribución | ✅ Mejorado |
| Documentación | Básica | README + Scripts + Resumen | ✅ Mejorado |

**Nota**: Diferencias en particiones debido a ejecución previa. Funcionalidad no afectada.

---

## 💡 Conclusiones

### Logros Principales

1. ✅ **Infraestructura de streaming operativa** con Kafka + Zookeeper
2. ✅ **Topics configurados** para flujo de datos (ratings → metrics)
3. ✅ **Esquema JSON robusto** con validación completa
4. ✅ **Producer/Consumer funcionales** con 100% de éxito en pruebas
5. ✅ **Particionamiento inteligente** por userId para stateful streaming
6. ✅ **Documentación completa** con ejemplos y troubleshooting

### Preparación para Fase 7

- ✅ Topics listos para Spark Structured Streaming
- ✅ Esquema validado para procesamiento batch
- ✅ Consumer group configurado para tracking de progreso
- ✅ Modelo ALS disponible (Fase 5) para inferencia en tiempo real
- ✅ Infraestructura Hadoop/HDFS para checkpointing

### Valor Agregado

- **Producer/Consumer robustos** más allá de "hello world"
- **CLI arguments** para testing flexible
- **Estadísticas detalladas** (throughput, distribución, errores)
- **Validación exhaustiva** previene datos corruptos
- **Scripts de automatización** para verificación end-to-end

---

**Estado Final**: ✅ **FASE 6 COMPLETADA Y VERIFICADA**

**Siguiente**: Fase 7 - Spark Structured Streaming para Recomendaciones en Tiempo Real

---

**Documentado por**: GitHub Copilot  
**Fecha**: 29 de octubre de 2025  
**Duración total de implementación**: ~2 horas (código + pruebas + documentación)
