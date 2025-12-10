# Ejemplos de Salida - Sistema de Recomendación

Ejemplos reales de las salidas esperadas al ejecutar scripts del sistema.

---

## 🎯 Entrenamiento

### Primera Ejecución (Modelos No Existen)

```bash
$ ./scripts/train_all_models.sh
```

**Salida:**
```
═══════════════════════════════════════════════════════════════
   🎯 ENTRENAMIENTO DE MODELOS DE RECOMENDACIÓN
═══════════════════════════════════════════════════════════════
📅 Fecha: 2024-01-15 10:30:45
🖥️  Host: ml-workstation
👤 Usuario: abraham
🚀 Modo: ENTRENAR MODELOS FALTANTES
══════════════════════════════════════════════════════════════

[1/6] 🔍 Verificando entorno virtual...
   ✅ Creando entorno virtual en .venv-training/

[2/6] 📦 Instalando dependencias...
   ✅ PySpark 3.4.1
   ✅ pandas 2.1.4
   ✅ numpy 1.24.3

[3/6] ☕ Verificando Java...
   ✅ Java versión: openjdk 17.0.9

[4/6] 💾 Verificando memoria...
   ✅ RAM disponible: 16 GB

[5/6] 📂 Verificando datasets...
   ✅ rating.csv (20,000,263 registros)
   ✅ movie.csv (27,278 películas)
   ✅ genome_scores.csv
   ✅ genome_tags.csv

[6/6] 🚀 Iniciando entrenamiento...

═══════════════════════════════════════════════════════════════
                  ENTRENANDO MODELO ALS
═══════════════════════════════════════════════════════════════

[INFO] Cargando datos desde Dataset/...
[INFO] Total de valoraciones: 20,000,263
[INFO] Usuarios únicos: 138,493
[INFO] Películas únicas: 26,744
[INFO] División train/test: 80%/20%

[INFO] Configuración ALS:
   - rank: 20
   - maxIter: 10
   - regParam: 0.1
   - coldStartStrategy: drop

[INFO] Entrenando modelo... (esto puede tardar varios minutos)
[PROGRESS] Iteración 1/10... Loss: 1.234
[PROGRESS] Iteración 2/10... Loss: 0.987
[PROGRESS] Iteración 3/10... Loss: 0.843
...
[PROGRESS] Iteración 10/10... Loss: 0.521

[INFO] Calculando métricas en conjunto de prueba...
   ✅ RMSE: 0.8234
   ✅ MAE:  0.6431
   ✅ MSE:  0.6780
   ✅ R²:   0.7845

[INFO] Guardando modelo en:
   📂 movies/trained_models/als/model_20240115_103045/
   🔗 Symlink: model_latest → model_20240115_103045

═══════════════════════════════════════════════════════════════
              ENTRENANDO MODELO ITEM-CF
═══════════════════════════════════════════════════════════════

[INFO] Cargando valoraciones y genome scores...
[INFO] Calculando matriz de similitud entre películas...
[INFO] Aplicando pesos de genome tags...
[INFO] Guardando matriz de similitud (26744 x 26744)

   ✅ Modelo Item-CF guardado
   📂 movies/trained_models/item_cf/model_20240115_104523/

═══════════════════════════════════════════════════════════════
          ENTRENAMIENTO COMPLETADO CON ÉXITO
═══════════════════════════════════════════════════════════════

📊 Resumen de Modelos Entrenados:
   ✅ ALS (RMSE: 0.8234)
   ✅ Item-CF
   ✅ Content-Based
   ✅ Hybrid

📁 Directorio de salida: movies/trained_models/

🎉 Siguiente paso: ./scripts/copy_models_to_containers.sh
```

---

### Segunda Ejecución (Modelos Ya Existen)

```bash
$ ./scripts/train_all_models.sh
```

