# Sistema de Recomendación en Gran Escala
## Arquitectura de Big Data con HDFS + YARN + Spark + Kafka

### 📋 Descripción del Sistema

Este proyecto configura una infraestructura completa de Big Data que incluye:

- **HDFS (Hadoop Distributed File System)**: Sistema de archivos distribuido
- **YARN (Yet Another Resource Negotiator)**: Gestor de recursos del cluster
- **Apache Spark**: Motor de procesamiento distribuido (versión 3.4.1)
- **Apache Kafka**: Plataforma de streaming distribuido (versión 3.5)
- **Zookeeper**: Coordinación de servicios distribuidos

### 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA DE ALMACENAMIENTO                    │
│  ┌─────────────┐      ┌─────────────┐                       │
│  │  NameNode   │──────│  DataNode   │  (HDFS)               │
│  └─────────────┘      └─────────────┘                       │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                 CAPA DE GESTIÓN DE RECURSOS                  │
│  ┌──────────────────┐      ┌──────────────┐                 │
│  │ ResourceManager  │──────│ NodeManager  │  (YARN)         │
│  └──────────────────┘      └──────────────┘                 │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   CAPA DE PROCESAMIENTO                      │
│  ┌──────────────┐      ┌──────────────┐                     │
│  │ Spark Master │──────│ Spark Worker │  (Spark 3.4.1)      │
│  └──────────────┘      └──────────────┘                     │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      CAPA DE STREAMING                       │
│  ┌────────────┐      ┌────────────────┐                     │
│  │ Zookeeper  │──────│     Kafka      │  (Kafka 3.5)        │
│  └────────────┘      └────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

### 🚀 Inicio Rápido

#### 1. Levantar todos los servicios

```bash
docker-compose up -d
```

#### 2. Verificar que todos los contenedores están corriendo

```bash
docker-compose ps
```

#### 3. Ejecutar tests de verificación

```bash
# Dar permisos de ejecución
chmod +x *.sh

# Test de conectividad
./test-connectivity.sh

# Test completo (todos los componentes)
./run-all-tests.sh
```

### 🧪 Tests Disponibles

1. **test-connectivity.sh**: Verifica que todos los servicios están accesibles
2. **test-hdfs.sh**: Prueba operaciones básicas de HDFS
3. **test-kafka.sh**: Prueba producción y consumo de mensajes en Kafka
4. **test-spark-standalone.sh**: Ejecuta un job de prueba en Spark
5. **test-spark-kafka.sh**: Prueba la integración Spark Streaming + Kafka
6. **run-all-tests.sh**: Ejecuta todos los tests anteriores

### 🌐 Interfaces Web

Una vez que los servicios estén corriendo, puedes acceder a las siguientes interfaces:

- **HDFS NameNode**: http://localhost:9870
- **YARN ResourceManager**: http://localhost:8088
- **YARN NodeManager**: http://localhost:8042
- **Spark Master**: http://localhost:8080
- **Spark Worker**: http://localhost:8081
- **Spark Application UI**: http://localhost:4040 (cuando hay una app corriendo)

### 🔌 Puertos de Servicios

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| HDFS NameNode | 9000 | RPC |
| HDFS NameNode | 9870 | Web UI |
| YARN ResourceManager | 8032 | RPC |
| YARN ResourceManager | 8088 | Web UI |
| YARN NodeManager | 8042 | Web UI |
| Spark Master | 7077 | RPC |
| Spark Master | 8080 | Web UI |
| Spark Worker | 8081 | Web UI |
| Kafka (Internal) | 9092 | Bootstrap Server |
| Kafka (External) | 9093 | External Access |
| Zookeeper | 2181 | Client Port |

### 📁 Estructura del Proyecto

