# FASE 6: Topics Kafka y Esquema de Eventos

## 📋 Objetivo

Configurar la infraestructura de streaming con Kafka para el sistema de recomendaciones en tiempo real:
- Crear topics de Kafka para ratings y métricas
- Definir y validar esquema JSON de eventos
- Implementar producer/consumer "hello world" funcional

---

## 🎯 Topics Creados

### 1. **ratings** (Input Streaming)
- **Propósito**: Recibir ratings de usuarios en tiempo real
- **Particiones**: 3
- **Replication Factor**: 1
- **Retention**: 7 días
- **Compression**: LZ4
- **Key**: userId (para particionamiento consistente)

### 2. **metrics** (Output Métricas)
- **Propósito**: Publicar métricas de streaming (throughput, latencia, RMSE)
- **Particiones**: 1
- **Replication Factor**: 1
- **Retention**: 30 días
- **Compression**: GZIP

---

## 📐 Esquema JSON - Topic `ratings`

```json
{
    "userId": 123,
    "movieId": 456,
    "rating": 4.5,
    "timestamp": 1730232000000
}
```

### Validaciones del Esquema

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `userId` | `int` | > 0, rango 1-138493 | ID del usuario único |
| `movieId` | `int` | > 0, rango 1-27278 | ID de la película única |
| `rating` | `double` | {0.5, 1.0, 1.5, ..., 5.0} | Rating en escala 0.5-5.0 (incrementos de 0.5) |
| `timestamp` | `long` | > 0 | Unix timestamp en milisegundos |

**Ejemplo válido**:
```json
{
    "userId": 12345,
    "movieId": 1234,
    "rating": 4.5,
    "timestamp": 1730232000000
}
```

**Ejemplo inválido**:
```json
{
    "userId": -1,          // ❌ userId debe ser > 0
    "movieId": "abc",      // ❌ movieId debe ser int
    "rating": 6.0,         // ❌ rating fuera de rango
    "timestamp": "2024"    // ❌ timestamp debe ser long
}
```

---

## 🛠️ Archivos Implementados

```
movies/src/streaming/
├── create_kafka_topics.py       # Creación de topics con validación
├── kafka_producer_hello.py      # Producer de prueba (hello world)
└── kafka_consumer_hello.py      # Consumer de prueba (hello world)

scripts/
└── verify_kafka_phase6.sh       # Script de verificación completa

requirements.txt                 # +kafka-python>=2.0.2
```

---

## 🚀 Ejecución

### Paso 1: Iniciar Kafka y Zookeeper

```bash
cd /home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala
docker-compose up -d zookeeper kafka
```

**Esperar ~30 segundos** para que Kafka esté completamente operativo.

### Paso 2: Instalar Dependencias

```bash
# Instalar kafka-python en contenedores Spark
docker exec -u root spark-master pip install kafka-python>=2.0.2
docker exec -u root spark-worker pip install kafka-python>=2.0.2
```

### Paso 3: Crear Topics

```bash
# Copiar scripts a directorio compartido
mkdir -p shared/streaming
cp movies/src/streaming/*.py shared/streaming/

# Ejecutar creación de topics
docker exec spark-master python3 /opt/spark/work-dir/streaming/create_kafka_topics.py
```

**Salida esperada**:
```
✅ Conectado a Kafka en ['kafka:9092']
✅ Topic 'ratings' creado exitosamente
✅ Topic 'metrics' creado exitosamente
```

### Paso 4: Verificar Topics Creados

```bash
# Listar topics
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Describir topic 'ratings'
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --describe --topic ratings
```

**Salida esperada**:
```
Topic: ratings  Partitions: 3  Replication: 1
```

### Paso 5: Producer Hello World

```bash
# Enviar 10 mensajes de prueba
docker exec spark-master python3 /opt/spark/work-dir/streaming/kafka_producer_hello.py --count 10
```

**Salida esperada**:
```
✅ Producer conectado a Kafka en ['kafka:9092']
📤 Enviando 10 ratings de prueba a topic 'ratings'...

[1/10] Generado:
  {
    "userId": 45678,
    "movieId": 1234,
    "rating": 4.5,
    "timestamp": 1730232000000
  }
✅ Enviado - userId=45678, movieId=1234, rating=4.5 | Partition=2, Offset=0

...

📊 RESUMEN DE ENVÍO
✅ Mensajes enviados: 10
❌ Mensajes fallidos: 0
📈 Total: 10
⏱️  Tiempo total: 5.23 segundos
🚀 Throughput: 1.91 mensajes/seg
✓  Tasa de éxito: 100.0%

✅ PRODUCER HELLO WORLD COMPLETADO EXITOSAMENTE
```

### Paso 6: Consumer Hello World

```bash
# Consumir mensajes (timeout 30s)
docker exec spark-master python3 /opt/spark/work-dir/streaming/kafka_consumer_hello.py --max-messages 10
```

