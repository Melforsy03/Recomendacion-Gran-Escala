# 🎬 Sistema de Recomendación a Gran Escala

<div align="center">

![Big Data](https://img.shields.io/badge/Big-Data-orange)
![Kafka](https://img.shields.io/badge/Apache-Kafka-blue)
![Python](https://img.shields.io/badge/Python-3.9-green)
![Real-time](https://img.shields.io/badge/Real--Time-Processing-red)

**Sistema completo de Big Data que procesa millones de interacciones en tiempo real**

[Instalación](#-instalación-rápida) • [Uso](#-uso-del-sistema) • [Dashboard](#-dashboard) • [Estructura](#-estructura-del-proyecto)

</div>

## 📋 Descripción

Sistema de recomendación que simula el procesamiento de **millones de interacciones de usuarios** usando una arquitectura de Big Data en tiempo real. Incluye generación de datos, streaming con Kafka, procesamiento de métricas y visualización interactiva.

### 🏗️ Arquitectura

┌─────────┐    ┌────────┐    ┌─────────────┐    ┌───────┐    ┌──────────┐
│Producer │───▶│ Kafka  │───▶│ Spark & Redis│───▶│ HDFS  │───▶│ Dashboard │
└─────────┘    └────────┘    └─────────────┘    └───────┘    └──────────┘
                                     │               │
                                     ▼               ▼
                               ┌──────────┐    ┌─────────────┐
                               │ YARN &   │    │ Batch &     │
                               │ MapReduce│    │ Spark Jobs  │
                               └──────────┘    └─────────────┘

