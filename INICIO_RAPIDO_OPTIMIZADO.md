# 🚀 Inicio Rápido - Sistema Optimizado

## ✅ Cambios Aplicados

### Recursos Spark Aumentados
- **Antes:** 2GB RAM, 2 cores
- **Ahora:** 4GB RAM, 4 cores
- **Jobs simultáneos:** 2

### Scripts Optimizados
- ✅ `run-streaming-processor.sh`: Usa 2 cores, máx 2GB
- ✅ `run-batch-analytics.sh`: Usa 2 cores, máx 2GB
- ✅ Ambos pueden correr simultáneamente

## 📋 Pasos de Ejecución

### 1️⃣ Verificar Estado del Sistema

```bash
# Verificar todos los servicios
docker compose ps

# Verificar recursos Spark específicamente
./scripts/check-spark-resources.sh
```

**Deberías ver:**
- ✅ Workers registrados: 1
- ✅ Memoria: 4G
- ✅ Cores: 4

### 2️⃣ Generar Datos con Latent Generator

```bash
# Terminal 1: Generar 100 ratings sintéticos
./scripts/run-latent-generator.sh 100
```

**Esto genera:**
- Ratings basados en factores latentes
- Usuarios y películas con preferencias
- Datos enviados a Kafka topic `ratings`

**Tiempo estimado:** ~30-60 segundos

### 3️⃣ Iniciar Procesador de Streaming

```bash
# Terminal 2: Procesar ratings en tiempo real
./scripts/run-streaming-processor.sh
```

**Esto hace:**
- Lee del topic `ratings`
- Calcula ventanas (tumbling 1min, sliding 5min)
- Escribe agregaciones a HDFS
- Publica métricas a topic `metrics`

**Estado esperado:**
```
Batch: X
-------------------------------------------
Batch: X
-------------------------------------------
```

**NO deberías ver:**
```
WARN TaskSchedulerImpl: Initial job has not accepted any resources
```

### 4️⃣ Ejecutar Analytics Batch (Opcional)

```bash
# Terminal 3: Análisis batch sobre datos almacenados
./scripts/run-batch-analytics.sh
```

**Requisitos:**
- Debe haber datos en `/streams/ratings/` en HDFS
- Espera al menos 2-3 minutos después de iniciar streaming

**Outputs:**
- Distribución de ratings por género
- Top películas por periodo
- Películas trending

### 5️⃣ Ver Dashboard

Abre en tu navegador:
```
http://localhost:8501
```

**Métricas en tiempo real:**
- Ratings por minuto
- Promedio de ratings
- Top películas
- Actividad por género

## 🔍 Monitoreo

### Spark Master UI
```
http://localhost:8080
```

**Verifica:**
- Workers: 1 activo
- Running Applications: 1-2
- Completed Applications: historial

### Spark Worker UI
```
http://localhost:8081
```

**Verifica:**
- Memory: 4.0 GB
- Cores: 4
- Running Executors: 1-2

### Logs en Tiempo Real

```bash
# Streaming processor
docker logs -f spark-master | grep -i "batch"

# Ver métricas enviadas a Kafka
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic metrics \
  --from-beginning

# Ver ratings generados
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic ratings \
  --max-messages 10
```

## 🐛 Troubleshooting

### "Initial job has not accepted any resources"

**Problema:** Jobs no pueden obtener recursos del worker

**Solución:**
```bash
# 1. Verificar recursos
./scripts/check-spark-resources.sh

# 2. Si worker no está registrado
docker compose restart spark-worker

# 3. Esperar 10 segundos
sleep 10

# 4. Verificar nuevamente
./scripts/check-spark-resources.sh
```

### "No hay workers registrados"

**Problema:** Worker no se conectó al master

**Solución:**
```bash
# Verificar logs del worker
docker logs spark-worker | tail -20

# Reiniciar servicios Spark
docker compose restart spark-master spark-worker

# Esperar y verificar
sleep 10
./scripts/check-spark-resources.sh
```

### Topic 'ratings' está vacío

**Problema:** No hay datos para procesar

**Solución:**
```bash
# Generar datos nuevamente
./scripts/run-latent-generator.sh 200

# Verificar que se crearon
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic ratings \
  --max-messages 5
```

### Dashboard no muestra datos

**Problema:** API no recibe métricas

**Verificar:**
```bash
# 1. API está corriendo
docker logs api | tail -20

# 2. Hay métricas en Kafka
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic metrics \
  --max-messages 5

# 3. Reiniciar API y dashboard
docker compose restart api dashboard
```

## 📊 Flujo Completo Recomendado

### Ejecución Secuencial (Más Estable)

```bash
# Paso 1: Verificar sistema
./scripts/check-spark-resources.sh

# Paso 2: Generar datos
./scripts/run-latent-generator.sh 100

# Paso 3: Iniciar streaming (dejar corriendo)
# Terminal 2
./scripts/run-streaming-processor.sh

# Paso 4: Generar más datos mientras streaming corre
# Terminal 1
./scripts/run-latent-generator.sh 200

# Paso 5: Esperar 2-3 minutos, luego analytics
# Terminal 3
sleep 180
./scripts/run-batch-analytics.sh

# Paso 6: Ver dashboard
# Navegador
http://localhost:8501
```

### Ejecución Paralela (Requiere sistema optimizado)

```bash
# Terminal 1: Streaming en background
nohup ./scripts/run-streaming-processor.sh > streaming.log 2>&1 &

# Esperar que inicie
sleep 30

# Terminal 2: Generar datos continuamente
./scripts/run-latent-generator.sh 500

# Terminal 3: Analytics periódico
sleep 180
./scripts/run-batch-analytics.sh

# Monitorear en paralelo
tail -f streaming.log
```

## 📈 Métricas de Rendimiento Esperadas

### Latent Generator
- **Velocidad:** ~10-20 ratings/segundo
- **100 ratings:** ~10 segundos
- **500 ratings:** ~30 segundos

### Streaming Processor
- **Latencia:** <1 segundo por batch
- **Throughput:** 100+ ratings/segundo
- **Memoria:** ~1.5GB
- **CPU:** 2 cores

### Batch Analytics
- **Duración:** 30-60 segundos
- **Memoria:** ~1.5GB
- **CPU:** 2 cores

### Dashboard
- **Actualización:** Cada 5 segundos
- **Latencia:** <500ms
- **Conexión:** WebSocket a API

## 📝 Próximos Pasos

1. **Explorar datos en HDFS:**
   ```bash
   docker exec namenode hadoop fs -ls -R /streams/ratings/
   ```

2. **Ver outputs de analytics:**
   ```bash
   docker exec namenode hadoop fs -ls -R /outputs/analytics/
   ```

3. **Experimentar con ventanas:**
   - Modificar `ratings_stream_processor.py`
   - Cambiar tamaños de ventana
   - Agregar nuevas métricas

4. **Escalar generación:**
   ```bash
   ./scripts/run-latent-generator.sh 1000
   ```

## 🎯 Objetivos Completados

- ✅ Recursos Spark optimizados (4GB, 4 cores)
- ✅ Jobs pueden correr simultáneamente
- ✅ Sistema estable sin warnings de recursos
- ✅ Pipeline completo funcional:
  - Generación de datos
  - Procesamiento streaming
  - Analytics batch
  - Dashboard en tiempo real

## 📚 Documentación Adicional

- **Optimización:** `docs/OPTIMIZACION_RECURSOS.md`
- **Verificación:** `./scripts/check-spark-resources.sh`
- **Comandos:** `docs/COMANDOS_RAPIDOS.md`
