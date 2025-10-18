

## 📋 Descripción

Sistema de recomendación que simula el procesamiento de **millones de interacciones de usuarios** usando una arquitectura de Big Data en tiempo real. Incluye generación de datos, streaming con Kafka, procesamiento de métricas y visualización interactiva.

### 🏗️ Arquitectura
JSON Local → Spark Producer → HDFS (raw) → Spark Processor → HDFS (processed) → Analysis