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

[Producer] → [Kafka] → [Consumer] → [Dashboard]


## 🚀 Instalación Rápida

### Prerrequisitos
- **Ubuntu 20.04/22.04**
- **Java 11**
- **Python 3.9+**
- **8GB RAM** recomendado

### Paso 1: Clonar y Configurar
```bash
git clone https://github.com/Melforsy03/Recomendacion-Gran-Escala.git
cd Recomendacion-Gran-Escala

Paso 2: Instalar Dependencias
bash

# Instalar Java y herramientas
sudo apt update && sudo apt install openjdk-11-jdk python3 python3-pip python3-venv -y

# Configurar entorno virtual
python3 -m venv myenv
source myenv/bin/activate
pip install kafka-python dash plotly pandas redis

Paso 3: Configurar Hadoop & Kafka
bash

# Descargar e instalar Hadoop
wget https://archive.apache.org/dist/hadoop/common/hadoop-3.3.1/hadoop-3.3.1.tar.gz
tar -xzf hadoop-3.3.1.tar.gz

# Descargar e instalar Kafka
wget https://archive.apache.org/dist/kafka/2.8.1/kafka_2.13-2.8.1.tgz
tar -xzf kafka_2.13-2.8.1.tgz

# Configurar variables de entorno
echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64' >> ~/.bashrc
echo 'export PATH=$PATH:~/Recomendacion-Gran-Escala/hadoop-3.3.1/bin' >> ~/.bashrc
source ~/.bashrc

Paso 4: Configurar SSH
bash

ssh-keygen -t rsa -P '' -f ~/.ssh/id_rsa
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
sudo systemctl start ssh

Paso 5: Inicializar Hadoop
bash

cd hadoop-3.3.1

# Formatear HDFS (SOLO UNA VEZ)
hdfs namenode -format

# Iniciar servicios Hadoop
start-dfs.sh
start-yarn.sh

# Verificar servicios
jps

🎯 Uso del Sistema
Inicio Automático (Recomendado)
bash

cd code
./start_local_system.sh

Acceso al Dashboard

Una vez iniciado, abre tu navegador en:
text

http://localhost:8050

Monitoreo en Tiempo Real
bash

# Ver métricas (en terminal separada)
tail -f consumer.log

# Ver datos generados
tail -f producer.log

Detener el Sistema
bash

./stop_local_system.sh

📊 Dashboard

El sistema incluye un dashboard interactivo con:

    👥 Usuarios Activos - En tiempo real

    📊 Interacciones por Tipo - Clicks, views, ratings, purchases

    🎬 Películas Más Populares - Top 5 en tiempo real

    ⭐ Ratings Promedio - Evaluaciones de usuarios

    📈 Métricas Instantáneas - 4 widgets con datos actualizados