# ✅ Fase 2 COMPLETADA - Staging de Datos en HDFS

**Fecha**: 28 de octubre de 2025  
**Duración**: ~5 minutos  
**Estado**: ✅ **ÉXITO TOTAL**

---

## 📋 Resumen Ejecutivo

Los datos de MovieLens han sido **cargados y verificados exitosamente** en HDFS:

- ✅ **6 archivos CSV** subidos (885.4 MB)
- ✅ **32.2 millones** de registros totales
- ✅ **100% de integridad** verificada con Spark
- ✅ **Estructura de directorios** creada para todo el pipeline
- ✅ **Permisos** configurados para lectura por Spark

---

## 🎯 Criterios de Aceptación ✓

### 1. Estructura HDFS Creada ✓

```bash
./scripts/recsys-utils.sh hdfs-ls /
```

Directorios creados:
- `/data/movielens/csv` - Datos CSV crudos (885.4 MB)
- `/data/movielens_parquet` - Para ETL Parquet (próxima fase)
- `/models/als` - Para modelo ALS entrenado
- `/streams/ratings` - Para datos de streaming
- `/checkpoints` - Para checkpoints de Spark Streaming

### 2. Archivos CSV Subidos ✓

```bash
./scripts/recsys-utils.sh hdfs-ls /data/movielens/csv
```

| Archivo | Tamaño (bytes) | Registros | Estado |
|---------|---------------|-----------|--------|
| movie.csv | 1,493,648 | 27,278 | ✓ OK |
| rating.csv | 690,353,377 | 20,000,263 | ✓ OK |
| tag.csv | 21,725,514 | 465,564 | ✓ OK |
| genome_tags.csv | 20,363 | 1,128 | ✓ OK |
| genome_scores.csv | 214,322,450 | 11,709,768 | ✓ OK |
| link.csv | 539,334 | 27,278 | ✓ OK |

**Total**: 885.4 MB (~2.6 GB con replicación HDFS)

### 3. Verificación de Integridad ✓

Ejecutado script `verify_csv_integrity.py` con Spark:

```
============================================================
COMPARACIÓN CON DATOS LOCALES:
------------------------------------------------------------
movie.csv                 HDFS:       27,278  Local:    27,278  ✓ MATCH
rating.csv                HDFS:   20,000,263  Local:20,000,263  ✓ MATCH
tag.csv                   HDFS:      465,564  Local:   465,564  ✓ MATCH
genome_tags.csv           HDFS:        1,128  Local:     1,128  ✓ MATCH
genome_scores.csv         HDFS:   11,709,768  Local:11,709,768  ✓ MATCH
link.csv                  HDFS:       27,278  Local:    27,278  ✓ MATCH
------------------------------------------------------------
TOTAL                     HDFS:   32,231,279
============================================================

✅ VERIFICACIÓN EXITOSA: Todos los archivos coinciden
```

**Resultado**: 0 discrepancias, 100% de integridad.

### 4. Schema Validation ✓

Todos los archivos tienen el schema esperado:

**movie.csv**:
- Columnas: `movieId`, `title`, `genres`
- Muestra verificada: "Toy Story (1995)" con géneros correctos

**rating.csv**:
- Columnas: `userId`, `movieId`, `rating`, `timestamp`
- 20M+ ratings de usuarios verificados

**tag.csv**:
- Columnas: `userId`, `movieId`, `tag`, `timestamp`
- Tags de usuarios libres

**genome_tags.csv**:
- Columnas: `tagId`, `tag`
- 1,128 tags del Tag Genome

**genome_scores.csv**:
- Columnas: `movieId`, `tagId`, `relevance`
- 11.7M scores de relevancia tag-película

**link.csv**:
- Columnas: `movieId`, `imdbId`, `tmdbId`
- Enlaces a IMDb y TMDb

### 5. Permisos y Acceso ✓

```bash
docker exec namenode hdfs dfs -ls /data/movielens/csv
```

Permisos: `-rw-r--r--` (lectura para todos, escritura para root)  
Replicación: Factor 3 (configurado en HDFS)  
Usuario: root  
Grupo: supergroup

**Spark puede leer**: ✓ Verificado con job de verificación