**Salida esperada**:
```
✅ Consumer conectado a Kafka en ['kafka:9092']
   Topic: ratings
   Group ID: ratings-consumer-hello-world

📥 Consumiendo mensajes del topic 'ratings'...

✅ Mensaje recibido:
   Partition: 2, Offset: 0
   Key: 45678
   Timestamp: 2024-10-29 15:20:00
   Value: {
      "userId": 45678,
      "movieId": 1234,
      "rating": 4.5,
      "timestamp": 1730232000000
   }

...

📊 RESUMEN DE CONSUMO
📈 Mensajes procesados:
   Total: 10
   Válidos: 10 (100.0%)
   Inválidos: 0

⭐ Distribución de ratings:
   4.5: ███████████████ (3)
   5.0: ██████████ (2)
   ...

✅ CONSUMER HELLO WORLD COMPLETADO EXITOSAMENTE
```

---

## ✅ Verificación Completa (Script Automatizado)

```bash
# Ejecutar script de verificación completa
./scripts/verify_kafka_phase6.sh
```

Este script ejecuta automáticamente:
1. ✅ Verificar Zookeeper y Kafka
2. ✅ Instalar dependencias Python
3. ✅ Crear topics
4. ✅ Listar y describir topics
5. ✅ Ejecutar producer (10 mensajes)
6. ✅ Ejecutar consumer (leer mensajes)
7. ✅ Verificar offsets

**Salida final esperada**:
```
✅ FASE 6 COMPLETADA EXITOSAMENTE

Próximos pasos:
  - Fase 7: Streaming de recomendaciones con Spark Structured Streaming
  - Fase 8: Dashboard en tiempo real con métricas
```

---

## 🔍 Comandos Útiles de Kafka

### Listar Topics
```bash
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list
```

### Describir Topic
```bash
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --describe --topic ratings
```

### Ver Mensajes en Topic (desde el inicio)
```bash
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic ratings \
  --from-beginning \
  --max-messages 10
```

### Ver Offsets de Particiones
```bash
docker exec kafka kafka-run-class kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic ratings
```

### Eliminar Topic (si es necesario)
```bash
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --delete --topic ratings
```

### Consumir con Consumer Group
```bash
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic ratings \
  --group my-consumer-group \
  --from-beginning
```

### Ver Consumer Groups
```bash
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --list
```

### Describir Consumer Group
```bash
docker exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe \
  --group ratings-consumer-hello-world
```

---

## 📊 Métricas y Monitoreo

### Ver Logs de Kafka
```bash
docker logs kafka --tail 100 -f
```

### Ver Logs de Zookeeper
```bash
docker logs zookeeper --tail 100 -f
```

### Verificar Conectividad
```bash
# Desde host
telnet localhost 9093

# Desde contenedor Spark
docker exec spark-master telnet kafka 9092
```

---

## 🐛 Troubleshooting

### Problema: Topics no se crean

**Síntoma**:
```
❌ Error creando topic 'ratings': TimeoutError
```

**Solución**:
```bash
# 1. Verificar que Kafka esté corriendo
docker ps | grep kafka

# 2. Ver logs de Kafka
docker logs kafka --tail 50

# 3. Reiniciar Kafka
docker-compose restart kafka

# 4. Esperar ~30s y reintentar
```

### Problema: Producer no puede conectar

**Síntoma**:
```
❌ Error creando producer: NoBrokersAvailable
```

**Solución**:
```bash
# Verificar que Kafka esté aceptando conexiones
docker exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# Verificar advertised.listeners
docker exec kafka env | grep KAFKA_ADVERTISED_LISTENERS
```

### Problema: Consumer no recibe mensajes

**Síntoma**:
```
⏱️  Timeout: 30s sin mensajes nuevos
```

**Solución**:
```bash
# 1. Verificar que hay mensajes en el topic
docker exec kafka kafka-run-class kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic ratings

# 2. Resetear consumer group offset
docker exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group ratings-consumer-hello-world \
  --reset-offsets \
  --to-earliest \
  --topic ratings \
  --execute

# 3. Reintentar consumo
```

### Problema: kafka-python no instalado

**Síntoma**:
```
ModuleNotFoundError: No module named 'kafka'
```

**Solución**:
```bash
# Instalar en contenedores
docker exec -u root spark-master pip install kafka-python
docker exec -u root spark-worker pip install kafka-python
```

---

## 📚 Próximos Pasos

### Fase 7: Streaming de Recomendaciones
- Spark Structured Streaming consumiendo topic `ratings`
- Generación de recomendaciones en tiempo real usando modelo ALS
- Publicación de métricas en topic `metrics`

### Fase 8: Dashboard de Métricas
- Consumir topic `metrics` en API REST
- Dashboard en tiempo real con throughput, latencia, RMSE
- Visualización de distribución de ratings

---

## ✅ Criterios de Aceptación

- [x] Topics `ratings` y `metrics` creados y visibles en Kafka
- [x] Esquema JSON definido y documentado
- [x] Producer hello world funcional (envía mensajes válidos)
- [x] Consumer hello world funcional (consume y valida mensajes)
- [x] Validación de esquema implementada
- [x] Script de verificación automatizado
- [x] Documentación completa con ejemplos

---

**Documentado**: 29 de octubre de 2025  
**Siguiente fase**: Streaming con Spark Structured Streaming