```
.
├── docker-compose.yml          # Configuración de servicios
├── hadoop-conf/                # Configuraciones de Hadoop/YARN
│   ├── core-site.xml
│   ├── hdfs-site.xml
│   └── yarn-site.xml
├── shared/                     # Directorio compartido entre contenedores
├── test-connectivity.sh        # Test de conectividad
├── test-hdfs.sh               # Test de HDFS
├── test-kafka.sh              # Test de Kafka
├── test-spark-standalone.sh   # Test de Spark
├── test-spark-kafka.sh        # Test de integración Spark+Kafka
└── run-all-tests.sh           # Ejecuta todos los tests
```

### 🔧 Comandos Útiles

#### Docker Compose

```bash
# Iniciar servicios
docker-compose up -d

# Ver logs de todos los servicios
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f spark-master

# Detener servicios
docker-compose down

# Detener y eliminar volúmenes (limpieza completa)
docker-compose down -v

# Reiniciar un servicio específico
docker-compose restart spark-master
```

#### HDFS

```bash
# Listar archivos en HDFS
docker exec namenode hadoop fs -ls /

# Crear directorio
docker exec namenode hadoop fs -mkdir -p /data

# Subir archivo
docker exec namenode hadoop fs -put /shared/archivo.txt /data/

# Descargar archivo
docker exec namenode hadoop fs -get /data/archivo.txt /shared/

# Ver contenido de archivo
docker exec namenode hadoop fs -cat /data/archivo.txt

# Obtener estadísticas
docker exec namenode hadoop fs -df -h
```

#### Kafka

```bash
# Listar topics
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Crear topic
docker exec kafka kafka-topics --create \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 3 \
    --topic mi-topic

# Describir topic
docker exec kafka kafka-topics --describe \
    --bootstrap-server localhost:9092 \
    --topic mi-topic

# Producir mensajes (interactivo)
docker exec -it kafka kafka-console-producer \
    --bootstrap-server localhost:9092 \
    --topic mi-topic

# Consumir mensajes
docker exec kafka kafka-console-consumer \
    --bootstrap-server localhost:9092 \
    --topic mi-topic \
    --from-beginning
```

#### Spark

```bash
# Enviar job a Spark (modo standalone)
docker exec spark-master spark-submit \
    --master spark://spark-master:7077 \
    --class org.apache.spark.examples.SparkPi \
    /opt/spark/examples/jars/spark-examples_2.12-3.4.1.jar \
    10

# Abrir Spark Shell
docker exec -it spark-master spark-shell \
    --master spark://spark-master:7077

# Abrir PySpark
docker exec -it spark-master pyspark \
    --master spark://spark-master:7077

# Enviar job Python
docker exec spark-master spark-submit \
    --master spark://spark-master:7077 \
    /shared/mi_script.py

# Enviar job con dependencias de Kafka (requiere root para descargar dependencias)
docker exec -u root spark-master spark-submit \
    --master spark://spark-master:7077 \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1 \
    /shared/mi_script_kafka.py
```

### 💡 Ejemplo: Spark Streaming con Kafka

```python
from pyspark.sql import SparkSession

# Crear SparkSession
spark = SparkSession.builder \
    .appName("KafkaSparkStreaming") \
    .master("spark://spark-master:7077") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1") \
    .getOrCreate()

# Leer desde Kafka
df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "mi-topic") \
    .option("startingOffsets", "earliest") \
    .load()

# Procesar datos
messages = df.selectExpr("CAST(value AS STRING)")

# Escribir a consola
query = messages \
    .writeStream \
    .outputMode("append") \
    .format("console") \
    .start()

query.awaitTermination()
```

### 🛠️ Configuración de Recursos

Los recursos asignados están configurados en `docker-compose.yml`:

- **YARN NodeManager**: 4GB RAM, 2 vCPUs
- **Spark Worker**: 2GB RAM, 2 Cores
- **Kafka**: 3 particiones por defecto, replicación factor 1

Puedes ajustar estos valores modificando las variables de entorno en el archivo `docker-compose.yml`.

### 🔍 Solución de Problemas

#### Los contenedores no inician

```bash
# Ver logs detallados
docker-compose logs

# Verificar recursos del sistema
docker stats

# Limpiar y reiniciar
docker-compose down -v
docker-compose up -d
```

