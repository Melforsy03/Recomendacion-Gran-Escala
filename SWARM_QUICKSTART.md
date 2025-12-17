# 🚀 DESPLIEGUE EN DOCKER SWARM MULTIMANAGER

**Documento:** Stack para desplegar servicio de recomendación entre dos computadoras manager  
**Versión:** 1.0  
**Última actualización:** 16 de diciembre de 2025

---

## 📌 CONTENIDO DE LA SOLUCIÓN

### Archivos principales

| Archivo | Descripción |
|---------|------------|
| **`docker-compose.swarm.yml`** | Stack optimizado para Swarm con 2 managers |
| **`docs/GUIA_DESPLIEGUE_SWARM.md`** | Guía completa y detallada (50+ páginas) |
| **`scripts/swarm-manager.sh`** | Herramienta CLI para operaciones comunes |
| **`scripts/check-swarm-requirements.sh`** | Verificador de requisitos previos |

---

## ⚡ INICIO RÁPIDO (5 minutos)

### 1️⃣ Verificar requisitos

```bash
cd /home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala
./scripts/check-swarm-requirements.sh
```

### 2️⃣ Inicializar Swarm en Manager-1

```bash
./scripts/swarm-manager.sh init --advertise-addr 192.168.1.100
```

### 3️⃣ Obtener token en Manager-1

```bash
./scripts/swarm-manager.sh join-token manager
```

### 4️⃣ Unir Manager-2 (ejecutar en Manager-2)

```bash
docker swarm join --token SWMTKN-1-xxx... 192.168.1.100:2377
```

### 5️⃣ Desplegar stack (desde Manager-1)

```bash
./scripts/swarm-manager.sh deploy
```

### 6️⃣ Verificar estado

```bash
./scripts/swarm-manager.sh status
```

---

## 🏗️ ARQUITECTURA

### Distribución de servicios entre managers

```
┌─────────────────────────┐       ┌─────────────────────────┐
│      MANAGER-1          │       │      MANAGER-2          │
├─────────────────────────┤       ├─────────────────────────┤
│ • Namenode (HDFS)       │◄─────►│ • Datanode (HDFS)       │
│ • ResourceManager (YARN)│       │ • NodeManager (YARN)    │
│ • Spark Master          │◄─────►│ • Spark Worker          │
│ • Zookeeper (Kafka)     │       │ • Kafka Broker          │
│ • API (replica 1)       │       │ • API (replica 2)       │
│ • Dashboard             │       │                         │
│ (4 puertos)             │       │ (4 puertos)             │
└─────────────────────────┘       └─────────────────────────┘
         │                                   │
         └───────────────────────────────────┘
            Red Overlay (VXLAN) Encriptada
           Puertos: 2377, 7946, 4789 UDP
```

### Servicios desplegados

| Servicio | Replicas | Puerto | Manager | Descripción |
|----------|----------|--------|---------|------------|
| **Namenode** | 1 | 9870, 9000 | Manager-1 | HDFS NameNode |
| **Datanode** | 1 | - | Manager-2 | HDFS DataNode |
| **ResourceManager** | 1 | 8088, 8032 | Manager-1 | YARN RM |
| **NodeManager** | 1 | 8042 | Manager-2 | YARN NM |
| **Spark Master** | 1 | 7077, 8080, 4040 | Manager-1 | Spark Master |
| **Spark Worker** | 1 | 8081 | Manager-2 | Spark Worker |
| **Zookeeper** | 1 | 2181 | Manager-1 | Kafka Zookeeper |
| **Kafka** | 1 | 9092, 9093 | Manager-2 | Kafka Broker |
| **API** | 2 | 8000 | Ambos | FastAPI Recomendaciones |
| **Dashboard** | 1 | 8501 | Ambos | Streamlit Dashboard |

---

## 📊 CARACTERÍSTICAS PRINCIPALES

### ✅ Alta disponibilidad
- **2 managers** para quórum de Swarm
- **API con 2 replicas** (distribuidas entre managers)
- **Políticas de reinicio automático** con `on-failure`
- **Health checks** en todos los servicios

