# 🚀 GUÍA DE DESPLIEGUE EN DOCKER SWARM MULTIMANAGER

**Última actualización:** 16 de diciembre de 2025  
**Entorno:** Docker Swarm con 2 managers  
**Servicios:** HDFS, YARN, Spark, Kafka, API REST, Dashboard

---

## 📋 TABLA DE CONTENIDOS

1. [Requisitos previos](#requisitos-previos)
2. [Configuración de Swarm](#configuración-de-swarm)
3. [Preparación del entorno](#preparación-del-entorno)
4. [Despliegue del stack](#despliegue-del-stack)
5. [Monitoreo y mantenimiento](#monitoreo-y-mantenimiento)
6. [Troubleshooting](#troubleshooting)
7. [Recuperación ante fallos](#recuperación-ante-fallos)

---

## 🔧 Requisitos previos

### Hardware
- **Manager-1**: Mínimo 8 GB RAM, 4 CPU cores
- **Manager-2**: Mínimo 8 GB RAM, 4 CPU cores
- **Conectividad**: Red privada entre managers (puertos 2377, 7946 TCP/UDP)
- **Almacenamiento**: Compartido (NFS, GlusterFS, o cloud storage)

### Software
- Docker CE 20.10+ en ambas máquinas
- Docker CLI configurado
- `docker-compose` CLI plugin v2.10+
- NFS server (para volúmenes persistentes)

### Verificación
```bash
# En ambas máquinas
docker version
docker compose version
docker info | grep Swarm

# Verificar conectividad entre máquinas
ping <ip-manager-2>
nc -zv <ip-manager-2> 2377  # Debe conectarse
```

---

## 🌐 Configuración de Swarm

### Paso 1: Inicializar Swarm en Manager-1

```bash
# En manager-1
docker swarm init --advertise-addr <IP-PRIVADA-MANAGER-1>

# Ejemplo:
docker swarm init --advertise-addr 192.168.1.100
```

**Output esperado:**
```
Swarm initialized: current node (abc123...) is now a manager.
To add a worker to this swarm, run the following command:
    docker swarm join --token SWMTKN-1-xxx...
```

### Paso 2: Obtener token de Manager en Manager-1

```bash
# En manager-1 - Obtener token para que manager-2 se una como manager
docker swarm join-token manager

# Output:
# docker swarm join --token SWMTKN-1-xxx-xxx <IP-MANAGER-1>:2377
```

**⚠️ Guardar el token en lugar seguro**

### Paso 3: Unir Manager-2 al Swarm

```bash
# En manager-2
docker swarm join --token SWMTKN-1-xxx-xxx 192.168.1.100:2377
```

**Output esperado:**
```
This node joined a swarm as a manager.
```

### Paso 4: Verificar cluster Swarm

```bash
# En manager-1
docker node ls

# Output esperado:
ID                            HOSTNAME     STATUS    AVAILABILITY   MANAGER STATUS   ENGINE VERSION
abc123...    manager-1      Ready      Active         Leader           20.10.12
def456...    manager-2      Ready      Active         Reachable        20.10.12
```

---

## 📦 Preparación del entorno

### Paso 1: Configurar NFS para volúmenes compartidos

#### En NFS Server (puede ser un tercero o manager-1)

```bash
# Instalar NFS
sudo apt-get install nfs-kernel-server

# Crear directorios de exportación
sudo mkdir -p /exports/{namenode_data,datanode_data,zookeeper_data,zookeeper_log,kafka_data}
sudo chown nobody:nogroup /exports/*
sudo chmod 777 /exports/*

# Editar /etc/exports
sudo nano /etc/exports

# Agregar (para acceso desde ambos managers):
/exports/namenode_data     192.168.1.0/24(rw,sync,no_root_squash,no_all_squash)
/exports/datanode_data     192.168.1.0/24(rw,sync,no_root_squash,no_all_squash)
/exports/zookeeper_data    192.168.1.0/24(rw,sync,no_root_squash,no_all_squash)
/exports/zookeeper_log     192.168.1.0/24(rw,sync,no_root_squash,no_all_squash)
/exports/kafka_data        192.168.1.0/24(rw,sync,no_root_squash,no_all_squash)

# Aplicar cambios
sudo exportfs -a
sudo systemctl restart nfs-kernel-server

# Verificar
showmount -e localhost
```

#### En Manager-1 y Manager-2: Instalar cliente NFS

```bash
# Instalar NFS client
sudo apt-get install nfs-common

# Crear puntos de montaje (solo para verificación local, Swarm lo monta automáticamente)
sudo mkdir -p /mnt/nfs/{namenode_data,datanode_data,zookeeper_data,kafka_data}

# Probar conexión
sudo mount -t nfs 192.168.1.101:/exports/namenode_data /mnt/nfs/namenode_data
sudo umount /mnt/nfs/namenode_data
```

### Paso 2: Configurar registro privado Docker (opcional pero recomendado)

```bash
# Opción A: Usar Docker Hub (no recomendado en producción)
docker login

# Opción B: Registrar privado en Manager-1
docker run -d \
  -p 5000:5000 \
  --name registry \
  --restart always \
  -v /mnt/registry:/var/lib/registry \
  registry:2

# En ambos managers: agregar /etc/docker/daemon.json
{
  "insecure-registries": ["localhost:5000"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}

# Reiniciar Docker
sudo systemctl restart docker
```

### Paso 3: Preparar imágenes Docker

```bash
# Compilar API
cd /home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala
docker build -t localhost:5000/recs-api:latest ./movies/api/
docker push localhost:5000/recs-api:latest

# Compilar Dashboard
docker build -t localhost:5000/recs-dashboard:latest ./movies/dashboard/
docker push localhost:5000/recs-dashboard:latest

# Verificar en registry
curl http://localhost:5000/v2/_catalog
```

### Paso 4: Ajustar docker-compose.swarm.yml

```yaml
# Editar las secciones importantes:

# 1. Cambiar IPs de NFS (línea ~30)
volumes:
  namenode_data:
    driver: local
    driver_opts:
      type: nfs
      o: "addr=192.168.1.101,vers=4,soft,timeo=180,bg,tcp,rw"  # Tu IP de NFS
      device: ":/exports/namenode_data"

# 2. Cambiar hostnames de nodos (línea ~160, ~250, etc.)
placement:
  constraints:
    - node.hostname == manager-1  # ✅ Verificar con 'docker node ls'
    - node.hostname == manager-2

# 3. Si usas registro privado (línea ~540, ~580)
image: localhost:5000/recs-api:latest
image: localhost:5000/recs-dashboard:latest
```

**Obtener hostnames exactos:**
```bash
docker node ls --format "{{.Hostname}}"
```

---

## 🚀 Despliegue del stack

### Paso 1: Validar configuración

```bash
cd /home/abraham/Escritorio/PGVD/Recomendacion-Gran-Escala

# Validar sintaxis del archivo
docker compose -f docker-compose.swarm.yml config

# Debe mostrar la configuración sin errores
```

### Paso 2: Desplegar stack

```bash
# Desplegar (solo desde un manager)
docker stack deploy -c docker-compose.swarm.yml recomendacion

# Output esperado:
# Creating network recomendacion_datapipeline
# Creating service recomendacion_namenode
# Creating service recomendacion_datanode
# Creating service recomendacion_resourcemanager
# ...
```

### Paso 3: Verificar despliegue

```bash
# Ver estado del stack
docker stack ps recomendacion

# Ver servicios
docker service ls

# Ver red overlay
docker network ls | grep recomendacion

# Inspeccionar red
docker network inspect recomendacion_datapipeline
```

**Estado esperado:**
```
ID             NAME                               MODE        REPLICAS   IMAGE
abc123...      recomendacion_namenode             replicated  1/1        bde2020/hadoop-namenode:...
def456...      recomendacion_datanode             replicated  1/1        bde2020/hadoop-datanode:...
ghi789...      recomendacion_api                  replicated  2/2        localhost:5000/recs-api:...
...
```

---

## 📊 Monitoreo y mantenimiento

### Verificar salud del cluster

```bash
# Dashboard del cluster
docker stats

# Logs de servicio específico
docker service logs recomendacion_namenode
docker service logs recomendacion_api -f  # Seguir en tiempo real

# Estado detallado del stack
docker stack ps recomendacion --no-trunc

# Inspeccionar servicio
docker service inspect recomendacion_api --pretty
```

### Acceder a UIs web

| Servicio | URL | Puerto |
|----------|-----|--------|
| **Spark Master** | `http://manager-1:8080` | 8080 |
| **Hadoop HDFS** | `http://manager-1:9870` | 9870 |
| **YARN ResourceManager** | `http://manager-1:8088` | 8088 |
| **API REST** | `http://manager-1:8000` | 8000 |
| **Dashboard** | `http://manager-1:8501` | 8501 |

### Escalado de servicios

```bash
# Aumentar replicas de API a 4
docker service scale recomendacion_api=4

# Verificar
docker service ls
docker service ps recomendacion_api
```

### Actualizar servicio

```bash
# Compilar nueva versión
docker build -t localhost:5000/recs-api:v2 ./movies/api/
docker push localhost:5000/recs-api:v2

# Actualizar servicio (rolling update automático)
docker service update --image localhost:5000/recs-api:v2 recomendacion_api

# Ver progreso
docker service ps recomendacion_api --no-trunc
```

---

## 🔍 Troubleshooting

### Problema: Servicio no inicia

```bash
# Ver logs del servicio
docker service logs recomendacion_namenode

# Ver tarea específica
docker task ps --no-trunc | grep namenode

# Inspeccionar container del nodo
docker ps -a | grep namenode

# Ver logs del container
docker logs <container-id>
```

### Problema: Red overlay no funciona

```bash
# Verificar red
docker network ls
docker network inspect recomendacion_datapipeline

# Desde cada nodo, verificar conectividad
docker exec -it <container> ping otro-servicio

# Verificar puertos abiertos
sudo ufw allow 2377/tcp
sudo ufw allow 7946/tcp
sudo ufw allow 7946/udp
sudo ufw allow 4789/udp
```

### Problema: Volúmenes NFS no montan

```bash
# Verificar NFS desde el nodo
sudo mount -t nfs 192.168.1.101:/exports/namenode_data /tmp/test
df -h /tmp/test
sudo umount /tmp/test

# Ver logs de Docker
journalctl -u docker -f

# Verificar permisos NFS
stat /exports/namenode_data
```

### Problema: Contenedor en estado "Pending"

```bash
# Ver por qué no se programa
docker service inspect recomendacion_api | jq '.DesiredState'

# Posibles causas:
# 1. Recursos insuficientes
docker node inspect manager-1 | jq '.Description.Resources'

# 2. Restricción de placement
docker service inspect recomendacion_api | jq '.Spec.TaskTemplate.Placement'

# 3. Imagen no disponible
docker images | grep recs-api
```

---

## 🔄 Recuperación ante fallos

### Escenario 1: Manager-1 se cae

```bash
# Desde Manager-2 (sigue siendo disponible)
docker node ls

# Status de Manager-1 será "Down"
# El stack sigue funcionando si todos los servicios están en replicas > 1

# Cuando Manager-1 vuelve
docker node ls  # Debería mostrarse como "Ready"
```

### Escenario 2: Fallo de servicio crítico

```bash
# Política de reinicio automática (ya configurada)
deploy:
  restart_policy:
    condition: on-failure
    delay: 10s
    max_attempts: 5

# Ver si se reinició
docker service logs recomendacion_namenode | tail -20
```

### Escenario 3: Recuperación de datos después de fallo

```bash
# Datos persistentes están en NFS (configuración actual)
# Verificar integridad
sudo fsck.nfs /mnt/nfs/namenode_data

# Si es necesario recuperar de backup
sudo rsync -av /backup/namenode_data/ /exports/namenode_data/

# Reiniciar servicio
docker service update --force recomendacion_namenode
```

### Escenario 4: Eliminar stack para recuperación completa

```bash
# ⚠️ ADVERTENCIA: Esto detiene pero NO elimina volúmenes
docker stack rm recomendacion

# Verificar que se eliminaron servicios
docker service ls  # Vacío

# Verificar que volúmenes persisten
docker volume ls | grep recomendacion

# Redeploy
docker stack deploy -c docker-compose.swarm.yml recomendacion
```

---

## 📋 Checklist de despliegue

- [ ] Swarm inicializado en ambos managers
- [ ] NFS configurado y compartido
- [ ] `docker-compose.swarm.yml` editado con IPs correctas
- [ ] Imágenes compiladas y en registro (si aplica)
- [ ] Red overlay creada correctamente
- [ ] `docker stack deploy` ejecutado sin errores
- [ ] Todos los servicios en estado "Running"
- [ ] Acceso a UIs web verificado
- [ ] Logs sin errores críticos
- [ ] Prueba de escalado: `docker service scale recomendacion_api=3`
- [ ] Prueba de fallo: `docker service pause recomendacion_api` → verificar reinicio automático

---

## 🔐 Consideraciones de seguridad

```yaml
# En producción, agregar:

# 1. Encriptación de red overlay
networks:
  datapipeline:
    driver: overlay
    driver_opts:
      com.docker.network.driver.overlay.vxlan_list: "4789"
      # Encriptación habilitada por defecto en overlay

# 2. Secretos para credenciales
secrets:
  kafka_password:
    external: true

services:
  kafka:
    secrets:
      - kafka_password
    environment:
      - KAFKA_PASSWORD_FILE=/run/secrets/kafka_password

# Crear secreto:
echo "tu_password_secura" | docker secret create kafka_password -

# 3. Límites de CPU/Memoria (ya incluido)
# 4. Restart policies (ya incluido)
# 5. Healthchecks (ya incluido)
```

---

## 📞 Soporte y debugging

### Logs centralizados (recomendado)

```bash
# Configurar Docker para enviar logs a ElasticSearch/Splunk/etc.
# Editar /etc/docker/daemon.json en ambos managers

{
  "log-driver": "splunk",
  "log-opts": {
    "splunk-token": "your-token",
    "splunk-url": "https://your-splunk:8088",
    "tag": "{{.Name}}"
  }
}

# Reiniciar Docker
sudo systemctl restart docker
```

### Debugging avanzado

```bash
# Entrar en container para debugging
docker exec -it $(docker ps | grep namenode | awk '{print $1}') /bin/bash

# Conectar desde otro container
docker exec -it <container> ping namenode

# Monitoreo de recursos
docker stats recomendacion_api

# Ver eventos del cluster
docker events --filter "service=recomendacion_api"
```

---

**Última revisión:** 16 de diciembre de 2025  
**Estado:** ✅ Listo para producción