#### Problemas de conectividad

```bash
# Verificar que todos los servicios están en la misma red
docker network inspect recomendacion-gran-escala_datapipeline

# Verificar DNS interno
docker exec spark-master ping namenode
docker exec spark-master ping kafka
```

#### HDFS no está accesible

```bash
# Verificar estado de NameNode
docker exec namenode hdfs dfsadmin -report

# Verificar logs
docker-compose logs namenode
docker-compose logs datanode
```

### 📊 Monitoreo

Para monitorear el sistema, accede a las interfaces web:

1. **HDFS**: Verifica el estado del cluster, espacio disponible, y bloques
2. **YARN**: Monitorea aplicaciones corriendo, recursos utilizados
3. **Spark**: Verifica jobs activos, executors, y métricas de rendimiento

### 🚢 Crear Imagen Docker Personalizada

Si necesitas crear una imagen personalizada con configuraciones adicionales:

```bash
# Crear Dockerfile para Spark personalizado
cat > Dockerfile.spark << 'EOF'
FROM bitnami/spark:3.4.1

USER root

# Instalar dependencias adicionales
RUN pip install kafka-python pandas numpy

# Copiar scripts personalizados
COPY ./scripts /opt/spark-scripts

USER 1001
EOF

# Construir imagen
docker build -f Dockerfile.spark -t mi-spark:3.4.1 .

# Actualizar docker-compose.yml para usar la nueva imagen
# Cambiar: image: bitnami/spark:3.4.1
# Por: image: mi-spark:3.4.1
```

### 📝 Próximos Pasos

1. ✅ Verificar que todos los servicios están corriendo
2. ✅ Ejecutar los tests de conectividad y funcionalidad
3. ⏭️ Desarrollar tu sistema de recomendación
4. ⏭️ Implementar pipelines de procesamiento de datos
5. ⏭️ Configurar Spark Streaming para datos en tiempo real
6. ⏭️ Optimizar configuraciones según tus necesidades

### 📚 Recursos Adicionales

- [Documentación de Hadoop](https://hadoop.apache.org/docs/)
- [Documentación de Spark](https://spark.apache.org/docs/latest/)
- [Documentación de Kafka](https://kafka.apache.org/documentation/)
- [Spark Structured Streaming + Kafka Guide](https://spark.apache.org/docs/latest/structured-streaming-kafka-integration.html)

### 🤝 Contribuciones

Este es un proyecto educativo para sistemas de recomendación en gran escala. Siéntete libre de adaptarlo a tus necesidades.

### 📄 Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT.

## 🧠 Sistema de Recomendación a Gran Escala (Streaming + Dashboard)

Esta repo incluye un pipeline de referencia para recomendaciones y métricas en tiempo real usando el dataset de ejemplo `movies/data/raw/movies.json`:

Arquitectura lógica:

```text
Kafka topic 'events'  <-- productor simulado (recomendaciones + interacciones)
           │
           ▼
Spark Structured Streaming (metrics_streaming.py)
           │
           ├──► Kafka topic 'metrics' (acceptance_rate, precision, active_users, engagement, top_products)
           ▼
API FastAPI (WebSocket/REST) ───► Dashboard (Chart.js)
```

### Cómo ejecutarlo

1) Inicia la infraestructura:

```bash
./scripts/start-system.sh
```

1) Lanza el job de métricas (Spark Streaming):

```bash
./scripts/run-streaming-metrics.sh
```

1) Arranca el productor de eventos (host):

```bash
./scripts/run-producer-events.sh
```

1) Abre el dashboard en tu navegador:

- API + Dashboard: <http://localhost:8000>

Verás en tiempo real:

- Tasa de aceptación (CTR) y precisión (proxy)
- Productos más sugeridos (Top 10)
- Usuarios activos por minuto
- Impacto en engagement (eventos promedio por usuario)

Notas:

- El tópico Kafka `events` se auto-crea al enviar los primeros mensajes.
- El job publica métricas en `metrics`; la API las consume y hace broadcast por WebSocket.
