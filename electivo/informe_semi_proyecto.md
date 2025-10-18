# 🎬 Informe del Semi-Proyecto — Análisis de Películas con Big Data

## 🧠 Descripción del Proyecto

**Objetivo:**  
Procesar, analizar y visualizar información de un dataset de películas utilizando tecnologías del ecosistema **Big Data (HDFS, YARN y Spark)**.  
El proyecto busca construir un pipeline completo que simule un flujo real de análisis distribuido, incluyendo etapas de **ingesta, limpieza, procesamiento y análisis** de datos a gran escala.

---

## 🎞️ Dataset Seleccionado

**Nombre:** `movies.json`  
**Fuente:** Dataset simulado con información de películas (nombre, puntuación, géneros, popularidad, descripción).  
**Formato:** JSON (convertido a Parquet para procesamiento eficiente con Spark).

**Ejemplo de registro:**
```json
{
  "ID": 1,
  "name": "The Godfather",
  "puan": 9.2,
  "genre_1": "Crime",
  "genre_2": "Drama",
  "pop": 99,
  "description": "A timeless saga of a mafia family and their pursuit of power and loyalty."
}
```

---

## 📊 Justificación del Dataset

### Volumen  
El dataset puede escalarse fácilmente, permitiendo simular **volúmenes masivos de datos** al duplicar o combinar distintas fuentes.  
Su estructura uniforme lo hace ideal para probar rendimiento de Spark y almacenamiento distribuido en HDFS.

### Características  
- Campos heterogéneos (numéricos, categóricos, texto).  
- Atributos derivados (niveles de popularidad, categorías de rating).  
- Compatible con distintos formatos de almacenamiento (JSON, Parquet).  
- Permite análisis de tipo **exploratorio y predictivo**.

### Pertinencia  
Permite aplicar el ciclo completo del procesamiento Big Data:
1. **Ingesta de datos** desde archivos JSON locales.  
2. **Carga y persistencia en HDFS.**  
3. **Procesamiento distribuido con Spark sobre YARN.**  
4. **Análisis exploratorio local y visualización de métricas clave.**

---

## ⚙️ Arquitectura Propuesta

### Tipo de enfoque:  
**Híbrido (Batch + Streaming Simulado)**  
- **Batch:** procesamiento de grandes volúmenes con Spark sobre YARN.  
- **Streaming:** simulado en fases posteriores mediante Kafka (a integrar).

### Pipeline general

```
movies.json
   │
   ▼
[movies_producer.py]
   ├─ Carga dataset JSON
   ├─ Verifica HDFS y YARN
   └─ Escribe datos crudos en HDFS (/user/movies/raw/)
   │
   ▼
[movies_processor.py]
   ├─ Limpieza y validación
   ├─ Creación de columnas derivadas
   └─ Guarda datos procesados (/user/movies/processed/)
   │
   ▼
[movie_analysis.py]
   ├─ Carga desde HDFS (modo local)
   ├─ Estadísticas por género, rating y popularidad
   └─ Visualización de resultados en consola o dashboard
```

---

## 🧩 Componentes Principales

### 1️⃣ **Producer — `movies_producer.py`**
- Carga `movies.json` con `SparkSession` en modo YARN.  
- Verifica servicios HDFS y YARN antes de ejecutar.  
- Escribe datos en HDFS tanto en formato **Parquet** como **JSON**.  
- Genera salida:  
  ```
  hdfs://localhost:9000/user/movies/raw/movies_dataset
  ```

### 2️⃣ **Processor — `movies_processor.py`**
- Lee los datos crudos desde HDFS.  
- Aplica transformaciones:  
  - Filtra nulos y valores inválidos.  
  - Genera columna `genres` como arreglo.  
  - Clasifica películas según **popularidad** (`Alta`, `Media`, `Baja`).  
  - Clasifica puntuaciones en categorías (`Excelente`, `Muy Bueno`, etc.).  
- Escribe resultados en:
  ```
  hdfs://localhost:9000/user/movies/processed/cleaned_movies
  ```

### 3️⃣ **Analysis — `movie_analysis.py`**
- Carga los datos procesados desde HDFS o ruta local.  
- Genera estadísticas:
  - **Top 5 películas mejor puntuadas.**
  - **Distribución de géneros.**
  - **Promedios de popularidad y rating.**
- Visualiza en consola y puede exportarse a dashboards (Plotly o Streamlit).

---

## 🧱 Infraestructura

Los servicios fueron gestionados mediante scripts:

- `iniciar_servicios.sh` → Levanta **HDFS**, **YARN**, y **Spark**.  
- `detener_servicios.sh` → Detiene los servicios de Hadoop.  
- `configurar_spark.sh` → Configura variables y paths del entorno Spark.  
- `ejecutar_proyecto.sh` → Orquesta el pipeline completo (Producer → Processor → Analysis).

---

## 🚀 Avances Realizados

✅ **Infraestructura operativa**:  
Configuración funcional de HDFS, YARN y Spark con validaciones de conexión.  

✅ **Carga inicial de dataset**:  
Subset cargado en HDFS mediante `movies_producer.py`.  

✅ **Procesamiento distribuido**:  
`movies_processor.py` ejecutado correctamente sobre YARN.  

✅ **Resultados procesados**:  
Datos transformados y guardados en `/user/movies/processed/cleaned_movies`.  

✅ **Primer análisis exploratorio**:  
Ejecución de `movie_analysis.py` para obtener estadísticas descriptivas y distribuciones.

---

## 📈 Próximos Pasos

- Integrar **Kafka** para recibir nuevos eventos de películas en tiempo real.  
- Incorporar un **dashboard interactivo** (Streamlit o Dash).  
- Extender el dataset con metadatos adicionales (año, país, duración, etc.).  
- Implementar consultas SQL distribuidas con **Spark SQL o Hive**.  

---

## 🧩 Conclusión

El semi-proyecto demuestra la integración de tecnologías del ecosistema Hadoop:
- **Ingesta y almacenamiento distribuido (HDFS)**  
- **Procesamiento paralelo (Spark sobre YARN)**  
- **Análisis y visualización local**

Esta arquitectura es una base sólida para escalar hacia un pipeline de análisis **real-time** y **batch**, aplicable a entornos empresariales o académicos.

---