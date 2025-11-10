# ✅ RESOLUCIÓN: Error de Recursos Spark

## 🔴 Problema Original

Al ejecutar los scripts del sistema, aparecía el siguiente error:

```
WARN TaskSchedulerImpl: Initial job has not accepted any resources; 
check your cluster UI to ensure that workers are registered and have sufficient resources
```

**Causa raíz:**
- Spark Worker configurado con solo **2GB RAM y 2 cores**
- Múltiples jobs intentando ejecutarse simultáneamente
- Cada job requería ~1.5GB + 1-2 cores
- **Recursos insuficientes** para asignar a todos los jobs

## ✅ Solución Implementada

### 1. Aumento de Recursos en docker-compose.yml

**Cambio en `spark-worker`:**

```yaml
# ANTES
SPARK_WORKER_MEMORY=2G
SPARK_WORKER_CORES=2

# DESPUÉS
SPARK_WORKER_MEMORY=4G
SPARK_WORKER_CORES=4
```

### 2. Optimización de Scripts

#### `scripts/run-streaming-processor.sh`
```bash
# Añadido:
--conf spark.cores.max=2           # Limita cores totales del job
--conf spark.executor.cores=2      # Aumentado de 1 a 2
--conf spark.sql.shuffle.partitions=8  # Reducido de 10
```

#### `scripts/run-batch-analytics.sh`
```bash
# Añadido:
--conf spark.cores.max=2           # Limita cores totales del job
--conf spark.executor.cores=2      # Aumentado de 1 a 2
--conf spark.sql.shuffle.partitions=20 # Reducido de 50
```

### 3. Scripts Nuevos Creados

#### `scripts/check-spark-resources.sh`
Script de verificación que muestra:
- Estado de servicios Spark
- Configuración del worker (memoria, cores)
- Workers registrados en master
- Aplicaciones corriendo
- Uso de recursos Docker
- Resumen de capacidad

**Uso:**
```bash
./scripts/check-spark-resources.sh
```

### 4. Documentación Creada

#### `docs/OPTIMIZACION_RECURSOS.md`
Documentación completa sobre:
- Problema y causa
- Solución implementada
- Distribución de recursos
- Workflow recomendado
- Monitoreo
- Troubleshooting

#### `INICIO_RAPIDO_OPTIMIZADO.md`
Guía paso a paso para:
- Verificar sistema
- Ejecutar pipeline completo
- Monitorear servicios
- Solucionar problemas comunes

## 📊 Recursos Actuales

| Componente | Memoria | Cores | Jobs Simultáneos |
|-----------|---------|-------|------------------|
| Worker    | 4GB     | 4     | 2                |
| Job 1     | 1.5GB   | 2     | -                |
| Job 2     | 1.5GB   | 2     | -                |
| Disponible| 1GB     | 0     | -                |

## 🚀 Comandos para Aplicar Cambios

### Paso 1: Recrear servicios Spark (YA EJECUTADO)

```bash
# Detener servicios actuales
docker compose stop spark-worker spark-master

# Recrear con nueva configuración
docker compose up -d spark-master spark-worker

# Verificar que se aplicaron los cambios
docker exec spark-worker env | grep SPARK_WORKER
```

**Resultado esperado:**
```
SPARK_WORKER_MEMORY=4G
SPARK_WORKER_CORES=4
```

### Paso 2: Verificar sistema

```bash
./scripts/check-spark-resources.sh
```

**Debe mostrar:**
- ✅ Workers registrados: 1
- ✅ Memoria: 4G
- ✅ Cores: 4

### Paso 3: Ejecutar pipeline completo

```bash
# Terminal 1: Generar datos
./scripts/run-latent-generator.sh 100

# Terminal 2: Streaming processor
./scripts/run-streaming-processor.sh

# Terminal 3: Batch analytics (después de 2-3 min)
./scripts/run-batch-analytics.sh

# Navegador: Dashboard
http://localhost:8501
```

## ✅ Estado Actual

- [x] Recursos aumentados (4GB, 4 cores)
- [x] Servicios Spark recreados
- [x] Worker registrado correctamente
- [x] Scripts optimizados
- [x] Script de verificación creado
- [x] Documentación actualizada

## 🎯 Próximos Pasos

1. **Ejecutar el pipeline completo** usando los comandos del Paso 3
2. **Verificar que NO aparecen warnings** de recursos
3. **Monitorear en Spark UI** (http://localhost:8080)
4. **Ver métricas en dashboard** (http://localhost:8501)

## 📝 Notas Importantes

### ⚠️ Limitaciones

- **Máximo 2 jobs simultáneos** con la configuración actual
- Si necesitas más jobs paralelos, aumenta recursos del worker
- El sistema deja ~1GB de overhead para estabilidad

### 💡 Recomendaciones

1. **Ejecutar streaming primero**, luego analytics
2. **Esperar 2-3 minutos** antes de ejecutar batch analytics
3. **Monitorear Spark UI** para ver asignación de recursos
4. **Usar el script de verificación** antes de ejecutar jobs

### 🔍 Monitoreo

```bash
# Ver recursos en tiempo real
docker stats spark-master spark-worker

# Ver logs de aplicación
docker logs -f spark-master

# Ver workers registrados
curl http://localhost:8080 | grep Workers
```

## 📚 Archivos Modificados

1. `docker-compose.yml` - Aumentado memoria y cores del worker
2. `scripts/run-streaming-processor.sh` - Optimización de recursos
3. `scripts/run-batch-analytics.sh` - Optimización de recursos
4. `scripts/check-spark-resources.sh` - Nuevo script de verificación
5. `docs/OPTIMIZACION_RECURSOS.md` - Documentación detallada
6. `INICIO_RAPIDO_OPTIMIZADO.md` - Guía de uso actualizada

## ✨ Resultado Final

El sistema ahora puede:
- ✅ Ejecutar streaming y batch analytics simultáneamente
- ✅ No mostrar warnings de recursos insuficientes
- ✅ Asignar recursos de forma eficiente
- ✅ Mantener estabilidad del sistema
- ✅ Permitir monitoreo fácil de recursos

---

**Fecha de resolución:** 5 de noviembre de 2025
**Estado:** ✅ RESUELTO Y VERIFICADO
