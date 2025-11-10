# Optimización de Recursos - Spark Standalone

## Problema Identificado

El sistema presentaba el siguiente error al ejecutar múltiples jobs de Spark:

```
WARN TaskSchedulerImpl: Initial job has not accepted any resources; 
check your cluster UI to ensure that workers are registered and have sufficient resources
```

### Causa
- Spark Worker configurado con **2GB RAM y 2 cores**
- Múltiples jobs intentando ejecutarse simultáneamente
- Recursos insuficientes para asignar a todos los jobs

## Solución Implementada

### 1. Aumento de Recursos del Worker

**Antes:**
```yaml
SPARK_WORKER_MEMORY=2G
SPARK_WORKER_CORES=2
```

**Después:**
```yaml
SPARK_WORKER_MEMORY=4G
SPARK_WORKER_CORES=4
```

### 2. Optimización de Configuración de Jobs

#### Streaming Processor
```bash
--conf spark.executor.memory=1g
--conf spark.executor.cores=2
--conf spark.cores.max=2           # Limita cores totales
--conf spark.sql.shuffle.partitions=8  # Reducido de 10
```

#### Batch Analytics
```bash
--conf spark.executor.memory=1g
--conf spark.executor.cores=2
--conf spark.cores.max=2           # Limita cores totales
--conf spark.sql.shuffle.partitions=20 # Reducido de 50
```

### 3. Distribución de Recursos

Con la nueva configuración:

| Job                | Driver | Executor | Cores | Total RAM |
|-------------------|--------|----------|-------|-----------|
| Streaming         | 512MB  | 1GB      | 2     | ~1.5GB    |
| Batch Analytics   | 512MB  | 1GB      | 2     | ~1.5GB    |
| **Disponible**    | -      | -        | **4** | **4GB**   |

Esto permite ejecutar **2 jobs simultáneamente** o dejar recursos para otros procesos.

## Aplicar Cambios

### 1. Detener servicios actuales
```bash
docker compose stop spark-worker spark-master
```

### 2. Recrear con nuevos recursos
```bash
docker compose up -d spark-worker spark-master
```

### 3. Verificar recursos asignados
```bash
# Verificar en Spark UI
http://localhost:8080

# Verificar configuración del worker
docker logs spark-worker | grep -i "memory\|cores"
```

## Workflow Recomendado

### Opción A: Secuencial (Más Estable)
```bash
# Terminal 1: Generar datos
./scripts/run-latent-generator.sh 100

# Terminal 2: Procesar streaming
./scripts/run-streaming-processor.sh

# Terminal 3 (después de tener datos): Analytics
./scripts/run-batch-analytics.sh

# Navegador: Dashboard
http://localhost:8501
```

### Opción B: Paralelo (Requiere recursos optimizados)
```bash
# Terminal 1: Streaming (background con nohup)
nohup ./scripts/run-streaming-processor.sh > streaming.log 2>&1 &

# Terminal 2: Generador de datos
./scripts/run-latent-generator.sh 200

# Terminal 3: Analytics (esperar 1-2 min después del streaming)
./scripts/run-batch-analytics.sh
```

## Monitoreo de Recursos

### Spark Master UI
```
http://localhost:8080
```

Verificar:
- ✅ Workers registrados: 1
- ✅ Cores disponibles: 4
- ✅ Memoria disponible: 4GB
- ✅ Applications en Running/Completed

### Logs en Tiempo Real
```bash
# Ver logs del worker
docker logs -f spark-worker

# Ver logs de streaming
docker logs -f spark-master | grep streaming

# Ver uso de recursos
docker stats spark-worker spark-master
```

## Troubleshooting

### Job no acepta recursos

**Síntoma:**
```
WARN TaskSchedulerImpl: Initial job has not accepted any resources
```

**Soluciones:**

1. **Verificar worker está registrado:**
   ```bash
   docker exec spark-master curl -s http://localhost:8080 | grep -i worker
   ```

2. **Revisar recursos disponibles:**
   ```bash
   # Debería mostrar 4 cores, 4GB
   docker logs spark-worker | grep "Starting Spark worker"
   ```

3. **Reducir cores máximos del job:**
   ```bash
   # Agregar a spark-submit
   --conf spark.cores.max=1
   ```

4. **Esperar a que termine job anterior:**
   ```bash
   # Listar jobs activos
   docker exec spark-master ps aux | grep spark-submit
   ```

### Worker no se registra

**Verificar conectividad:**
```bash
docker exec spark-worker curl -s http://spark-master:8080
```

**Reiniciar servicios:**
```bash
docker compose restart spark-worker
```

### Memoria insuficiente

**Reducir memoria del executor:**
```bash
--conf spark.executor.memory=512m
--conf spark.driver.memory=256m
```

## Límites del Sistema

### Recursos Totales Disponibles
- **CPU:** 4 cores en worker
- **RAM:** 4GB en worker
- **Jobs simultáneos recomendados:** 2

### Por Job
- **Mínimo:** 512MB executor + 256MB driver = ~768MB
- **Recomendado:** 1GB executor + 512MB driver = ~1.5GB
- **Máximo seguro:** 1.5GB executor + 1GB driver = ~2.5GB

### Restricciones
- Dejar al menos 512MB libres para overhead del sistema
- No usar `spark.cores.max` mayor a 3 si hay múltiples jobs
- Streaming tiene prioridad (procesos largos)

## Verificación Post-Cambios

```bash
# 1. Verificar servicios corriendo
docker ps | grep spark

# 2. Verificar recursos en UI
curl http://localhost:8080 | grep -A5 "Resources"

# 3. Test rápido
./scripts/run-batch-analytics.sh

# 4. Verificar que no hay warnings
docker logs spark-master 2>&1 | grep -i "warn.*resource"
```

## Referencias

- [Spark Standalone Mode](https://spark.apache.org/docs/3.4.1/spark-standalone.html)
- [Spark Configuration](https://spark.apache.org/docs/3.4.1/configuration.html)
- [Resource Allocation](https://spark.apache.org/docs/3.4.1/job-scheduling.html#configuration-and-setup)