### ✅ Persistencia distribuida
- **Volúmenes NFS** compartidos entre managers
- **Datos siempre disponibles** aunque un manager falle
- **Soporte para backup/restore** automático

### ✅ Escalabilidad
```bash
# Escalar API a 4 replicas
./scripts/swarm-manager.sh scale api 4

# Actualizar imagen sin downtime
./scripts/swarm-manager.sh update api localhost:5000/recs-api:v2
```

### ✅ Monitoreo
```bash
# Ver estado en tiempo real
docker stats

# Logs en tiempo real
./scripts/swarm-manager.sh logs api 100

# Health check
./scripts/swarm-manager.sh health
```

---

## 🔧 CONFIGURACIÓN REQUERIDA

### Hardware mínimo recomendado (CADA MANAGER)

| Recurso | Requerimiento | Recomendado |
|---------|--------------|------------|
| **CPU** | 2 cores | 4+ cores |
| **RAM** | 4 GB | 8+ GB |
| **Almacenamiento** | 50 GB | 100+ GB |
| **Conectividad** | 100 Mbps | 1 Gbps |

### Red requerida

| Puerto | Protocolo | Uso |
|--------|-----------|-----|
| 2377 | TCP | Comunicación Swarm |
| 7946 | TCP/UDP | Gossip protocol |
| 4789 | UDP | VXLAN overlay |

### Software requerido

```bash
# Verificar versiones
docker version           # ✓ 20.10+
docker compose version   # ✓ 2.10+
```

---

## 📚 GUÍAS Y RECURSOS

### 🟢 Guía completa (detallada)
Ver: **`docs/GUIA_DESPLIEGUE_SWARM.md`**

Incluye:
- Configuración paso a paso
- Troubleshooting completo
- Recuperación ante fallos
- Consideraciones de seguridad
- Ejemplos prácticos

### 🟢 Scripts disponibles

```bash
# Gestor principal de stack
./scripts/swarm-manager.sh help

# Verificador de requisitos
./scripts/check-swarm-requirements.sh

# Otros scripts del proyecto
./scripts/start-system.sh      # Inicia servicios locales
./scripts/stop-system.sh       # Detiene servicios locales
./scripts/check-system-status.sh  # Estado general
```

---

## 🚀 OPERACIONES COMUNES

### Desplegar (primera vez)

```bash
./scripts/check-swarm-requirements.sh
./scripts/swarm-manager.sh init --advertise-addr 192.168.1.100
# En Manager-2: docker swarm join ...
./scripts/swarm-manager.sh deploy
```

### Actualizar imagen de API

```bash
# Compilar nueva versión
docker build -t localhost:5000/recs-api:v2 ./movies/api/
docker push localhost:5000/recs-api:v2

# Actualizar en Swarm (rolling update)
./scripts/swarm-manager.sh update api localhost:5000/recs-api:v2
```

### Escalar servicio

```bash
# API a 4 replicas
./scripts/swarm-manager.sh scale api 4

# Verificar
./scripts/swarm-manager.sh status
```

### Ver logs de servicio

```bash
# Últimas 50 líneas (seguimiento en tiempo real)
./scripts/swarm-manager.sh logs api 50

# Últimas 200 líneas
./scripts/swarm-manager.sh logs api 200
```

### Respaldo de datos

```bash
# Crear respaldo
./scripts/swarm-manager.sh backup ./backups

# Restaurar desde respaldo
./scripts/swarm-manager.sh restore ./backups
```

### Eliminar stack

```bash
# Elimina servicios pero mantiene volúmenes
./scripts/swarm-manager.sh remove
```

---

## 🔗 ACCESO A SERVICIOS

Una vez desplegado, acceder mediante:

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **API** | `http://manager-1:8000` | REST API de recomendaciones |
| **Dashboard** | `http://manager-1:8501` | Visualización Streamlit |
| **Spark Master UI** | `http://manager-1:8080` | Monitor de Spark |
| **Hadoop HDFS** | `http://manager-1:9870` | NameNode HDFS |
| **YARN** | `http://manager-1:8088` | ResourceManager YARN |

---

## 🛡️ SEGURIDAD

### Habilitado en la configuración

