# Comandos Rápidos - Sistema de Recomendación

Referencia rápida de comandos útiles para operar el sistema.

# Comandos Rápidos - Sistema de Recomendación

## 🎯 Guía Rápida de Operaciones

---

## � **FASE 3: ETL PARQUET** (✅ COMPLETADA)

### Ejecutar ETL completo
```bash
./scripts/recsys-utils.sh spark-submit movies/src/etl/etl_movielens.py
```

### Verificar datos Parquet
```bash
./scripts/recsys-utils.sh spark-submit movies/src/etl/verify_parquet.py
```

### Ver tamaños en HDFS
```bash
./scripts/recsys-utils.sh hdfs-du /data/movielens_parquet
```

### Listar particiones de ratings
```bash
docker exec namenode hdfs dfs -ls -R /data/movielens_parquet/ratings | head -50
```

---

## 🚀 **INICIO RÁPIDO DEL SISTEMA**

```bash
# Iniciar el sistema completo
cd /home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala
docker compose up -d

# Verificar estado
./scripts/recsys-utils.sh status

# Ejecutar tests
bash scripts/run-all-tests.sh
```

## 📊 Monitoreo

### UIs Web
```bash
# Abrir todas las interfaces
./scripts/recsys-utils.sh open-uis

# O manualmente:
firefox http://localhost:9870  # HDFS NameNode
firefox http://localhost:8088  # YARN ResourceManager
firefox http://localhost:8080  # Spark Master
firefox http://localhost:8081  # Spark Worker
firefox http://localhost:8000  # API Métricas
```

### Estado de Contenedores
```bash
# Ver todos los contenedores
docker ps

# Logs de un servicio específico
docker logs -f spark-master
docker logs -f kafka
docker logs -f namenode

# Estado de recursos
docker stats
```

## 💾 HDFS

### Operaciones Básicas
```bash
# Listar raíz
./scripts/recsys-utils.sh hdfs-ls /

# Crear directorio
./scripts/recsys-utils.sh hdfs-mkdir /data/movielens/csv

# Subir archivo
./scripts/recsys-utils.sh hdfs-put Dataset/movie.csv /data/movielens/csv/movie.csv

# Ver uso de disco
./scripts/recsys-utils.sh hdfs-du /data

# Eliminar
./scripts/recsys-utils.sh hdfs-rm /test

# Reporte del cluster
./scripts/recsys-utils.sh hdfs-status
```

### Comandos Directos (desde namenode)
```bash
# Listar
docker exec namenode hdfs dfs -ls /data

# Crear directorio
docker exec namenode hdfs dfs -mkdir -p /data/movielens/csv

# Ver contenido de archivo
docker exec namenode hdfs dfs -cat /data/test.txt

# Copiar de HDFS a local
docker exec namenode hdfs dfs -get /data/file.txt /tmp/

# Info de archivo
docker exec namenode hdfs dfs -stat "%n %b bytes" /data/file.parquet
```

## 📨 Kafka

### Topics
```bash
# Listar topics
./scripts/recsys-utils.sh kafka-topics

# Crear topic
./scripts/recsys-utils.sh kafka-create ratings 6 1
./scripts/recsys-utils.sh kafka-create metrics 3 1

# Describir topic
./scripts/recsys-utils.sh kafka-describe ratings

# Eliminar topic
./scripts/recsys-utils.sh kafka-delete test-topic
```

### Producir/Consumir
```bash
# Consumir mensajes (últimos 10)
./scripts/recsys-utils.sh kafka-consume ratings 10

# Consumir en tiempo real (desde el inicio)
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic ratings \
  --from-beginning

# Producir mensajes interactivos
./scripts/recsys-utils.sh kafka-produce ratings
# Luego escribe JSON, ej: {"userId":1,"movieId":50,"rating":4.5,"timestamp":1234567890}
# Ctrl+D para terminar

# Producir desde archivo
cat mensajes.json | docker exec -i kafka kafka-console-producer \
  --bootstrap-server localhost:9092 \
  --topic ratings
```

### Info de Consumer Groups
```bash
# Listar grupos
docker exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --list

# Describir grupo
docker exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group my-consumer-group \
  --describe
```

## ⚡ Spark

### Submit Jobs
```bash
# Job batch simple
./scripts/recsys-utils.sh spark-submit jobs/etl_movielens.py

# Job con Kafka (streaming)
./scripts/recsys-utils.sh spark-submit-kafka streaming/generate_ratings.py

# Con argumentos
./scripts/recsys-utils.sh spark-submit jobs/train_als.py --rank 64 --maxIter 10
```

### Ejecución Manual
```bash
# Copiar script al contenedor
docker cp jobs/mi_script.py spark-master:/tmp/

# Ejecutar batch
docker exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  --conf spark.sql.shuffle.partitions=200 \
  /tmp/mi_script.py

# Ejecutar streaming (con Kafka)
docker exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1 \
  --conf spark.streaming.backpressure.enabled=true \
  /tmp/streaming_job.py
```

### PySpark Shell Interactivo
```bash
# Shell normal
docker exec -it spark-master pyspark \
  --master spark://spark-master:7077

# Con Kafka
docker exec -it spark-master pyspark \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1
```

### Monitoreo
```bash
# Ver aplicaciones activas
curl -s http://localhost:8080/json/ | jq '.activeapps'

# Ver workers
curl -s http://localhost:8080/json/ | jq '.aliveworkers'

# Logs de aplicación
docker exec spark-master cat /opt/spark/logs/spark--org.apache.spark.deploy.master.Master-1-*.out
```

## 🔧 Utilidades

