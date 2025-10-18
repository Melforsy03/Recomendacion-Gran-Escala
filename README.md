

## 📋 Descripción

Sistema de recomendación que simula el procesamiento de **millones de interacciones de usuarios** usando una arquitectura de Big Data en tiempo real. Incluye generación de datos, streaming con Kafka, procesamiento de métricas y visualización interactiva.

### 🏗️ Arquitectura

JSON Local (1768 películas)
       ↓
PRODUCER (Spark + YARN)
       ↓
HDFS [/raw/] ←─── Datos crudos
       ↓  
PROCESSOR (Spark + YARN) ←─── Transformaciones
       ↓
HDFS [/processed/] ←─── Datos enriquecidos
       ↓
ANALYSIS (Opcional) ←─── Reportes/Estadísticas