✅ **Encriptación de red overlay** (VXLAN)  
✅ **Health checks** en todos los servicios  
✅ **Límites de recursos** por servicio  
✅ **Restart policies** con reintentos  
✅ **Aislamientos de red** por overlay

### Recomendaciones adicionales

Para producción, considera:

```yaml
# 1. Secretos para credenciales
docker secret create kafka_user_pass -
docker secret create spark_password -

# 2. Registar privado con autenticación
docker login registry.tudominio.com

# 3. TLS/mTLS entre servicios
# Configurable en docker-compose.swarm.yml

# 4. Logs centralizados
# Cambiar log driver a Splunk/ELK/CloudWatch
```

---

## ❌ TROUBLESHOOTING RÁPIDO

### "Container en estado Pending"
```bash
docker service inspect SERVICE_NAME | jq '.Spec.TaskTemplate.Placement'
# Verificar restricciones y disponibilidad de nodos
```

### "Red overlay no conecta"
```bash
# Verificar puertos abiertos
sudo ufw allow 2377/tcp
sudo ufw allow 7946/tcp
sudo ufw allow 7946/udp
sudo ufw allow 4789/udp
```

### "NFS no monta"
```bash
sudo mount -t nfs 192.168.1.101:/exports/namenode_data /tmp/test
# Si falla, revisar guía completa: docs/GUIA_DESPLIEGUE_SWARM.md
```

### "Imágenes personalizadas no se encuentran"
```bash
# Compilar y pushear
docker build -t localhost:5000/recs-api:latest ./movies/api/
docker push localhost:5000/recs-api:latest
```

---

## 📞 SOPORTE

### Documentación
- 📖 Guía completa: `docs/GUIA_DESPLIEGUE_SWARM.md`
- 📋 README original: `README.md`
- 🔗 Docs de despliegue local: `docs/GUIA_DESPLIEGUE_INICIAL_UNICO.md`

### Comandos de diagnóstico

```bash
# Estado general del Swarm
docker info

# Nodos del cluster
docker node ls

# Servicios activos
docker service ls

# Tareas/contenedores
docker stack ps recomendacion

# Eventos en tiempo real
docker events --filter "type=service"

# Logs de servicio específico
docker service logs recomendacion_api -f

# Recursos utilizados
docker stats
```

---

## 📋 COMPARATIVA: Docker Compose vs Swarm

| Aspecto | Docker Compose | Docker Swarm |
|--------|---|---|
| **Nodos** | 1 | 1+ (cluster) |
| **Alta disponibilidad** | ❌ No | ✅ Sí |
| **Replicación** | ❌ No | ✅ Sí (escalado) |
| **Reinicio automático** | ⚠️ Limitado | ✅ Robusto |
| **Volúmenes distribuidos** | ⚠️ Local | ✅ NFS/Distribuido |
| **Actualización sin downtime** | ❌ No | ✅ Rolling update |
| **Configuración** | 📄 Simple | 📚 Más compleja |
| **Producción** | ⚠️ Limitado | ✅ Recomendado |

---

## ✅ CHECKLIST DE DESPLIEGUE

```
PREPARACIÓN
  ☐ Dos máquinas con Docker 20.10+
  ☐ Conectividad entre máquinas verificada
  ☐ NFS configurado y compartido
  ☐ Imágenes compiladas (API y Dashboard)

DESPLIEGUE
  ☐ Swarm inicializado en Manager-1
  ☐ Manager-2 unido al Swarm
  ☐ docker-compose.swarm.yml editado con IPs correctas
  ☐ Stack desplegado: ./scripts/swarm-manager.sh deploy

VALIDACIÓN
  ☐ Todos los servicios en "Running"
  ☐ Acceso a UIs web verificado
  ☐ Logs sin errores críticos
  ☐ Health check pasando: ./scripts/swarm-manager.sh health

OPERACIÓN
  ☐ Respaldo de datos configurado
  ☐ Monitoreo en tiempo real funcional
  ☐ Escalado de API probado
  ☐ Rol de Manager verificado en ambos nodos
```

---

**Última actualización:** 16 de diciembre de 2025  
**Versión del stack:** 1.0  
**Estado:** ✅ Listo para producción
