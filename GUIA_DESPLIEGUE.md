# 🚀 Guía de Despliegue y Ejecución

**Sistema de Recomendación de Películas en Gran Escala**  
**Fecha de actualización**: 3 de noviembre de 2025  
**Versión**: 1.0

---

## 📋 Tabla de Contenidos

1. [Requisitos Previos](#requisitos-previos)
2. [Despliegue Inicial (Primera Vez)](#despliegue-inicial-primera-vez)
3. [Ejecución Normal (Días Posteriores)](#ejecución-normal-días-posteriores)
4. [Monitoreo y Verificación](#monitoreo-y-verificación)
5. [Detener el Sistema](#detener-el-sistema)
6. [Troubleshooting](#troubleshooting)
7. [Comandos de Referencia Rápida](#comandos-de-referencia-rápida)

---

## 🔧 Requisitos Previos

### Hardware Mínimo
- **RAM**: 8 GB disponibles para Docker
- **Disco**: 20 GB libres
- **CPU**: 4 cores recomendados

### Software Requerido
- **Docker**: 20.10 o superior
- **Docker Compose**: 2.0 o superior
- **Python**: 3.8+ (para scripts auxiliares)

### Verificar Instalación
```bash
# Verificar Docker
docker --version
docker compose version

# Verificar que Docker está corriendo
docker info

# Verificar Python
python3 --version
```

### Puertos Necesarios (Deben estar libres)
- `8000` - API de Recomendaciones
- `8080` - Spark Master UI
- `8081` - Spark Worker UI
- `8088` - YARN ResourceManager UI
- `9000` - HDFS NameNode RPC
- `9092` - Kafka (interno)
- `9093` - Kafka (externo)
- `9870` - HDFS NameNode UI

---

## 🎯 Despliegue Inicial (Primera Vez)

Sigue estos pasos **solo la primera vez** que ejecutas el sistema o después de eliminar los volúmenes de Docker.

### Paso 1: Clonar/Navegar al Proyecto

```bash
cd /home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala
```

### Paso 2: Dar Permisos a Scripts

```bash
chmod +x scripts/*.sh
```

### Paso 3: Iniciar Infraestructura Docker

```bash
./scripts/start-system.sh
```

**Tiempo estimado**: 2-3 minutos  
**Resultado esperado**: 9 contenedores corriendo

Verifica el estado:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

Deberías ver:
- ✅ `namenode` - Up (healthy)
- ✅ `datanode` - Up (healthy)
- ✅ `resourcemanager` - Up (healthy)
- ✅ `nodemanager` - Up (healthy)
- ✅ `spark-master` - Up
- ✅ `spark-worker` - Up
- ✅ `kafka` - Up
- ✅ `zookeeper` - Up
- ✅ `recs-api` - Up

### Paso 4: Ejecutar Suite de Tests

```bash
./scripts/run-all-tests.sh
```

**Tiempo estimado**: 3-5 minutos  
**Resultado esperado**: Todos los tests pasan ✅

Tests ejecutados:
- ✅ Conectividad de servicios
- ✅ HDFS (lectura/escritura)
- ✅ Kafka (topics/producer/consumer)
- ✅ Spark Standalone
- ✅ Spark + Kafka Integration

### Paso 5: Cargar Datos CSV en HDFS

#### 5.1. Crear Estructura de Directorios

```bash
# Crear directorios necesarios
./scripts/recsys-utils.sh hdfs-mkdir /data/movielens/csv
./scripts/recsys-utils.sh hdfs-mkdir /data/movielens_parquet
./scripts/recsys-utils.sh hdfs-mkdir /models/als
./scripts/recsys-utils.sh hdfs-mkdir /streams/ratings
./scripts/recsys-utils.sh hdfs-mkdir /checkpoints
```

#### 5.2. Subir Archivos CSV

```bash
# Asegúrate de estar en el directorio raíz del proyecto
cd /home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala

# Subir los 6 archivos CSV
./scripts/recsys-utils.sh hdfs-put Dataset/movie.csv /data/movielens/csv/
./scripts/recsys-utils.sh hdfs-put Dataset/rating.csv /data/movielens/csv/
./scripts/recsys-utils.sh hdfs-put Dataset/tag.csv /data/movielens/csv/
./scripts/recsys-utils.sh hdfs-put Dataset/genome_tags.csv /data/movielens/csv/
./scripts/recsys-utils.sh hdfs-put Dataset/genome_scores.csv /data/movielens/csv/
./scripts/recsys-utils.sh hdfs-put Dataset/link.csv /data/movielens/csv/
```

**Tiempo estimado**: 5-10 minutos (dependiendo del tamaño de datos)

#### 5.3. Verificar Integridad

```bash
# Listar archivos en HDFS
./scripts/recsys-utils.sh hdfs-ls /data/movielens/csv

# Verificar integridad con Spark
./scripts/recsys-utils.sh spark-submit scripts/verify_csv_integrity.py
```

**Resultado esperado**: 6 archivos con ~32 millones de registros totales

### Paso 6: Ejecutar ETL a Parquet (Fase 3)

```bash
./scripts/recsys-utils.sh spark-submit movies/src/etl/etl_movielens.py
```

**Tiempo estimado**: 10-15 minutos  
**Qué hace**: Convierte CSV a Parquet con schemas tipados y particionado inteligente

Verificar:
```bash
./scripts/recsys-utils.sh spark-submit movies/src/etl/verify_parquet.py
```

### Paso 7: Generar Features de Contenido (Fase 4)

```bash
./scripts/recsys-utils.sh spark-submit movies/src/features/generate_content_features.py
```

**Tiempo estimado**: 5-8 minutos  
**Qué hace**: Crea vectores de features (géneros + genome tags) para cada película

Verificar:
```bash
./scripts/recsys-utils.sh hdfs-ls /data/content_features
```

### Paso 8: Entrenar Modelo ALS (Fase 5)

```bash
./scripts/recsys-utils.sh spark-submit movies/src/models/train_als.py
```

**Tiempo estimado**: 3-5 minutos (con sample del 5%)  
**Qué hace**: Entrena modelo de Collaborative Filtering con ALS

Verificar:
```bash
./scripts/recsys-utils.sh hdfs-ls /models/als
./scripts/recsys-utils.sh hdfs-ls /outputs/als
```

**Resultado esperado**:
- Modelo guardado en `/models/als/model/`
- Recomendaciones top-10 por usuario
- Métricas de evaluación (RMSE, MAE)

### Paso 9: Crear Topics de Kafka (Fase 6)

```bash
python3 movies/src/streaming/create_kafka_topics.py
```

**Tiempo estimado**: 30 segundos  
**Qué hace**: Crea topics `ratings` (6 particiones) y `metrics` (3 particiones)

Verificar:
```bash
./scripts/verify_kafka_phase6.sh
```

### Paso 10: Probar Sistema de Streaming

#### 10.1. Terminal 1 - Generador de Ratings Sintéticos (Fase 7)

```bash
./scripts/run-synthetic-ratings.sh
```

O manualmente:
```bash
./scripts/recsys-utils.sh spark-submit movies/src/streaming/synthetic_ratings_generator.py
```

Deja esta terminal corriendo. Deberías ver:
```
[INFO] Generating synthetic ratings at 50 ratings/sec
[INFO] Published batch of 100 ratings to Kafka
```

#### 10.2. Terminal 2 - Procesador de Streaming (Fase 8)

Abre una **nueva terminal** y ejecuta:

```bash
cd /home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala
./scripts/run-streaming-processor.sh
```

O manualmente:
```bash
./scripts/recsys-utils.sh spark-submit movies/src/streaming/streaming_processor.py
```

Deja esta terminal corriendo. Deberías ver:
```
[INFO] Starting streaming processor
[INFO] Processing window [2025-11-03 10:00:00, 2025-11-03 10:01:00]
[INFO] Processed 3,250 ratings, avg=3.67, p50=3.5, p95=4.5
```

#### 10.3. Terminal 3 - Monitor de Métricas (Opcional)

Abre una **tercera terminal** y ejecuta:

```bash
cd /home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala
./scripts/run-streaming-metrics.sh
```

Deberías ver las métricas en tiempo real.

### Paso 11: Verificar Resultados

```bash
# Ver datos de streaming en HDFS
./scripts/recsys-utils.sh hdfs-ls /streams/ratings/raw
./scripts/recsys-utils.sh hdfs-ls /streams/ratings/agg

# Ver estadísticas
./scripts/recsys-utils.sh hdfs-du /streams
```

---

## 🔄 Ejecución Normal (Días Posteriores)

Después del despliegue inicial, **solo necesitas**:

### 1. Iniciar Infraestructura

```bash
cd /home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala
./scripts/start-system.sh
```

### 2. (Opcional) Verificar Estado

```bash
./scripts/check-status.sh
```

### 3. Iniciar Componentes de Streaming

Si quieres trabajar con streaming:

**Terminal 1 - Generador**:
```bash
./scripts/run-synthetic-ratings.sh
```

**Terminal 2 - Procesador**:
```bash
./scripts/run-streaming-processor.sh
```

**Terminal 3 - Monitor (opcional)**:
```bash
./scripts/run-streaming-metrics.sh
```

### 4. Trabajar con el Sistema

Ahora puedes:
- Acceder a las UIs web (ver sección Monitoreo)
- Ejecutar jobs de Spark
- Consultar datos en HDFS
- Hacer queries con Spark SQL

---

## 📊 Monitoreo y Verificación

### Interfaces Web

Abre estas URLs en tu navegador:

| Servicio | URL | Descripción |
|----------|-----|-------------|
| HDFS NameNode | http://localhost:9870 | Ver archivos, uso de disco |
| YARN ResourceManager | http://localhost:8088 | Ver jobs, recursos |
| Spark Master | http://localhost:8080 | Ver workers, aplicaciones |
| Spark Worker | http://localhost:8081 | Ver tasks, logs |
| API Métricas | http://localhost:8000 | Endpoint de recomendaciones |

### Comandos de Monitoreo

```bash
# Ver estado de contenedores
docker ps

# Ver logs de un servicio
docker logs -f spark-master
docker logs -f kafka
docker logs -f namenode

# Ver recursos de Docker
docker stats

# Ver estado general del sistema
./scripts/check-status.sh

# Ver estructura de HDFS
./scripts/recsys-utils.sh hdfs-ls /

# Ver uso de disco en HDFS
./scripts/recsys-utils.sh hdfs-du /data
./scripts/recsys-utils.sh hdfs-du /models
./scripts/recsys-utils.sh hdfs-du /streams
```

### Verificar Datos en HDFS

```bash
# Datos CSV originales
./scripts/recsys-utils.sh hdfs-ls /data/movielens/csv

# Datos Parquet procesados
./scripts/recsys-utils.sh hdfs-ls /data/movielens_parquet

# Features de contenido
./scripts/recsys-utils.sh hdfs-ls /data/content_features

# Modelo ALS entrenado
./scripts/recsys-utils.sh hdfs-ls /models/als

# Datos de streaming
./scripts/recsys-utils.sh hdfs-ls /streams/ratings/raw
./scripts/recsys-utils.sh hdfs-ls /streams/ratings/agg
```

### Verificar Topics de Kafka

```bash
# Listar topics
./scripts/recsys-utils.sh kafka-topics

# Describir topic ratings
./scripts/recsys-utils.sh kafka-describe ratings

# Consumir últimos mensajes del topic ratings
docker exec kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic ratings \
  --from-beginning \
  --max-messages 10
```

---

## 🛑 Detener el Sistema

### Opción 1: Detener Componentes de Streaming

Si solo quieres detener el streaming pero mantener la infraestructura:

1. Presiona `Ctrl + C` en cada terminal donde corre un proceso de Spark
2. Los contenedores Docker siguen corriendo

### Opción 2: Detener Todo el Sistema

```bash
./scripts/stop-system.sh
```

Esto detiene y elimina todos los contenedores, pero **conserva los datos** en volúmenes Docker.

### Opción 3: Limpieza Completa (¡CUIDADO!)

Si quieres eliminar **TODO** incluyendo datos:

```bash
./scripts/stop-system.sh

# Eliminar volúmenes (PERDERÁS TODOS LOS DATOS)
docker volume prune -f
```

⚠️ **ADVERTENCIA**: Solo usa esto si quieres empezar desde cero.

---

## 🔧 Troubleshooting

### Problema: Contenedores no inician

**Síntoma**: `docker ps` no muestra 9 contenedores

**Solución**:
```bash
# Ver logs de errores
docker compose logs

# Reintentar inicio
./scripts/stop-system.sh
./scripts/start-system.sh
```

### Problema: Puertos en uso

**Síntoma**: Error "port already in use"

**Solución**:
```bash
# Identificar proceso usando el puerto (ejemplo: 8080)
sudo lsof -i :8080

# Detener el proceso o cambiar puerto en docker-compose.yml
```

### Problema: HDFS no accesible

**Síntoma**: Error "Connection refused" al ejecutar comandos HDFS

**Solución**:
```bash
# Verificar que namenode está corriendo
docker ps | grep namenode

# Ver logs del namenode
docker logs namenode

# Reiniciar namenode si es necesario
docker restart namenode
```

### Problema: Kafka no recibe mensajes

**Síntoma**: Producer funciona pero consumer no recibe nada

**Solución**:
```bash
# Verificar topics
./scripts/recsys-utils.sh kafka-topics

# Ver logs de Kafka
docker logs kafka

# Recrear topics si es necesario
python3 movies/src/streaming/create_kafka_topics.py
```

### Problema: Spark job falla por memoria

**Síntoma**: Error "OutOfMemoryError" en logs de Spark

**Solución**:
```bash
# Aumentar memoria en docker-compose.yml para spark-worker:
# SPARK_WORKER_MEMORY: 4g  (en vez de 2g)

# Reiniciar servicios
docker compose down
docker compose up -d
```

### Problema: Datos no aparecen en HDFS después de subir

**Síntoma**: `hdfs-ls` no muestra archivos

**Solución**:
```bash
# Verificar que el comando put funcionó
./scripts/recsys-utils.sh hdfs-put Dataset/movie.csv /data/movielens/csv/

# Verificar espacio en HDFS
./scripts/recsys-utils.sh hdfs-status

# Verificar permisos
docker exec namenode hdfs dfs -ls -R /data
```

### Problema: Script no tiene permisos

**Síntoma**: "Permission denied" al ejecutar script

**Solución**:
```bash
chmod +x scripts/*.sh
```

---

## 📚 Comandos de Referencia Rápida

### Infraestructura

```bash
# Iniciar sistema
./scripts/start-system.sh

# Detener sistema
./scripts/stop-system.sh

# Ver estado
./scripts/check-status.sh
docker ps

# Ver logs
docker logs -f <nombre-contenedor>
```

### HDFS

```bash
# Listar directorio
./scripts/recsys-utils.sh hdfs-ls <path>

# Crear directorio
./scripts/recsys-utils.sh hdfs-mkdir <path>

# Subir archivo
./scripts/recsys-utils.sh hdfs-put <local-file> <hdfs-path>

# Descargar archivo
./scripts/recsys-utils.sh hdfs-get <hdfs-path> <local-path>

# Eliminar
./scripts/recsys-utils.sh hdfs-rm <path>

# Ver uso de disco
./scripts/recsys-utils.sh hdfs-du <path>

# Estado del cluster
./scripts/recsys-utils.sh hdfs-status
```

### Spark

```bash
# Ejecutar job de Spark
./scripts/recsys-utils.sh spark-submit <script.py>

# Ver aplicaciones corriendo
# Ir a http://localhost:8080

# Ver logs de aplicación
docker logs spark-master
docker logs spark-worker
```

### Kafka

```bash
# Listar topics
./scripts/recsys-utils.sh kafka-topics

# Describir topic
./scripts/recsys-utils.sh kafka-describe <topic-name>

# Consumir mensajes
docker exec kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic <topic-name> \
  --from-beginning
```

### Pipeline Completo

```bash
# ETL
./scripts/recsys-utils.sh spark-submit movies/src/etl/etl_movielens.py

# Features
./scripts/recsys-utils.sh spark-submit movies/src/features/generate_content_features.py

# Entrenar modelo
./scripts/recsys-utils.sh spark-submit movies/src/models/train_als.py

# Streaming
./scripts/run-synthetic-ratings.sh      # Terminal 1
./scripts/run-streaming-processor.sh    # Terminal 2
./scripts/run-streaming-metrics.sh      # Terminal 3
```

---

## 🎯 Checklist de Despliegue

### Primera Vez
- [ ] Requisitos instalados (Docker, Python)
- [ ] Permisos a scripts (`chmod +x`)
- [ ] Infraestructura iniciada (9 contenedores)
- [ ] Tests pasados (suite completa)
- [ ] Directorios HDFS creados
- [ ] CSVs subidos a HDFS (6 archivos)
- [ ] Integridad verificada
- [ ] ETL Parquet ejecutado
- [ ] Features generadas
- [ ] Modelo ALS entrenado
- [ ] Topics Kafka creados
- [ ] Streaming probado

### Ejecución Normal
- [ ] Infraestructura iniciada
- [ ] Estado verificado
- [ ] Streaming iniciado (si necesario)
- [ ] UIs accesibles

---

## 📞 Soporte

### Archivos de Documentación

- `README.md` - Documentación general del proyecto
- `INICIO.md` - Guía de inicio rápido
- `docs/FASE*_RESUMEN.md` - Documentación de cada fase
- `docs/COMANDOS_RAPIDOS.md` - Referencia de comandos

### Verificación de Fases

```bash
# Ver qué fases se han completado
ls -la docs/FASE*_RESUMEN.md

# Leer resumen de una fase específica
cat docs/FASE8_RESUMEN.md
```

---

**Última actualización**: 3 de noviembre de 2025  
**Autor**: Sistema de Recomendación - Equipo de Desarrollo  
**Contacto**: [Tu contacto aquí]
