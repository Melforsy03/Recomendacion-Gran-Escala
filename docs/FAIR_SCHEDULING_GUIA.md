# 🔄 Gestión de Recursos con Fair Scheduling

## 🎯 Problema Resuelto

El sistema tenía un problema crítico: **Spark Standalone asigna TODOS los recursos al primer job que llega**, dejando a los demás jobs sin recursos disponibles.

### Síntoma
```
WARN TaskSchedulerImpl: Initial job has not accepted any resources
```

### Causa Raíz
- El **latent generator** usa 4 cores (todos los disponibles)
- El **streaming processor** no puede obtener recursos
- Configuración por defecto de Spark: FIFO scheduling

## ✅ Solución Implementada

### 1. Fair Scheduling con Pools

Hemos configurado **Fair Scheduling** que permite a múltiples jobs compartir recursos de forma justa:

```xml
<allocations>
  <pool name="streaming">
    <weight>2</weight>        <!-- Prioridad ALTA -->
    <minShare>1</minShare>
  </pool>
  
  <pool name="batch">
    <weight>1</weight>        <!-- Prioridad MEDIA -->
    <minShare>1</minShare>
  </pool>
  
  <pool name="generator">
    <weight>1</weight>        <!-- Prioridad BAJA -->
    <minShare>1</minShare>
  </pool>
</allocations>
```

### 2. Asignación de Recursos por Job

| Job | Pool | Cores Max | Memory | Prioridad |
|-----|------|-----------|--------|-----------|
| **Streaming Processor** | streaming | 2 | 1GB | ⭐⭐ ALTA |
| **Batch Analytics** | batch | 2 | 1GB | ⭐ MEDIA |
| **Latent Generator** | generator | 1 | 512MB | BAJA |

### 3. Estrategia Round-Robin Automática

Con Fair Scheduling, Spark automáticamente:
- ✅ Divide recursos entre jobs activos
- ✅ Respeta pesos (streaming tiene prioridad 2x)
- ✅ Garantiza mínimo 1 core a cada job
- ✅ Redistribuye recursos cuando un job termina

## 🚀 Cómo Usar

### Paso 1: Activar Fair Scheduling (YA HECHO)

```bash
./scripts/spark-job-manager.sh fair-mode
```

### Paso 2: Ejecutar Jobs (Orden Recomendado)

```bash
# Terminal 1: Streaming (prioridad ALTA)
./scripts/run-streaming-processor.sh

# Terminal 2: Generator (prioridad BAJA - se adapta)
./scripts/run-latent-generator.sh 100

# Terminal 3: Analytics (cuando haya datos)
./scripts/run-batch-analytics.sh
```

**Ahora los jobs pueden ejecutarse simultáneamente sin conflictos!**

## 📊 Distribución de Recursos

### Escenario 1: Solo Streaming
```
Worker: [████████████] 4 cores
Streaming: [████] 2 cores (usa lo asignado)
Disponible: [████] 2 cores
```

### Escenario 2: Streaming + Generator
```
Worker: [████████████] 4 cores
Streaming: [████] 2 cores (prioridad alta)
Generator: [██] 1 core (limitado)
Disponible: [██] 1 core
```

### Escenario 3: Streaming + Generator + Batch
```
Worker: [████████████] 4 cores
Streaming: [███] ~1.7 cores (peso 2)
Generator: [█] ~1.1 cores (peso 1)
Batch: [█] ~1.2 cores (peso 1)
```

## 🛠️ Herramientas de Gestión

### Script: spark-job-manager.sh

```bash
# Ver jobs activos
./scripts/spark-job-manager.sh list

# Ver recursos disponibles
./scripts/spark-job-manager.sh resources

# Detener todos los jobs
./scripts/spark-job-manager.sh kill-all

# Configurar fair scheduling
./scripts/spark-job-manager.sh fair-mode
```

### Ejemplo de Uso

```bash
# 1. Verificar estado
./scripts/spark-job-manager.sh resources

# Output:
# Worker Configuration:
#   SPARK_WORKER_MEMORY=4G
#   SPARK_WORKER_CORES=4
# 
# Slots de Ejecución:
#   Total: 2 jobs (con 2 cores cada uno)
#   Usados: 1
#   Libres: 1

# 2. Ver jobs corriendo
./scripts/spark-job-manager.sh list

# Output:
# Aplicaciones activas: 1
# Detalles:
#   PID: 1234
#   CMD: /opt/spark/bin/spark-submit ... ratings_stream_processor.py
```

## 🎛️ Configuración Avanzada

### Cambiar Recursos de un Pool

Editar archivo en spark-master:
```bash
docker exec -it spark-master vi /opt/spark/conf/fairscheduler.xml
```

Luego reiniciar los jobs para que tomen la nueva configuración.

### Aumentar Prioridad de Batch

```xml
<pool name="batch">
  <weight>2</weight>  <!-- Cambiar de 1 a 2 -->
  <minShare>2</minShare>  <!-- Garantizar 2 cores -->
</pool>
```

### Limitar Generator Más Agresivamente

Ya está limitado a 1 core en el script:
```bash
--conf spark.cores.max=1
```

## 🔍 Monitoreo en Tiempo Real

### Spark Master UI
```
http://localhost:8080
```

**Verificar:**
- Running Applications: 1-3
- Cada app muestra cores asignados
- Estado: RUNNING

### Logs de Fair Scheduler

```bash
docker exec spark-master cat /opt/spark/logs/*.out | grep -i "fair"
```

## 📈 Ventajas de Fair Scheduling

### Antes (FIFO)
```
Job 1: ████████████ (todos los recursos)
Job 2: (esperando...)
Job 3: (esperando...)
```

### Después (FAIR)
```
Job 1 (streaming): ████████ (peso 2)
Job 2 (generator): ████ (peso 1)
Job 3 (batch): ████ (peso 1)
```

### Beneficios
- ✅ Múltiples jobs simultáneos
- ✅ Priorización automática
- ✅ No más "waiting for resources"
- ✅ Mejor utilización de recursos
- ✅ Streaming siempre tiene recursos garantizados

## 🚨 Troubleshooting

### Job sigue sin recursos

**Verificar configuración:**
```bash
# Ver logs del job
docker logs spark-master | grep -i "fair\|pool"

# Verificar que el archivo existe
docker exec spark-master ls -la /opt/spark/conf/fairscheduler.xml
```

### Pool no reconocido

**Reconfigurar:**
```bash
./scripts/spark-job-manager.sh fair-mode
```

### Demasiados jobs

**Detener todos y empezar de nuevo:**
```bash
./scripts/spark-job-manager.sh kill-all
sleep 5
./scripts/spark-job-manager.sh resources
```

## 📚 Referencias

- [Spark Fair Scheduler](https://spark.apache.org/docs/3.4.1/job-scheduling.html#fair-scheduler-pools)
- [Scheduling Pools](https://spark.apache.org/docs/3.4.1/job-scheduling.html#scheduling-within-an-application)
- [Resource Allocation](https://spark.apache.org/docs/3.4.1/configuration.html#dynamic-allocation)

## ✨ Resumen

| Aspecto | Antes | Después |
|---------|-------|---------|
| Scheduling | FIFO | FAIR |
| Jobs simultáneos | 1 | 3 |
| Uso de recursos | 100% a 1 job | Distribuido |
| Priorización | No | Sí (por peso) |
| Waiting | Común | Raro |

**El sistema ahora puede manejar múltiples cargas de trabajo simultáneamente con priorización inteligente!** 🎉