**Salida:**
```
═══════════════════════════════════════════════════════════════
   🎯 ENTRENAMIENTO DE MODELOS DE RECOMENDACIÓN
═══════════════════════════════════════════════════════════════
📅 Fecha: 2024-01-15 11:15:30
🖥️  Host: ml-workstation
👤 Usuario: abraham
🚀 Modo: OMITIR MODELOS EXISTENTES
══════════════════════════════════════════════════════════════

[1/6] 🔍 Verificando entorno virtual...
   ✅ Usando entorno existente .venv-training/

[2/6] 📦 Verificando dependencias...
   ✅ Todas las dependencias instaladas

[3/6] ☕ Verificando Java...
   ✅ Java versión: openjdk 17.0.9

[4/6] 💾 Verificando memoria...
   ✅ RAM disponible: 14 GB

[5/6] 📂 Verificando datasets...
   ✅ Todos los datasets presentes

[6/6] 🚀 Verificando modelos...

═══════════════════════════════════════════════════════════════

⏭️ Modelo ALS ya existe, omitiendo entrenamiento
   📂 Ubicación: movies/trained_models/als/model_20240115_103045
   📅 Entrenado: 2024-01-15 10:30:45
   📊 RMSE: 0.8234

⏭️ Modelo ITEM_CF ya existe, omitiendo entrenamiento
   📂 Ubicación: movies/trained_models/item_cf/model_20240115_104523
   📅 Entrenado: 2024-01-15 10:45:23

⏭️ Modelo CONTENT_BASED ya existe, omitiendo entrenamiento
   📂 Ubicación: movies/trained_models/content_based/model_20240115_105312

⏭️ Modelo HYBRID ya existe, omitiendo entrenamiento
   📂 Ubicación: movies/trained_models/hybrid/model_20240115_105820

═══════════════════════════════════════════════════════════════
          TODOS LOS MODELOS YA ENTRENADOS
═══════════════════════════════════════════════════════════════

ℹ️  Para re-entrenar, usa: ./scripts/train_all_models.sh --force

⏱️ Tiempo total: 2 segundos
```

---

### Forzar Re-Entrenamiento

```bash
$ ./scripts/train_all_models.sh --force
```

**Salida:**
```
═══════════════════════════════════════════════════════════════
   🎯 ENTRENAMIENTO DE MODELOS DE RECOMENDACIÓN
═══════════════════════════════════════════════════════════════
📅 Fecha: 2024-01-15 12:00:00
🖥️  Host: ml-workstation
👤 Usuario: abraham
🚀 Modo: FORZAR RE-ENTRENAMIENTO
⚠️  ADVERTENCIA: Se re-entrenarán todos los modelos
══════════════════════════════════════════════════════════════

[...proceso completo de entrenamiento...]

═══════════════════════════════════════════════════════════════
          ENTRENAMIENTO COMPLETADO CON ÉXITO
═══════════════════════════════════════════════════════════════

📊 Nuevos Modelos:
   ✅ ALS (RMSE: 0.8198) [↑ Mejora: 0.0036]
   ✅ Item-CF
   ✅ Content-Based
   ✅ Hybrid

⏱️ Tiempo total: 45 minutos
```

---

## 🚀 Despliegue

### Verificar Modelos en Docker

```bash
$ ./scripts/copy_models_to_containers.sh
```

**Salida:**
```
═══════════════════════════════════════════════════════════════
   🚢 VERIFICACIÓN DE MODELOS EN CONTENEDORES
═══════════════════════════════════════════════════════════════

[1/4] 🔍 Verificando modelos locales...
   ✅ ALS: model_20240115_103045
   ✅ Item-CF: model_20240115_104523
   ✅ Content-Based: model_20240115_105312
   ✅ Hybrid: model_20240115_105820

[2/4] 🐳 Verificando volúmenes Docker...
   ✅ Volume mounted: /app/trained_models
   ✅ Modelo ALS accesible en contenedor

[3/4] 🔄 Reiniciando servicio API...
   ⏳ Deteniendo contenedor api...
   ✅ Contenedor detenido
   ⏳ Iniciando contenedor api...
   ✅ Contenedor iniciado
   ⏳ Esperando inicialización (30s)...

[4/4] 🏥 Verificando health check...
   ✅ API respondiendo en http://localhost:8000
   ✅ Health check: OK
   ✅ Modelo ALS cargado correctamente

═══════════════════════════════════════════════════════════════
          DEPLOYMENT VERIFICADO CON ÉXITO
═══════════════════════════════════════════════════════════════

🎉 Sistema listo para servir recomendaciones!

📝 Prueba el API:
   curl http://localhost:8000/recommendations/recommend/123?n=10
```

---

## 🧪 Pruebas de API

### Obtener Recomendaciones

```bash
$ curl http://localhost:8000/recommendations/recommend/123?n=5
```

**Respuesta:**
```json
{
  "user_id": 123,
  "recommendations": [
    {
      "movie_id": 2571,
      "title": "Matrix, The (1999)",
      "score": 4.87,
      "rank": 1
    },
    {
      "movie_id": 296,
      "title": "Pulp Fiction (1994)",
      "score": 4.76,
      "rank": 2
    },
    {
      "movie_id": 318,
      "title": "Shawshank Redemption, The (1994)",
      "score": 4.72,
      "rank": 3
    },
    {
      "movie_id": 858,
      "title": "Godfather, The (1972)",
      "score": 4.68,
      "rank": 4
    },
    {
      "movie_id": 50,
      "title": "Usual Suspects, The (1995)",
      "score": 4.65,
      "rank": 5
    }
  ],
  "model": "als",
  "cached": false,
  "latency_ms": 234
}
```

