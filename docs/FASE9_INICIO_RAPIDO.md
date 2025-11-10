# 🚀 Guía Rápida - Fase 9: Analytics y Dashboard

## Inicio Rápido (5 minutos)

### 1. Prerequisitos
```bash
# Verificar que el sistema esté corriendo
docker ps | grep -E "(namenode|kafka|spark|api)"

# Si no está corriendo, iniciar todo
./scripts/start-system.sh
```

### 2. Generar Datos de Streaming
```bash
# Terminal 1: Generar ratings (100/seg durante unos minutos)
./scripts/run-latent-generator.sh 100

# Terminal 2: Procesar streaming (dejar corriendo)
./scripts/run-streaming-processor.sh
```

### 3. Ejecutar Analytics Batch
```bash
# Una vez que haya datos (esperar 2-3 minutos)
./scripts/run-batch-analytics.sh
```

### 4. Iniciar Dashboard
```bash
# Primera vez: construir imagen
docker-compose build dashboard

# Iniciar servicio
docker-compose up -d dashboard

# Ver logs
docker-compose logs -f dashboard
```

### 5. Acceder al Dashboard
**Abrir en navegador**: http://localhost:8501

---

## Verificación

```bash
# Verificar todo
./scripts/verify_fase9.sh
```

---

## Accesos Rápidos

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Dashboard** | http://localhost:8501 | Visualizaciones en tiempo real |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **API Health** | http://localhost:8000/metrics/health | Estado del sistema |
| **SSE Stream** | http://localhost:8000/metrics/stream | Server-Sent Events |
| **Spark UI** | http://localhost:8080 | Monitoreo de jobs |
| **HDFS UI** | http://localhost:9870 | Explorador de archivos |

---

## Comandos Útiles

### Consultar Analytics
```bash
# Ver distribución global
docker exec namenode hadoop fs -ls /outputs/analytics/distributions/global

# Ver películas trending
docker exec namenode hadoop fs -ls /outputs/analytics/trending/trending_movies

# Listar todos los outputs
docker exec namenode hadoop fs -ls -R /outputs/analytics
```

### Probar API
```bash
# Health check
curl http://localhost:8000/metrics/health | jq

# Resumen de métricas
curl http://localhost:8000/metrics/summary | jq

# Top-10 películas
curl "http://localhost:8000/metrics/topn?limit=10" | jq '.movies[] | {title, score}'
```

### Ver Logs
```bash
# Dashboard
docker-compose logs -f dashboard

# API
docker-compose logs -f api

# Spark (últimas 100 líneas)
docker logs spark-master --tail 100
```

### Reiniciar Servicios
```bash
# Reiniciar dashboard
docker-compose restart dashboard

# Reiniciar API
docker-compose restart api

# Reconstruir dashboard
docker-compose up -d --build dashboard
```

---

## Troubleshooting Rápido

### Dashboard no muestra datos
```bash
# 1. Verificar que la API esté respondiendo
curl http://localhost:8000/metrics/health

# 2. Verificar que el procesador streaming esté corriendo
docker logs spark-master | grep processor

# 3. Reiniciar API
docker-compose restart api
```

### Analytics batch falla
```bash
# Verificar que existan datos de streaming
docker exec namenode hadoop fs -ls /streams/ratings/raw

# Ver logs de Spark
docker logs spark-master --tail 50
```

### API no responde
```bash
# Ver logs de la API
docker logs recs-api --tail 50

# Reiniciar API
docker-compose restart api

# Reconstruir API
docker-compose up -d --build api
```

---

## Flujo Completo de Prueba

```bash
# 1. Limpiar datos anteriores (opcional)
docker exec namenode hadoop fs -rm -r /streams/ratings
docker exec namenode hadoop fs -rm -r /outputs/analytics

# 2. Generar datos frescos (2-3 minutos)
./scripts/run-latent-generator.sh 100
# (Ctrl+C después de 2-3 minutos)

# 3. Procesar streaming (background)
./scripts/run-streaming-processor.sh &
sleep 60  # Esperar 1 minuto

# 4. Ejecutar analytics
./scripts/run-batch-analytics.sh

# 5. Verificar
./scripts/verify_fase9.sh

# 6. Abrir dashboard
xdg-open http://localhost:8501  # Linux
# open http://localhost:8501     # macOS
```

---

## Características del Dashboard

✅ **Auto-refresh**: Actualización automática cada 5 segundos
✅ **Gráficos interactivos**: Hover para ver detalles
✅ **Filtros configurables**: Ajustar intervalo de refresh
✅ **Múltiples vistas**: Métricas, Top-N, Géneros, Historial
✅ **Responsive**: Se adapta al tamaño de pantalla

---

## Próximos Pasos

1. **Explorar analytics batch**: Ver distribuciones y trending en HDFS
2. **Probar endpoints API**: Swagger UI en http://localhost:8000/docs
3. **Experimentar con SSE**: Conectar cliente personalizado
4. **Ajustar parámetros**: Throughput del generador, ventanas de agregación
5. **Escalar el sistema**: Más workers de Spark, particiones de Kafka

---

**Documentación completa**: `docs/FASE9_RESUMEN.md`
