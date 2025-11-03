# ⚡ Inicio Rápido - Sistema de Recomendación

**Guía condensada para iniciar el sistema rápidamente**

---

## 🚀 Primera Vez (Despliegue Completo)

```bash
# 1. Navegar al proyecto
cd /home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala

# 2. Dar permisos
chmod +x scripts/*.sh

# 3. Iniciar infraestructura
./scripts/start-system.sh

# 4. Verificar
./scripts/run-all-tests.sh

# 5. Crear directorios HDFS
./scripts/recsys-utils.sh hdfs-mkdir /data/movielens/csv
./scripts/recsys-utils.sh hdfs-mkdir /data/movielens_parquet
./scripts/recsys-utils.sh hdfs-mkdir /models/als
./scripts/recsys-utils.sh hdfs-mkdir /streams/ratings
./scripts/recsys-utils.sh hdfs-mkdir /checkpoints

# 6. Subir datos CSV
./scripts/recsys-utils.sh hdfs-put Dataset/movie.csv /data/movielens/csv/
./scripts/recsys-utils.sh hdfs-put Dataset/rating.csv /data/movielens/csv/
./scripts/recsys-utils.sh hdfs-put Dataset/tag.csv /data/movielens/csv/
./scripts/recsys-utils.sh hdfs-put Dataset/genome_tags.csv /data/movielens/csv/
./scripts/recsys-utils.sh hdfs-put Dataset/genome_scores.csv /data/movielens/csv/
./scripts/recsys-utils.sh hdfs-put Dataset/link.csv /data/movielens/csv/

# 7. Ejecutar pipeline de procesamiento
./scripts/recsys-utils.sh spark-submit movies/src/etl/etl_movielens.py
./scripts/recsys-utils.sh spark-submit movies/src/features/generate_content_features.py
./scripts/recsys-utils.sh spark-submit movies/src/models/train_als.py

# 8. Configurar Kafka
python3 movies/src/streaming/create_kafka_topics.py

# 9. Iniciar streaming (en 3 terminales diferentes)
# Terminal 1:
./scripts/run-synthetic-ratings.sh

# Terminal 2:
./scripts/run-streaming-processor.sh

# Terminal 3 (opcional):
./scripts/run-streaming-metrics.sh
```

**Tiempo total estimado**: 30-45 minutos

---

## 🔄 Días Posteriores (Inicio Normal)

```bash
# 1. Navegar al proyecto
cd /home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala

# 2. Iniciar infraestructura
./scripts/start-system.sh

# 3. Verificar estado (opcional)
./scripts/check-status.sh

# 4. Iniciar streaming (en terminales separadas)
# Terminal 1:
./scripts/run-synthetic-ratings.sh

# Terminal 2:
./scripts/run-streaming-processor.sh
```

**Tiempo total**: 2-3 minutos

---

## 📊 Interfaces Web

Una vez iniciado el sistema, abre en tu navegador:

- **HDFS**: http://localhost:9870
- **YARN**: http://localhost:8088
- **Spark Master**: http://localhost:8080
- **Spark Worker**: http://localhost:8081
- **API**: http://localhost:8000

---

## 🛑 Detener Sistema

```bash
# Opción 1: Solo detener streaming
# Presiona Ctrl+C en cada terminal de Spark

# Opción 2: Detener todo (conserva datos)
./scripts/stop-system.sh

# Opción 3: Limpieza completa (ELIMINA DATOS)
./scripts/stop-system.sh
docker volume prune -f
```

---

## 🔍 Verificación Rápida

```bash
# Ver contenedores
docker ps

# Ver datos en HDFS
./scripts/recsys-utils.sh hdfs-ls /data
./scripts/recsys-utils.sh hdfs-ls /models
./scripts/recsys-utils.sh hdfs-ls /streams

# Ver topics Kafka
./scripts/recsys-utils.sh kafka-topics

# Ver estado general
./scripts/check-status.sh
```

---

## 🆘 Problemas Comunes

### Contenedores no inician
```bash
./scripts/stop-system.sh
./scripts/start-system.sh
```

### Puerto en uso
```bash
sudo lsof -i :8080  # Cambiar puerto según error
```

### Sin permisos en script
```bash
chmod +x scripts/*.sh
```

### HDFS no responde
```bash
docker restart namenode
```

---

## 📚 Documentación Completa

Para más detalles, consulta:

- `GUIA_DESPLIEGUE.md` - Guía completa de despliegue
- `README.md` - Documentación general
- `docs/FASE*_RESUMEN.md` - Documentación por fases
- `docs/COMANDOS_RAPIDOS.md` - Referencia de comandos

---

**Última actualización**: 3 de noviembre de 2025
