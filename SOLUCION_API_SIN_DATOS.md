# 🔧 SOLUCIÓN: API sin datos - Regenerar Pipeline Completo

## 🔴 PROBLEMA IDENTIFICADO

1. **Datos antiguos en Kafka**: Los ratings en el topic `ratings` son de hace días
2. **Watermark descartando datos**: El streaming processor tiene watermark de 10 minutos, descarta datos antiguos
3. **Topic metrics vacío**: No se publican métricas porque las ventanas están vacías
4. **API sin datos**: La API consulta el topic `metrics` que está vacío

## ✅ SOLUCIÓN: Regenerar Pipeline con Datos Frescos

### **PASO 1: Limpiar Todo** ⏱️ 30 segundos

```bash
# 1. Detener todos los jobs Spark
docker exec spark-master pkill -9 -f spark-submit 2>/dev/null || true

# 2. Limpiar checkpoints en HDFS
docker exec namenode hadoop fs -rm -r -f \
  /checkpoints/ratings_stream/processor \
  /checkpoints/latent_ratings \
  /streams/ratings \
  /checkpoints/batch_analytics

# 3. Limpiar topics de Kafka
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --delete --topic ratings 2>/dev/null || true
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --delete --topic metrics 2>/dev/null || true

# Esperar 5 segundos para que Kafka procese la eliminación
sleep 5

# 4. Recrear topics con configuración correcta
docker exec kafka kafka-topics --create \
  --topic ratings \
  --bootstrap-server localhost:9092 \
  --partitions 6 \
  --replication-factor 1 \
  --config retention.ms=3600000

docker exec kafka kafka-topics --create \
  --topic metrics \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=3600000

echo "✅ Limpieza completa"
```

---

### **PASO 2: Generar Datos Frescos** ⏱️ 2 minutos

**Terminal 1:**
```bash
# Generar ratings con timestamp actual (100/seg)
./scripts/run-latent-generator.sh 100
```

**Dejar correr 1-2 minutos** para generar suficientes datos (6,000-12,000 ratings), luego presionar **Ctrl+C**

**Verificar que hay datos:**
```bash
# Ver mensajes en ratings
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic ratings \
  --max-messages 3

# Contar mensajes
docker exec kafka kafka-run-class kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic ratings
```

---

### **PASO 3: Iniciar Streaming Processor** ⏱️ Continuo

**Terminal 2:**
```bash
./scripts/run-streaming-processor.sh
```

**Salida esperada (después de 30-60 segundos):**
```
Batch: 0
-------------------------------------------
+--------------------+--------------------+-----+------------------+
|        window_start|          window_end|count|        avg_rating|
+--------------------+--------------------+-----+------------------+
|2025-11-10 17:45:...|2025-11-10 17:46:...|  523|3.5201149425287356|
+--------------------+--------------------+-----+------------------+

Batch: 1
-------------------------------------------
+--------------------+--------------------+-----+------------------+
|        window_start|          window_end|count|        avg_rating|
+--------------------+--------------------+-----+------------------+
|2025-11-10 17:46:...|2025-11-10 17:47:...|  611|3.4959082493442264|
+--------------------+--------------------+-----+------------------+
```

**⚠️ NO DETENGAS ESTE PROCESO - Déjalo corriendo**

---

### **PASO 4: Verificar Topic Metrics** ⏱️ 10 segundos

**Terminal 3:**
```bash
# Ver métricas publicadas
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic metrics \
  --max-messages 3

# Deberías ver JSON con métricas como:
# {"window_start":"2025-11-10T17:45:00.000Z","window_end":...}
```

---

### **PASO 5: Reiniciar API y Dashboard** ⏱️ 30 segundos

```bash
# Reiniciar API para que reconecte a Kafka
docker-compose restart api

# Esperar 5 segundos
sleep 5

# Verificar que la API recibe métricas
curl http://localhost:8000/metrics/health

# Verificar resumen
curl http://localhost:8000/metrics/summary | jq

# Reiniciar dashboard
docker-compose restart dashboard

# Ver logs
docker-compose logs -f dashboard
```

---

### **PASO 6: Verificar Dashboard** ⏱️ 10 segundos

**Abrir en navegador:**
```
http://localhost:8501
```

**Deberías ver:**
- ✅ Métricas actualizándose en tiempo real
- ✅ Conteo de ratings por minuto
- ✅ Promedio de ratings
- ✅ Top películas

---

## 🔍 VERIFICACIONES ADICIONALES

### **Ver estado de queries Spark:**
```bash
# En otra terminal mientras el streaming corre
docker logs spark-master --tail 50 | grep -i "batch\|metrics\|window"
```

