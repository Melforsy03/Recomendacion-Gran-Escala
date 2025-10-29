# ✅ VERIFICACIÓN FASE 6 - TOPICS KAFKA Y ESQUEMA DE EVENTOS

**Fecha**: 29 de octubre de 2025  
**Hora**: 18:38 UTC  
**Estado**: ✅ COMPLETADA EXITOSAMENTE

---

## 🎯 Resumen Ejecutivo

La Fase 6 ha sido **completada y verificada exitosamente**. Todos los componentes de la infraestructura de streaming con Kafka están operativos:

- ✅ **Zookeeper** corriendo (puerto 2181)
- ✅ **Kafka** corriendo (puertos 9092/9093)
- ✅ **Topics** creados y configurados
- ✅ **Producer** funcional (10/10 mensajes enviados)
- ✅ **Consumer** funcional (10/10 mensajes recibidos y validados)
- ✅ **Esquema JSON** validado
- ✅ **Offsets** confirmados
- ✅ **Consumer Group** operativo

---

## 🐳 Servicios Docker Verificados

### Contenedores Kafka
```
CONTAINER ID   IMAGE                            STATUS
0609626d7199   confluentinc/cp-kafka:6.2.0      Up (corriendo)
fd9ceb911f95   confluentinc/cp-zookeeper:6.2.0  Up (corriendo)
```

### Puertos Expuestos
- **Zookeeper**: 2181
- **Kafka (interno)**: 9092
- **Kafka (externo)**: 9093

---

## 📁 Topics Creados

### Topic: `ratings`
```
Topic: ratings
TopicId: Ee4loqYbR_WIlV7yJhJw3A
PartitionCount: 6
ReplicationFactor: 1
Configs: retention.ms=604800000, compression.type=lz4

Particiones:
  - Partition 0: Leader=1, Replicas=1, Isr=1 → Offset=3
  - Partition 1: Leader=1, Replicas=1, Isr=1 → Offset=0
  - Partition 2: Leader=1, Replicas=1, Isr=1 → Offset=2
  - Partition 3: Leader=1, Replicas=1, Isr=1 → Offset=1
  - Partition 4: Leader=1, Replicas=1, Isr=1 → Offset=3
  - Partition 5: Leader=1, Replicas=1, Isr=1 → Offset=1
```

**Total de mensajes**: 10 (distribuidos en 5 de 6 particiones)

### Topic: `metrics`
```
Topic: metrics
TopicId: k6LdFs0_Sg2xwFL6Xbr8dw
PartitionCount: 3
ReplicationFactor: 1
Configs: retention.ms=2592000000, compression.type=gzip
```

---

## 📐 Esquema JSON Validado

### Estructura del Evento `ratings`

```json
{
  "userId": 44176,
  "movieId": 21373,
  "rating": 3.5,
  "timestamp": 1761763121809
}
```

### Validaciones Implementadas

| Campo | Tipo | Validación | Resultado |
|-------|------|------------|-----------|
| `userId` | `int` | > 0, rango 1-138493 | ✅ PASS |
| `movieId` | `int` | > 0, rango 1-131262 | ✅ PASS |
| `rating` | `double` | ∈ {0.5, 1.0, ..., 5.0} | ✅ PASS |
| `timestamp` | `long` | > 0 (epoch millis) | ✅ PASS |

**Mensajes validados**: 10/10 (100% válidos)

---

## 📤 Producer Hello World

### Comando Ejecutado
```bash
docker exec spark-master python3 /opt/spark/work-dir/streaming/kafka_producer_hello.py \
  --count 10 --delay 0.3
```

### Resultados

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

======================================================================
✅ PRODUCER HELLO WORLD COMPLETADO EXITOSAMENTE
```

### Ejemplos de Mensajes Enviados

**Mensaje 1** (Partition 0, Offset 0):
```json
{
  "userId": 44176,
  "movieId": 21373,
  "rating": 3.5,
  "timestamp": 1761763121809
}
```

**Mensaje 6** (Partition 3, Offset 0):
```json
{
  "userId": 127007,
  "movieId": 24788,
  "rating": 5.0,
  "timestamp": 1761763122145
}
```

**Mensaje 10** (Partition 5, Offset 0):
```json
{
  "userId": 126554,
  "movieId": 10318,
  "rating": 4.5,
  "timestamp": 1761763124564
}
```

---

## 📥 Consumer Hello World

### Comando Ejecutado
```bash
docker exec spark-master python3 /opt/spark/work-dir/streaming/kafka_consumer_hello.py \
  --max-messages 10 --timeout 10
```

### Resultados

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
   0.5: █ (1)
   1.0: █ (1)
   1.5: ██ (2)
   2.0: █ (1)
   3.5: █ (1)
   4.0: █ (1)
   4.5: ██ (2)
   5.0: █ (1)

======================================================================
✅ CONSUMER HELLO WORLD COMPLETADO EXITOSAMENTE
```

### Validación de Particionamiento

Los mensajes fueron correctamente distribuidos por `userId` (key):

| Partition | Mensajes | Offsets | Ejemplo userId |
|-----------|----------|---------|----------------|
| 0 | 3 | 0-2 | 44176, 110885, 1345 |
| 1 | 0 | - | - |
| 2 | 2 | 0-1 | 33351, 28643 |
| 3 | 1 | 0 | 127007 |
| 4 | 3 | 0-2 | 118307, 1196, 87687 |
| 5 | 1 | 0 | 126554 |

