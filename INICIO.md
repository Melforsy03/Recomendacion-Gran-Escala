# 🚀 GUÍA DE INICIO - Sistema de Recomendación en Gran Escala

## ✅ Tu sistema está listo!

He configurado un entorno completo de Big Data con las siguientes mejoras:

### 📦 Componentes Instalados y Configurados

1. **HDFS + YARN (Hadoop 3.2.1)**
   - NameNode con Web UI en puerto 9870
   - DataNode para almacenamiento distribuido
   - ResourceManager para gestión de recursos YARN
   - NodeManager para ejecución de tareas
   - Configuraciones de compatibilidad optimizadas

2. **Apache Spark 3.4.1**
   - Spark Master en modo cluster
   - Spark Worker con 2GB RAM y 2 cores
   - Soporte completo para YARN
   - Integración con Kafka mediante Spark Streaming
   - Configuraciones de hadoop-conf montadas

3. **Apache Kafka 3.5 + Zookeeper 3.9**
   - Kafka broker con 3 particiones por defecto
   - Zookeeper para coordinación
   - Puertos internos (9092) y externos (9093)
   - Auto-creación de topics habilitada

4. **Health Checks**
   - Verificaciones de salud para todos los servicios
   - Reintentos automáticos configurados

### 🔧 Archivos de Configuración Creados

```
Recomendacion-Gran-Escala/
├── docker-compose.yml              # Configuración de todos los servicios
├── hadoop-conf/                    # Configuraciones de Hadoop/YARN
│   ├── core-site.xml
│   ├── hdfs-site.xml
│   └── yarn-site.xml
├── shared/                         # Directorio compartido entre contenedores
├── examples/                       # Ejemplos de código listos para usar
│   ├── batch_processing.py
│   ├── streaming_recommendation.py
│   ├── kafka_producer.py
│   ├── requirements.txt
│   └── README.md
├── Scripts de gestión:
│   ├── start-system.sh            # Inicia todo el sistema
│   ├── stop-system.sh             # Detiene el sistema
│   └── quickstart.sh              # Guía interactiva
├── Scripts de prueba:
│   ├── test-connectivity.sh       # Verifica conectividad
│   ├── test-hdfs.sh              # Prueba HDFS
│   ├── test-kafka.sh             # Prueba Kafka
│   ├── test-spark-standalone.sh  # Prueba Spark
│   ├── test-spark-kafka.sh       # Prueba integración Spark+Kafka
│   └── run-all-tests.sh          # Ejecuta todos los tests
└── README.md                      # Documentación completa
```

### 🎯 Instrucciones de Uso

#### PASO 1: Iniciar el Sistema

```bash
./start-system.sh
```

Este script:
- Verifica que Docker esté corriendo
- Levanta todos los contenedores
- Espera a que los servicios estén listos
- Muestra las URLs de las interfaces web

**Tiempo estimado**: 2-3 minutos

#### PASO 2: Verificar Conectividad

```bash
./test-connectivity.sh
```

Este script verifica:
- ✓ HDFS NameNode (Web UI y RPC)
- ✓ YARN ResourceManager y NodeManager
- ✓ Spark Master y Worker
- ✓ Kafka y Zookeeper

#### PASO 3: Ejecutar Tests de Funcionalidad

```bash
./run-all-tests.sh
```

Este script ejecuta:
1. Test de conectividad
2. Test de HDFS (crear, leer, listar archivos)
3. Test de Kafka (crear topic, producir, consumir)
4. Test de Spark standalone (calcular Pi)
5. Test de integración Spark + Kafka

**Tiempo estimado**: 5-10 minutos

#### PASO 4: Acceder a las Interfaces Web

Una vez iniciado el sistema, abre en tu navegador:

- **HDFS NameNode**: http://localhost:9870
  - Ver estado del cluster HDFS
  - Explorar archivos
  - Ver estadísticas

- **YARN ResourceManager**: http://localhost:8088
  - Ver aplicaciones corriendo
  - Monitorear recursos
  - Ver historial de jobs

- **YARN NodeManager**: http://localhost:8042
  - Ver contenedores corriendo
  - Logs de aplicaciones

- **Spark Master**: http://localhost:8080
  - Ver workers conectados
  - Aplicaciones Spark corriendo
  - Recursos asignados

- **Spark Worker**: http://localhost:8081
  - Ver tareas ejecutándose
  - Logs del worker

### 🧪 Ejecutar Ejemplos

#### Ejemplo 1: Procesamiento Batch

```bash
cd examples

# Copiar al contenedor Spark
docker cp batch_processing.py spark-master:/tmp/

# Ejecutar
docker exec spark-master spark-submit \
    --master spark://spark-master:7077 \
    /tmp/batch_processing.py
```

Este ejemplo muestra:
- Crear DataFrames con datos de ratings
- Calcular rating promedio por item
- Identificar items más populares
- Analizar actividad de usuarios

#### Ejemplo 2: Streaming en Tiempo Real

**Terminal 1 - Crear topic y ejecutar Spark Streaming:**