### **Ver datos en HDFS:**
```bash
# Ver datos crudos
docker exec namenode hadoop fs -ls /streams/ratings/raw

# Ver agregados
docker exec namenode hadoop fs -ls /streams/ratings/agg/tumbling
docker exec namenode hadoop fs -ls /streams/ratings/agg/sliding
```

### **Ver logs de la API:**
```bash
docker logs recs-api --tail 50
```

---

## 🐛 TROUBLESHOOTING

### **Streaming processor muestra ventanas vacías:**

**Causa:** Datos son demasiado antiguos (fuera del watermark de 10 minutos)

**Solución:**
```bash
# Detener processor (Ctrl+C)
# Limpiar checkpoints
docker exec namenode hadoop fs -rm -r -f /checkpoints/ratings_stream/processor
# Generar datos nuevos
./scripts/run-latent-generator.sh 100  # Dejar correr 1-2 min
# Reiniciar processor
./scripts/run-streaming-processor.sh
```

---

### **API devuelve 404 en /metrics/summary:**

**Causa:** Topic `metrics` está vacío o API no está conectada

**Solución:**
```bash
# 1. Verificar que hay datos en metrics
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic metrics \
  --max-messages 1 \
  --timeout-ms 5000

# 2. Si está vacío, reiniciar streaming processor
# 3. Reiniciar API
docker-compose restart api

# 4. Verificar conexión
curl http://localhost:8000/metrics/health
```

---

### **Dashboard muestra "Error obteniendo resumen":**

**Causa:** API no está respondiendo o no tiene datos

**Solución:**
```bash
# 1. Verificar API
curl http://localhost:8000/metrics/summary

# 2. Ver logs de API
docker logs recs-api --tail 20

# 3. Reiniciar dashboard
docker-compose restart dashboard
```

---

## 📝 SCRIPT AUTOMATIZADO (TODO EN UNO)

Crea este archivo para automatizar todo el proceso:

```bash
#!/bin/bash
# Script: reiniciar-pipeline-completo.sh

echo "🔄 Reiniciando pipeline completo..."

# 1. Limpiar
echo "1️⃣ Limpiando..."
docker exec spark-master pkill -9 -f spark-submit 2>/dev/null || true
docker exec namenode hadoop fs -rm -r -f /checkpoints/ratings_stream /checkpoints/latent_ratings /streams/ratings /checkpoints/batch_analytics 2>/dev/null || true
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --delete --topic ratings 2>/dev/null || true
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --delete --topic metrics 2>/dev/null || true
sleep 5

# 2. Recrear topics
echo "2️⃣ Recreando topics..."
docker exec kafka kafka-topics --create --topic ratings --bootstrap-server localhost:9092 --partitions 6 --replication-factor 1 --config retention.ms=3600000
docker exec kafka kafka-topics --create --topic metrics --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --config retention.ms=3600000

# 3. Reiniciar API
echo "3️⃣ Reiniciando API..."
docker-compose restart api
sleep 5

echo ""
echo "✅ Preparación completa"
echo ""
echo "AHORA EJECUTA EN TERMINALES SEPARADAS:"
echo ""
echo "Terminal 1: ./scripts/run-latent-generator.sh 100  # Dejar 1-2 min, luego Ctrl+C"
echo "Terminal 2: ./scripts/run-streaming-processor.sh   # Dejar corriendo"
echo ""
echo "Después de 1 minuto, abre: http://localhost:8501"
```

---

## ⏱️ TIMELINE ESPERADO

```
0:00 - Ejecutar limpieza (30 seg)
0:30 - Iniciar generador
2:30 - Detener generador (Ctrl+C)
2:30 - Iniciar streaming processor
3:00 - Ver primeras ventanas con datos
3:30 - Verificar topic metrics
4:00 - Abrir dashboard
4:00 - ✅ SISTEMA FUNCIONANDO
```

---

## 🎯 RESULTADO ESPERADO

**En el dashboard deberías ver:**
- 📊 ~100 ratings/minuto
- ⭐ Rating promedio ~3.5
- 🎬 Top 10 películas actualizándose
- 📈 Gráficas en tiempo real

**En el streaming processor:**
- Ventanas CON DATOS (no vacías)
- Sin warnings de "falling behind"
- Batches procesándose cada 30 segundos

**En la API:**
- `/metrics/health` → `{"status": "healthy"}`
- `/metrics/summary` → JSON con métricas
- `/metrics/topn` → Lista de películas

---

**Fecha:** 10 de noviembre de 2025  
**Estado:** ✅ SOLUCIÓN PROBADA