### Limpieza
```bash
# Limpiar topics de prueba
./scripts/recsys-utils.sh kafka-delete test-topic
./scripts/recsys-utils.sh kafka-delete test-streaming

# Limpiar datos de prueba HDFS
./scripts/recsys-utils.sh hdfs-rm /test
./scripts/recsys-utils.sh hdfs-rm /tmp

# Limpiar volúmenes Docker (CUIDADO: datos permanentes)
docker compose down -v
```

### Reinicio de Servicios
```bash
# Reiniciar todo
docker compose restart

# Reiniciar servicio específico
docker compose restart spark-master
docker compose restart kafka

# Parar y arrancar
docker compose down
docker compose up -d
```

### Debugging
```bash
# Entrar a contenedor
docker exec -it spark-master bash
docker exec -it namenode bash
docker exec -it kafka bash

# Ver variables de entorno
docker exec spark-master env | grep SPARK

# Test de red (ping entre contenedores)
docker exec spark-master ping -c 3 namenode
docker exec spark-master ping -c 3 kafka

# Verificar puertos
docker exec spark-master netstat -tuln | grep 7077
docker exec kafka netstat -tuln | grep 9092
```

## 📦 Dataset (MovieLens)

### Subir a HDFS (Fase 2)
```bash
# Crear estructura
./scripts/recsys-utils.sh hdfs-mkdir /data/movielens/csv
./scripts/recsys-utils.sh hdfs-mkdir /data/movielens_parquet
./scripts/recsys-utils.sh hdfs-mkdir /models/als
./scripts/recsys-utils.sh hdfs-mkdir /streams/ratings

# Subir CSVs (loop)
cd /home/abraham/Escritorio/PGVD
for file in Dataset/*.csv; do
    filename=$(basename "$file")
    ./Recomendacion-Gran-Escala/scripts/recsys-utils.sh hdfs-put \
        "$file" "/data/movielens/csv/$filename"
    echo "✓ Uploaded: $filename"
done

# Verificar
./scripts/recsys-utils.sh hdfs-ls /data/movielens/csv
./scripts/recsys-utils.sh hdfs-du /data/movielens/csv
```

### Contar Registros
```bash
# Desde PySpark (interactivo)
docker exec -it spark-master pyspark --master spark://spark-master:7077

# Dentro de PySpark:
movies = spark.read.option("header", True).csv("hdfs://namenode:9000/data/movielens/csv/movie.csv")
movies.count()
movies.show(5)
```

## 🎯 Workflows Completos

### Desarrollo Local
```bash
# 1. Editar script
vim jobs/mi_nuevo_job.py

# 2. Ejecutar
./scripts/recsys-utils.sh spark-submit jobs/mi_nuevo_job.py

# 3. Ver logs
docker logs spark-master --tail 100

# 4. Verificar output HDFS
./scripts/recsys-utils.sh hdfs-ls /outputs/mi_job
```

### Pipeline Completo (ejemplo)
```bash
# ETL
./scripts/recsys-utils.sh spark-submit jobs/etl_movielens.py

# Features
./scripts/recsys-utils.sh spark-submit jobs/build_features.py

# Entrenamiento
./scripts/recsys-utils.sh spark-submit jobs/train_als.py

# Streaming (background)
./scripts/recsys-utils.sh spark-submit-kafka streaming/generate_ratings.py &
./scripts/recsys-utils.sh spark-submit-kafka streaming/process_ratings.py &

# Monitorear Kafka
./scripts/recsys-utils.sh kafka-consume metrics 100
```

## 📊 Verificaciones de Salud

### Checklist Rápido
```bash
# 1. Contenedores
docker ps | grep -E "(namenode|spark|kafka)" | wc -l
# Debe ser >= 9

# 2. HDFS
docker exec namenode hdfs dfsadmin -safemode get
# Debe decir: Safe mode is OFF

# 3. Kafka
docker exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092 | head -1
# Debe mostrar versión

# 4. Spark
curl -s http://localhost:8080/json/ | jq -r '.status'
# Debe decir: ALIVE
```

### Script de Health Check
```bash
#!/bin/bash
echo "=== Health Check ==="
echo "HDFS NameNode: $(curl -s http://localhost:9870 > /dev/null && echo OK || echo FAIL)"
echo "YARN RM: $(curl -s http://localhost:8088 > /dev/null && echo OK || echo FAIL)"
echo "Spark Master: $(curl -s http://localhost:8080 > /dev/null && echo OK || echo FAIL)"
echo "Kafka: $(docker exec kafka kafka-topics --list --bootstrap-server localhost:9092 > /dev/null 2>&1 && echo OK || echo FAIL)"
```

---

## 🆘 Solución de Problemas

### Contenedor no inicia
```bash
# Ver logs
docker logs <nombre_contenedor>

# Reiniciar
docker compose restart <nombre_servicio>

# Forzar recreación
docker compose up -d --force-recreate <nombre_servicio>
```

### HDFS en Safe Mode
```bash
docker exec namenode hdfs dfsadmin -safemode leave
```

### Kafka no acepta conexiones
```bash
# Verificar Zookeeper primero
docker logs zookeeper --tail 50

# Reiniciar Kafka
docker compose restart zookeeper
sleep 10
docker compose restart kafka
```

### Spark job falla con OOM
```bash
# Ajustar memoria en docker-compose.yml:
# SPARK_WORKER_MEMORY=4G
# SPARK_EXECUTOR_MEMORY=2G

docker compose up -d --force-recreate spark-worker
```

---

**Referencia rápida creada para**: Sistema de Recomendación de Películas  
**Última actualización**: 2025-10-28