**Total**: 10 mensajes en 5 particiones activas

---

## 📍 Offsets Verificados

### Topic `ratings` - Log End Offsets
```
ratings:0 → 3 mensajes
ratings:1 → 0 mensajes
ratings:2 → 2 mensajes
ratings:3 → 1 mensaje
ratings:4 → 3 mensajes
ratings:5 → 1 mensaje

Total: 10 mensajes
```

### Consumer Group: `ratings-consumer-hello-world`

```
GROUP                        TOPIC    PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
ratings-consumer-hello-world ratings  0          3               3               0
ratings-consumer-hello-world ratings  1          0               0               0
ratings-consumer-hello-world ratings  2          2               2               0
ratings-consumer-hello-world ratings  3          1               1               0
ratings-consumer-hello-world ratings  4          3               3               0
ratings-consumer-hello-world ratings  5          1               1               0
```

**LAG Total**: 0 (todos los mensajes consumidos)

---

## 🔧 Dependencias Instaladas

### Python Packages (spark-master)
```
✅ kafka-python == 2.2.15
✅ lz4 == 4.3.3
✅ python-snappy == 0.7.3
✅ cramjam == 2.11.0
```

### Instalación
```bash
docker exec -u root spark-master pip install kafka-python lz4 python-snappy
```

---

## ✅ Criterios de Aceptación

| Criterio | Estado | Evidencia |
|----------|--------|-----------|
| Topics `ratings` y `metrics` creados | ✅ PASS | kafka-topics --describe |
| Esquema JSON definido | ✅ PASS | README_FASE6.md |
| Producer hello world funcional | ✅ PASS | 10/10 enviados, 0 errores |
| Consumer hello world funcional | ✅ PASS | 10/10 consumidos, 0 lag |
| Validación de esquema | ✅ PASS | 10/10 válidos (100%) |
| Particionamiento por userId | ✅ PASS | 5 particiones activas |
| Offsets correctos | ✅ PASS | LAG=0 en todas las particiones |
| Documentación completa | ✅ PASS | README_FASE6.md + scripts |

---

## 🎓 Lecciones Aprendidas

### 1. Dependencias de Compresión
**Problema**: Error `Libraries for lz4 compression codec not found`

**Solución**: Instalar librerías de compresión en contenedores Spark:
```bash
pip install kafka-python lz4 python-snappy
```

### 2. Particionamiento Consistente
El uso de `userId` como key garantiza que todos los ratings de un usuario vayan a la misma partición, facilitando procesamiento con estado (stateful streaming) en Spark.

### 3. Validación de Esquema
La validación en producer y consumer evita mensajes malformados:
- **Producer**: Valida antes de enviar
- **Consumer**: Re-valida al recibir
- **Resultado**: 100% de mensajes válidos

### 4. Consumer Group Offsets
El consumer group `ratings-consumer-hello-world` mantiene offsets automáticamente, permitiendo reanudar consumo desde última posición.

---

## 🚀 Próximos Pasos

### Fase 7: Streaming de Recomendaciones con Spark Structured Streaming

**Objetivo**: Consumir ratings en tiempo real y generar recomendaciones

**Tareas**:
1. Crear Spark Structured Streaming consumer
2. Cargar modelo ALS de Fase 5
3. Generar recomendaciones por micro-batch
4. Publicar resultados en topic `recommendations`
5. Publicar métricas en topic `metrics`
6. Implementar checkpointing en HDFS

**Archivos a crear**:
```
movies/src/streaming/
├── spark_streaming_recommendations.py  # Consumer Structured Streaming
├── model_loader.py                     # Carga modelo ALS
├── recommendation_generator.py         # Genera recomendaciones
└── metrics_publisher.py                # Publica métricas
```

**Métricas a rastrear**:
- Throughput (ratings/segundo)
- Latencia (end-to-end)
- RMSE de predicciones
- Cobertura de recomendaciones (% usuarios con recs)

---

## 📋 Comandos de Referencia Rápida

### Verificar Topics
```bash
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --describe --topic ratings
```

### Enviar Mensajes de Prueba
```bash
docker exec spark-master python3 /opt/spark/work-dir/streaming/kafka_producer_hello.py --count 10
```

### Consumir Mensajes
```bash
docker exec spark-master python3 /opt/spark/work-dir/streaming/kafka_consumer_hello.py --max-messages 10
```

### Ver Offsets
```bash
docker exec kafka kafka-run-class kafka.tools.GetOffsetShell --broker-list localhost:9092 --topic ratings
```

### Ver Consumer Groups
```bash
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --list
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --describe --group ratings-consumer-hello-world
```

---

## 📊 Métricas de Performance

| Métrica | Producer | Consumer |
|---------|----------|----------|
| **Mensajes** | 10 | 10 |
| **Duración** | 2.76 s | 3.29 s |
| **Throughput** | 3.63 msg/s | 3.04 msg/s |
| **Tasa de éxito** | 100% | 100% |
| **Errores** | 0 | 0 |

---

## ✅ Estado Final

**FASE 6: ✅ COMPLETADA Y VERIFICADA**

Todos los componentes de la infraestructura de streaming están operativos y listos para la Fase 7 (Spark Structured Streaming).

---

**Verificado por**: GitHub Copilot  
**Timestamp**: 2025-10-29 18:39:00 UTC