---

## 📊 Desglose de Datos

### Registros por Archivo

```
┌──────────────────────┬──────────────┬─────────────┐
│ Archivo              │ Registros    │ % del Total │
├──────────────────────┼──────────────┼─────────────┤
│ rating.csv           │ 20,000,263   │ 62.0%       │
│ genome_scores.csv    │ 11,709,768   │ 36.3%       │
│ tag.csv              │    465,564   │  1.4%       │
│ movie.csv            │     27,278   │  0.1%       │
│ link.csv             │     27,278   │  0.1%       │
│ genome_tags.csv      │      1,128   │  0.0%       │
├──────────────────────┼──────────────┼─────────────┤
│ TOTAL                │ 32,231,279   │ 100.0%      │
└──────────────────────┴──────────────┴─────────────┘
```

### Tamaño por Archivo

```
rating.csv         ████████████████████████████████████ 690 MB (77.8%)
genome_scores.csv  ████████████ 214 MB (24.1%)
tag.csv            █ 21 MB (2.4%)
movie.csv          █ 1.5 MB (0.2%)
link.csv           █ 0.5 MB (0.1%)
genome_tags.csv    █ 20 KB (0.0%)
```

---

## 🔍 Detalles de los Datos

### MovieLens Dataset
- **Versión**: MovieLens 20M (2019)
- **Películas**: 27,278 títulos únicos
- **Usuarios**: ~138,000 (estimado de rating.csv)
- **Ratings**: 20,000,263 valoraciones (escala 0.5-5.0)
- **Tags de usuarios**: 465,564 etiquetas libres
- **Tag Genome**: 1,128 tags con relevancia para 13,816 películas
- **Periodo temporal**: Varios años (verificable en timestamps)

### Género Distribution (a explorar en ETL)
Los géneros están en formato pipe-separated:
```
Adventure|Animation|Children|Comedy|Fantasy
Action|Crime|Thriller
Comedy|Romance
```

Total de géneros únicos: ~20 (estimado)

---

## 🛠️ Herramientas Creadas

### Script de Verificación
**Ubicación**: `scripts/verify_csv_integrity.py`

Funcionalidad:
- Lee todos los CSV desde HDFS con Spark
- Cuenta registros y valida schema
- Compara con conteos locales
- Muestra primeras filas de cada archivo
- Genera reporte detallado

**Ejecución**:
```bash
./scripts/recsys-utils.sh spark-submit scripts/verify_csv_integrity.py
```

**Tiempo de ejecución**: ~2 minutos para 885 MB

---

## 📁 Comandos Ejecutados

### Creación de Estructura
```bash
./scripts/recsys-utils.sh hdfs-mkdir /data/movielens/csv
./scripts/recsys-utils.sh hdfs-mkdir /data/movielens_parquet
./scripts/recsys-utils.sh hdfs-mkdir /models/als
./scripts/recsys-utils.sh hdfs-mkdir /streams/ratings
./scripts/recsys-utils.sh hdfs-mkdir /checkpoints
```

### Carga de Datos
```bash
# Para cada CSV (movie, rating, tag, genome_tags, genome_scores, link)
docker cp Dataset/<file>.csv namenode:/tmp/<file>.csv
docker exec namenode hdfs dfs -put /tmp/<file>.csv /data/movielens/csv/
docker exec namenode rm /tmp/<file>.csv
```

### Verificación
```bash
./scripts/recsys-utils.sh hdfs-ls /data/movielens/csv
./scripts/recsys-utils.sh hdfs-du /data/movielens
./scripts/recsys-utils.sh spark-submit scripts/verify_csv_integrity.py
```

---

## 💾 Uso de Disco HDFS

```bash
./scripts/recsys-utils.sh hdfs-status
```

**Estado del cluster**:
- Capacidad total: 936.8 GB
- Usado: ~2.6 GB (con replicación factor 3)
- Disponible: 771.6 GB
- Uso: 0.3%

**Espacio por directorio**:
```
/data/movielens/csv     885.4 MB (raw)  →  2.6 GB (con replicación 3x)
```