```bash
# Crear topic
docker exec kafka kafka-topics --create \
    --bootstrap-server localhost:9092 \
    --replication-factor 1 \
    --partitions 3 \
    --topic ratings

# Copiar script
docker cp examples/streaming_recommendation.py spark-master:/tmp/

# Ejecutar Spark Streaming
docker exec -u root spark-master spark-submit \
    --master spark://spark-master:7077 \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1 \
    /tmp/streaming_recommendation.py
```

**Terminal 2 - Ejecutar productor de datos:**

```bash
cd examples

# Instalar dependencias (solo primera vez)
pip install -r requirements.txt

# Ejecutar productor
python kafka_producer.py
```

Este ejemplo muestra:
- Leer streams desde Kafka en tiempo real
- Procesar datos con ventanas de tiempo
- Detectar items trending
- Calcular estadísticas en tiempo real

### 🔍 Verificar que Todo Funciona

#### 1. Verificar contenedores corriendo:

```bash
docker-compose ps
```

Deberías ver 8 contenedores corriendo:
- namenode
- datanode
- resourcemanager
- nodemanager
- spark-master
- spark-worker
- zookeeper
- kafka

#### 2. Ver logs de un servicio:

```bash
docker-compose logs -f spark-master
```

#### 3. Verificar conectividad entre servicios:

```bash
# Desde Spark, verificar acceso a HDFS
docker exec spark-master hdfs dfs -ls /

# Desde Spark, verificar acceso a Kafka
docker exec spark-master nc -zv kafka 9092
```

### 📊 Comandos Útiles

#### Docker Compose:

```bash
# Ver estado
docker-compose ps

# Ver logs
docker-compose logs -f

# Reiniciar un servicio
docker-compose restart spark-master

# Detener todo
./stop-system.sh
```

#### HDFS:

```bash
# Listar archivos
docker exec namenode hadoop fs -ls /

# Crear directorio
docker exec namenode hadoop fs -mkdir -p /data

# Subir archivo
docker exec namenode hadoop fs -put /shared/file.txt /data/

# Descargar archivo
docker exec namenode hadoop fs -get /data/file.txt /shared/
```

#### Kafka:

```bash
# Listar topics
docker exec kafka kafka-topics --list \
    --bootstrap-server localhost:9092

# Ver mensajes de un topic
docker exec kafka kafka-console-consumer \
    --bootstrap-server localhost:9092 \
    --topic ratings \
    --from-beginning
```

#### Spark:

```bash
# Abrir PySpark shell
docker exec -it spark-master pyspark \
    --master spark://spark-master:7077

# Ver aplicaciones corriendo
docker exec spark-master curl -s http://localhost:8080/json/
```

### 🎓 Próximos Pasos para tu Proyecto

1. ✅ **Sistema configurado** - Verificado y funcionando

2. 📝 **Explorar ejemplos** - Ejecuta y modifica los ejemplos incluidos

3. 🔬 **Desarrollar tu modelo**:
   - Carga tus datos en HDFS
   - Implementa algoritmos de recomendación (ALS, CF, etc.)
   - Entrena modelos con Spark MLlib
   - Evalúa métricas de rendimiento

4. 🌊 **Implementar streaming**:
   - Recibe ratings en tiempo real con Kafka
   - Procesa con Spark Streaming
   - Actualiza recomendaciones en tiempo real

5. 📈 **Escalar**:
   - Añade más workers de Spark
   - Añade más datanodes de HDFS
   - Configura replicación en Kafka

### 🐛 Solución de Problemas

#### Problema: Los contenedores no inician

**Solución:**
```bash
# Limpiar todo y reiniciar
docker-compose down -v
docker system prune -f
./start-system.sh
```

#### Problema: Spark no puede conectar con HDFS

**Solución:**
```bash
# Verificar NameNode
docker exec namenode hdfs dfsadmin -report

# Verificar configuración
docker exec spark-master cat /opt/hadoop-conf/core-site.xml
```

#### Problema: Kafka no acepta mensajes

**Solución:**
```bash
# Verificar que Kafka está corriendo
docker exec kafka kafka-broker-api-versions \
    --bootstrap-server localhost:9092

# Verificar que el topic existe
docker exec kafka kafka-topics --list \
    --bootstrap-server localhost:9092
```

### 💡 Recursos y Documentación

- **README.md**: Documentación completa del proyecto
- **examples/README.md**: Guía de los ejemplos de código
- **Documentación oficial**:
  - [Spark](https://spark.apache.org/docs/latest/)
  - [Kafka](https://kafka.apache.org/documentation/)
  - [Hadoop](https://hadoop.apache.org/docs/)

### 🎉 ¡Listo para Empezar!

Tu sistema está completamente configurado y listo para usar. Todos los componentes son compatibles entre sí y están optimizados para trabajar juntos.

**Ejecuta ahora:**

```bash
./quickstart.sh
```

Para una guía interactiva o:

```bash
./start-system.sh
./run-all-tests.sh
```

Para iniciar y verificar todo automáticamente.

---

**¡Buena suerte con tu proyecto de Sistema de Recomendación en Gran Escala!** 🚀
