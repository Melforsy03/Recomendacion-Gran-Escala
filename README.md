# 🎬 Sistema de Recomendación de Películas a Gran Escala

<<<<<<< HEAD
<<<<<<< HEAD
## 📋 Descripción

Sistema inteligente de recomendación de películas diseñado para procesar y analizar millones de valoraciones de usuarios en tiempo real. El proyecto utiliza el reconocido dataset **MovieLens 20M** para ofrecer recomendaciones personalizadas basadas en los gustos y preferencias de los usuarios.

## 🎯 ¿Qué hace este sistema?
=======
[![Estado](https://img.shields.io/badge/Fase-3%20%7C%20ETL%20Completado-success)](docs/FASE3_RESUMEN.md)
[![Datos](https://img.shields.io/badge/Datos-32.2M%20registros-blue)](docs/FASE2_RESUMEN.md)
[![Parquet](https://img.shields.io/badge/Parquet-293%20MB-orange)](docs/FASE3_RESUMEN.md)
=======
## 📋 Descripción
>>>>>>> 8da1009 (Actualiza el README.md)

Sistema inteligente de recomendación de películas diseñado para procesar y analizar millones de valoraciones de usuarios en tiempo real. El proyecto utiliza el reconocido dataset **MovieLens 20M** para ofrecer recomendaciones personalizadas basadas en los gustos y preferencias de los usuarios.

## 🎯 ¿Qué hace este sistema?

- **Recomienda películas** personalizadas a cada usuario basándose en su historial de valoraciones y las preferencias de usuarios similares
- **Procesa datos en tiempo real** para actualizar las recomendaciones instantáneamente cuando un usuario califica una nueva película
- **Analiza tendencias** para identificar las películas más populares y las preferencias por género
- **Visualiza métricas** a través de un dashboard interactivo que muestra estadísticas en vivo

## 📊 Dataset

<<<<<<< HEAD
| Fase | Estado | Descripción | Documentación |
|------|--------|-------------|---------------|
| **Fase 1** | ✅ COMPLETADA | Verificación infraestructura Docker | [FASE1_RESUMEN.md](docs/FASE1_RESUMEN.md) |
| **Fase 2** | ✅ COMPLETADA | Carga de 885 MB CSV a HDFS | [FASE2_RESUMEN.md](docs/FASE2_RESUMEN.md) |
| **Fase 3** | ✅ COMPLETADA | ETL a Parquet tipado (293 MB) | [FASE3_RESUMEN.md](docs/FASE3_RESUMEN.md) |
| **Fase 4** | 🔄 PENDIENTE | Features de contenido (géneros, tags) | - |
| **Fase 5** | 🔄 PENDIENTE | Entrenamiento modelo ALS | - |
| **Fase 6** | 🔄 PENDIENTE | Evaluación y métricas | - |
| **Fase 7** | 🔄 PENDIENTE | Producer Kafka (ratings sintéticos) | - |
| **Fase 8** | 🔄 PENDIENTE | Streaming processor con métricas | - |
| **Fase 9** | 🔄 PENDIENTE | Persistencia de streams en HDFS | - |
| **Fase 10** | 🔄 PENDIENTE | Analytics batch sobre streams | - |
>>>>>>> 472dd09 (feat: Implement FASE 3 ETL process for MovieLens data)

- **Recomienda películas** personalizadas a cada usuario basándose en su historial de valoraciones y las preferencias de usuarios similares
- **Procesa datos en tiempo real** para actualizar las recomendaciones instantáneamente cuando un usuario califica una nueva película
- **Analiza tendencias** para identificar las películas más populares y las preferencias por género
- **Visualiza métricas** a través de un dashboard interactivo que muestra estadísticas en vivo

## 📊 Dataset

El sistema trabaja con aproximadamente **32 millones de registros** que incluyen:

- 🎥 ~27,000 películas con información de géneros
- ⭐ ~20 millones de valoraciones de usuarios
- 🏷️ ~465,000 etiquetas descriptivas
- 🧬 ~11.7 millones de puntuaciones de similitud entre películas

## ✨ Características Principales

| Característica | Descripción |
|----------------|-------------|
| **Recomendaciones Personalizadas** | Sugiere películas basándose en tus gustos y los de usuarios similares |
| **Procesamiento en Tiempo Real** | Las recomendaciones se actualizan instantáneamente |
| **Dashboard Interactivo** | Visualiza métricas y estadísticas del sistema en vivo |
| **API REST** | Accede a las recomendaciones desde cualquier aplicación |
| **Escalabilidad** | Diseñado para manejar millones de usuarios y valoraciones |

## 🌐 Interfaces Disponibles

Una vez iniciado el sistema, puedes acceder a:

| Interfaz | URL | Descripción |
|----------|-----|-------------|
| Dashboard | http://localhost:8501 | Panel de control con métricas en tiempo real |
| API | http://localhost:8000 | Endpoints para obtener recomendaciones |
| Monitoreo Spark | http://localhost:8080 | Estado del procesamiento |
| Monitoreo Almacenamiento | http://localhost:9870 | Estado del sistema de archivos |

## 🚀 Inicio Rápido

```bash
# 1. Iniciar todos los servicios
./scripts/start-system.sh

# 2. Verificar que todo funciona
./scripts/check_system_status.sh

# 3. Abrir el dashboard en tu navegador
# http://localhost:8501
```

## 📁 Estructura del Proyecto

```
📦 Recomendacion-Gran-Escala
├── 📂 Dataset/          → Datos de MovieLens (películas, valoraciones, etiquetas)
├── 📂 movies/           → Código principal del sistema
│   ├── 📂 api/          → Servicio de recomendaciones (REST API)
│   ├── 📂 dashboard/    → Panel de visualización de métricas
│   └── 📂 src/          → Lógica de procesamiento y modelos
├── 📂 scripts/          → Scripts de gestión y despliegue
├── 📂 docs/             → Documentación detallada
└── 📂 tests/            → Pruebas del sistema
```

## 📚 Documentación

=======
El sistema trabaja con aproximadamente **32 millones de registros** que incluyen:

- 🎥 ~27,000 películas con información de géneros
- ⭐ ~20 millones de valoraciones de usuarios
- 🏷️ ~465,000 etiquetas descriptivas
- 🧬 ~11.7 millones de puntuaciones de similitud entre películas

## ✨ Características Principales

| Característica | Descripción |
|----------------|-------------|
| **Recomendaciones Personalizadas** | Sugiere películas basándose en tus gustos y los de usuarios similares |
| **Procesamiento en Tiempo Real** | Las recomendaciones se actualizan instantáneamente |
| **Dashboard Interactivo** | Visualiza métricas y estadísticas del sistema en vivo |
| **API REST** | Accede a las recomendaciones desde cualquier aplicación |
| **Escalabilidad** | Diseñado para manejar millones de usuarios y valoraciones |

## 🌐 Interfaces Disponibles

Una vez iniciado el sistema, puedes acceder a:

| Interfaz | URL | Descripción |
|----------|-----|-------------|
| Dashboard | http://localhost:8501 | Panel de control con métricas en tiempo real |
| API | http://localhost:8000 | Endpoints para obtener recomendaciones |
| Monitoreo Spark | http://localhost:8080 | Estado del procesamiento |
| Monitoreo Almacenamiento | http://localhost:9870 | Estado del sistema de archivos |

## 📁 Estructura del Proyecto

```
📦 Recomendacion-Gran-Escala
├── 📂 Dataset/          → Datos de MovieLens (películas, valoraciones, etiquetas)
├── 📂 movies/           → Código principal del sistema
│   ├── 📂 api/          → Servicio de recomendaciones (REST API)
│   ├── 📂 dashboard/    → Panel de visualización de métricas
│   └── 📂 src/          → Lógica de procesamiento y modelos
├── 📂 scripts/          → Scripts de gestión y despliegue
├── 📂 docs/             → Documentación detallada
└── 📂 tests/            → Pruebas del sistema
```

## 📚 Documentación

>>>>>>> 8da1009 (Actualiza el README.md)
Para más información, consulta:

- **[Documentación Técnica](docs/DOCUMENTACION.md)** - Detalles de arquitectura y componentes
- **[Guía de Primer Despliegue](docs/GUIA_DESPLIEGUE_INICIAL_UNICO.md)** - Configuración inicial paso a paso
- **[Guía de Uso Regular](docs/GUIA_DESPLIEGUE_REGULAR.md)** - Operación diaria del sistema

## 🤝 Contribuciones

Este es un proyecto educativo para sistemas de recomendación a gran escala. ¡Las contribuciones son bienvenidas!

## 📄 Licencia

Este proyecto es de código abierto bajo la licencia MIT.