Espacio reservado para próximas fases:
- Parquet (estimado): ~300-400 MB (mejor compresión)
- Modelos ALS: ~50-100 MB
- Datos streaming: depende de retención (configurar truncate)

---

## 🚀 Próximos Pasos (Fase 3)

La infraestructura y datos están listos para el ETL.

### Fase 3: ETL a Parquet Tipado
Objetivos:
1. Leer CSV desde `/data/movielens/csv`
2. Tipar columnas correctamente (int, double, timestamp, string)
3. Limpiar nulos y datos inconsistentes
4. Normalizar géneros (explode pipe-separated)
5. Escribir Parquet optimizado en `/data/movielens_parquet/`

**Archivos a generar**:
- `movies.parquet` - Películas tipadas con géneros normalizados
- `ratings.parquet` - Ratings con tipos correctos, particionado por date
- `tags.parquet` - Tags de usuarios tipados
- `genome_tags.parquet` - Tags del Genome
- `genome_scores.parquet` - Scores de relevancia
- `links.parquet` - Enlaces externos

**Beneficios esperados**:
- ✅ Reducción de tamaño ~60-70% (885 MB → ~300 MB)
- ✅ Lectura 5-10x más rápida
- ✅ Tipos fuertemente tipados (sin parsing)
- ✅ Compresión columnar (Snappy)
- ✅ Particionado eficiente para queries

**Script a crear**: `movies/src/etl/etl_movielens.py`

---

## 📝 Lecciones Aprendidas

### Optimizaciones Aplicadas
1. **Copia a contenedor primero**: Evita timeouts en `docker cp` → `hdfs dfs -put`
2. **Limpieza temporal**: Borrar `/tmp/` del namenode después de cada upload
3. **Verificación con Spark**: Más confiable que `wc -l` para grandes archivos
4. **Replicación HDFS**: Factor 3 aplicado automáticamente (885 MB → 2.6 GB)

### Tiempos de Carga
- movie.csv (1.5 MB): ~2 segundos
- rating.csv (690 MB): ~40 segundos
- genome_scores.csv (214 MB): ~35 segundos
- Resto (~22 MB total): ~5 segundos cada uno

**Total**: ~3 minutos de carga + 2 minutos verificación = **5 minutos**

---

## ✅ Checklist de Completitud

- [x] Estructura HDFS creada (`/data`, `/models`, `/streams`, `/checkpoints`)
- [x] 6 archivos CSV subidos a `/data/movielens/csv`
- [x] Conteos verificados (32.2M registros totales)
- [x] Schema validado para todos los archivos
- [x] Integridad 100% confirmada (conteos locales == HDFS)
- [x] Permisos de lectura para Spark confirmados
- [x] Script de verificación creado y probado
- [x] Documentación generada

---

## 🔍 Verificación Rápida

Para confirmar que todo está OK:

```bash
# Listar archivos
./scripts/recsys-utils.sh hdfs-ls /data/movielens/csv

# Ver uso
./scripts/recsys-utils.sh hdfs-du /data/movielens

# Verificar integridad (2 min)
./scripts/recsys-utils.sh spark-submit scripts/verify_csv_integrity.py
```

**Esperado**:
- 6 archivos CSV visibles
- 885.4 MB de uso (2.6 GB con replicación)
- Verificación exitosa con 0 errores

---

## 📊 Métricas de la Fase

| Métrica | Valor |
|---------|-------|
| Archivos cargados | 6/6 (100%) |
| Registros totales | 32,231,279 |
| Tamaño total (raw) | 885.4 MB |
| Tamaño HDFS (3x repl) | 2.6 GB |
| Integridad | 100% |
| Tiempo total | 5 minutos |
| Errores | 0 |

---

**Fase 2 COMPLETADA** ✅  
**Sistema listo para**: Fase 3 (ETL a Parquet)

---

**Verificado por**: Script Spark automatizado + Validación manual  
**Última verificación**: 2025-10-28 09:50 UTC

Para continuar con la Fase 3:
```bash
# Crear script ETL
vim Recomendacion-Gran-Escala/movies/src/etl/etl_movielens.py

# Ejecutar ETL (próximo paso)
./scripts/recsys-utils.sh spark-submit movies/src/etl/etl_movielens.py
```
