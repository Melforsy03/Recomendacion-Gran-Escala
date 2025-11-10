# 🚀 Comandos Esenciales - Fair Scheduling

## ✅ Sistema Listo

Tu sistema ya está configurado con:
- Worker: 4GB RAM, 4 cores
- Fair Scheduling activado
- 3 pools configurados (streaming, batch, generator)

## 📋 Comandos de Verificación

```bash
# Ver recursos y estado general
./scripts/spark-job-manager.sh resources

# Ver jobs activos
./scripts/spark-job-manager.sh list

# Verificar Spark detallado
./scripts/check-spark-resources.sh
```

## 🎯 Ejecutar Jobs (Sin Conflictos)

### Opción 1: Solo Streaming
```bash
./scripts/run-streaming-processor.sh
```

### Opción 2: Streaming + Generator (Simultáneos)
```bash
# Terminal 1
./scripts/run-streaming-processor.sh

# Terminal 2
./scripts/run-latent-generator.sh 100
```

### Opción 3: Pipeline Completo (3 Jobs)
```bash
# Terminal 1: Streaming
./scripts/run-streaming-processor.sh

# Terminal 2: Generator
./scripts/run-latent-generator.sh 100

# Terminal 3: Analytics (después de 2-3 min)
./scripts/run-batch-analytics.sh
```

## 🛠️ Gestión de Jobs

```bash
# Detener todos los jobs
./scripts/spark-job-manager.sh kill-all

# Reconfigurar fair scheduling (si es necesario)
./scripts/spark-job-manager.sh fair-mode
```

## 🌐 Interfaces Web

```bash
# Spark Master UI
http://localhost:8080

# Spark Worker UI  
http://localhost:8081

# Dashboard de Métricas
http://localhost:8501

# Aplicación Spark (cuando hay job corriendo)
http://localhost:4040
```

## 🔍 Monitoreo

```bash
# Ver logs de streaming
docker logs -f spark-master | grep -i "batch"

# Ver métricas en Kafka
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic metrics \
  --from-beginning

# Ver ratings generados
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic ratings \
  --max-messages 10

# Ver uso de recursos Docker
docker stats spark-master spark-worker
```

## ❓ Troubleshooting Rápido

### Si un job no obtiene recursos:

```bash
# 1. Ver qué está corriendo
./scripts/spark-job-manager.sh list

# 2. Detener todo
./scripts/spark-job-manager.sh kill-all

# 3. Verificar recursos
./scripts/spark-job-manager.sh resources

# 4. Iniciar de nuevo
./scripts/run-streaming-processor.sh
```

### Si Fair Scheduling no funciona:

```bash
# Reconfigurar
./scripts/spark-job-manager.sh fair-mode

# Verificar archivo
docker exec spark-master cat /opt/spark/conf/fairscheduler.xml

# Reiniciar jobs
./scripts/spark-job-manager.sh kill-all
./scripts/run-streaming-processor.sh
```

### Si worker no tiene recursos:

```bash
# Verificar configuración
docker exec spark-worker env | grep SPARK_WORKER

# Debe mostrar:
# SPARK_WORKER_MEMORY=4G
# SPARK_WORKER_CORES=4

# Si no, recrear:
docker compose restart spark-worker
```

## 📊 Distribución de Recursos

```
Worker Total: 4 cores, 4GB RAM

Streaming:  2 cores, 1GB (prioridad ALTA)
Generator:  1 core,  512MB (prioridad BAJA)
Batch:      2 cores, 1GB (prioridad MEDIA)
```

## ✨ Workflow Recomendado

```bash
# 1. Verificar sistema
./scripts/spark-job-manager.sh resources

# 2. Iniciar streaming (prioridad alta)
./scripts/run-streaming-processor.sh

# 3. En otra terminal, generar datos
./scripts/run-latent-generator.sh 100

# 4. Ver dashboard
# Navegador: http://localhost:8501

# 5. (Opcional) Ejecutar analytics
./scripts/run-batch-analytics.sh
```

## 📚 Documentación

- **Este archivo**: Comandos rápidos
- `RESUMEN_SOLUCION_FINAL.md`: Resumen completo
- `docs/FAIR_SCHEDULING_GUIA.md`: Guía detallada
- `docs/SOLUCION_FAIR_SCHEDULING.md`: Solución ejecutiva

---

**Todo listo para ejecutar múltiples jobs simultáneamente!** 🎉