---

## 🔥 Simulación de Tráfico

### Ejecución del Simulador

```bash
$ python scripts/simulate_traffic.py --rate 50 --duration 60
```

**Salida en Tiempo Real:**
```
═══════════════════════════════════════════════════════════════
   🔥 SIMULADOR DE TRÁFICO - API RECOMENDACIONES
═══════════════════════════════════════════════════════════════
⚙️  Configuración:
   - URL Base: http://localhost:8000
   - Tasa: 50 req/s
   - Duración: 60 segundos
   - Total esperado: ~3000 peticiones
══════════════════════════════════════════════════════════════

[00:05] 📊 Enviadas: 250  |  ✅ OK: 248  |  ❌ Error: 2  |  ⚡ P95: 145ms
[00:10] 📊 Enviadas: 500  |  ✅ OK: 496  |  ❌ Error: 4  |  ⚡ P95: 152ms
[00:15] 📊 Enviadas: 750  |  ✅ OK: 743  |  ❌ Error: 7  |  ⚡ P95: 148ms
[00:20] 📊 Enviadas: 1000 |  ✅ OK: 991  |  ❌ Error: 9  |  ⚡ P95: 156ms
...
[00:60] 📊 Enviadas: 3000 |  ✅ OK: 2987 |  ❌ Error: 13 |  ⚡ P95: 163ms

═══════════════════════════════════════════════════════════════
                  RESUMEN FINAL
═══════════════════════════════════════════════════════════════

📊 Peticiones:
   - Total enviadas: 3000
   - ✅ Exitosas: 2987 (99.57%)
   - ❌ Fallidas: 13 (0.43%)

⚡ Latencias:
   - P50 (mediana): 87ms
   - P95: 163ms
   - P99: 287ms
   - Promedio: 102ms

🚀 Throughput:
   - Peticiones/seg: 49.78
   - Duración real: 60.24s

📁 Logs guardados:
   - Detalle: logs/traffic_simulation_20240115_120530.jsonl
   - Resumen: logs/traffic_summary_20240115_120530.json

✅ Simulación completada exitosamente!
```

---

## 🏥 Health Check

```bash
$ curl http://localhost:8000/recommendations/health
```

**Respuesta:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_type": "als",
  "model_version": "model_20240115_103045",
  "spark_version": "3.4.1",
  "cache_size": 847,
  "uptime_seconds": 3642,
  "timestamp": "2024-01-15T12:30:45Z"
}
```

---

## ⚠️ Errores Comunes

### Error: Modelo No Encontrado

```bash
$ ./scripts/copy_models_to_containers.sh
```

**Salida:**
```
═══════════════════════════════════════════════════════════════
   🚢 VERIFICACIÓN DE MODELOS EN CONTENEDORES
═══════════════════════════════════════════════════════════════

[1/4] 🔍 Verificando modelos locales...
   ❌ ERROR: Modelo ALS no encontrado!

📍 Ubicación esperada: movies/trained_models/als/model_latest

💡 Solución: Ejecuta primero el entrenamiento:
   ./scripts/train_all_models.sh
```

---

### Error: Java No Instalado

```bash
$ ./scripts/train_all_models.sh
```

**Salida:**
```
[3/6] ☕ Verificando Java...
   ❌ ERROR: Java no encontrado!

💡 Instala Java 8+ con:
   Ubuntu/Debian: sudo apt install openjdk-17-jre
   MacOS: brew install openjdk@17

⚠️  Entrenamiento abortado.
```

---

### Error: Memoria Insuficiente

```bash
$ ./scripts/train_all_models.sh
```

**Salida:**
```
[4/6] 💾 Verificando memoria...
   ⚠️  ADVERTENCIA: RAM disponible: 4 GB
   ⚠️  Recomendado: 8 GB o más

⚠️  El entrenamiento puede fallar o ser muy lento.

Continuar de todos modos? (s/n): n

Entrenamiento cancelado por el usuario.
```

---

## 📖 Referencias

- Ver documentación completa: `docs/GUIA_ENTRENAMIENTO_DESPLIEGUE.md`
- Scripts disponibles: `scripts/README.md`
- Troubleshooting: `docs/TROUBLESHOOTING.md` (si existe)
