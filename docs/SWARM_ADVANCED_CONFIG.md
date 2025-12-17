# 🔧 CONFIGURACIONES AVANZADAS DE DOCKER SWARM

**Documento:** Ejemplos y configuraciones avanzadas para diferentes escenarios  
**Fecha:** 16 de diciembre de 2025

---

## 📋 TABLA DE CONTENIDOS

1. [Múltiples nodos (3+ managers)](#múltiples-nodos-3-managers)
2. [Alta disponibilidad Kafka](#alta-disponibilidad-kafka)
3. [Almacenamiento distribuido con GlusterFS](#almacenamiento-distribuido-con-glusterfs)
4. [Monitoreo con Prometheus + Grafana](#monitoreo-con-prometheus--grafana)
5. [Backup automático](#backup-automático)
6. [Load balancing avanzado](#load-balancing-avanzado)
7. [Configuración de producción](#configuración-de-producción)
8. [Disaster recovery](#disaster-recovery)

---

## 🔄 Múltiples nodos (3+ managers)

Para mayor disponibilidad, usar 3 o 5 managers (quórum de Raft).

### Arquitectura recomendada

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│  MANAGER-1   │───────│  MANAGER-2   │───────│  MANAGER-3   │
│ (Leader)     │       │ (Reachable)  │       │ (Reachable)  │
└──────────────┘       └──────────────┘       └──────────────┘
       ↓                     ↓                      ↓
   NAMENODE            DATANODE-2            DATANODE-3
   ZOOKEEPER           KAFKA-2               KAFKA-3
   SPARK-MASTER        SPARK-WORKER-2        SPARK-WORKER-3
```

### Pasos de despliegue (3 managers)

```bash
# Manager-1: Inicializar
docker swarm init --advertise-addr 192.168.1.100

# Obtener token
docker swarm join-token manager

# Manager-2 y Manager-3: Unirse
docker swarm join --token SWMTKN-1-xxx... 192.168.1.100:2377

# Verificar
docker node ls
# Debe mostrar 3 nodos como "Ready"
```

### docker-compose.swarm.yml modificado para 3 managers

```yaml
services:
  # Distribuir servicios de estado entre los 3 managers
  namenode:
    deploy:
      placement:
        constraints:
          - node.hostname == manager-1

  datanode-2:
    image: bde2020/hadoop-datanode:2.0.0-hadoop3.2.1-java8
    hostname: datanode-2
    deploy:
      placement:
        constraints:
          - node.hostname == manager-2

  datanode-3:
    image: bde2020/hadoop-datanode:2.0.0-hadoop3.2.1-java8
    hostname: datanode-3
    deploy:
      placement:
        constraints:
          - node.hostname == manager-3

  api:
    deploy:
      replicas: 3  # Una por cada manager
      placement:
        preferences:
          - spread: node.id
```

---

## 🔗 Alta disponibilidad Kafka

Cluster Kafka con 3 brokers replicados.

### docker-compose.swarm.yml (Kafka HA)

```yaml
services:
  zookeeper-1:
    image: confluentinc/cp-zookeeper:6.2.0
    hostname: zookeeper-1
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
      ZOOKEEPER_SYNC_LIMIT: 5
      ZOOKEEPER_INIT_LIMIT: 10
      ZOOKEEPER_SERVER_1: zookeeper-1:2888:3888
      ZOOKEEPER_SERVER_2: zookeeper-2:2888:3888
      ZOOKEEPER_SERVER_3: zookeeper-3:2888:3888
    networks:
      - datapipeline
    deploy:
      placement:
        constraints:
          - node.hostname == manager-1

  zookeeper-2:
    image: confluentinc/cp-zookeeper:6.2.0
    hostname: zookeeper-2
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
      ZOOKEEPER_SYNC_LIMIT: 5
      ZOOKEEPER_INIT_LIMIT: 10
      ZOOKEEPER_SERVER_1: zookeeper-1:2888:3888
      ZOOKEEPER_SERVER_2: zookeeper-2:2888:3888
      ZOOKEEPER_SERVER_3: zookeeper-3:2888:3888
    networks:
      - datapipeline
    deploy:
      placement:
        constraints:
          - node.hostname == manager-2

  zookeeper-3:
    image: confluentinc/cp-zookeeper:6.2.0
    hostname: zookeeper-3
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
      ZOOKEEPER_SYNC_LIMIT: 5
      ZOOKEEPER_INIT_LIMIT: 10
      ZOOKEEPER_SERVER_1: zookeeper-1:2888:3888
      ZOOKEEPER_SERVER_2: zookeeper-2:2888:3888
      ZOOKEEPER_SERVER_3: zookeeper-3:2888:3888
    networks:
      - datapipeline
    deploy:
      placement:
        constraints:
          - node.hostname == manager-3

  kafka-1:
    image: confluentinc/cp-kafka:6.2.0
    hostname: kafka-1
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: 'zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181'
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka-1:9092
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
      KAFKA_DEFAULT_REPLICATION_FACTOR: 3
    deploy:
      placement:
        constraints:
          - node.hostname == manager-1

  kafka-2:
    image: confluentinc/cp-kafka:6.2.0
    hostname: kafka-2
    environment:
      KAFKA_BROKER_ID: 2
      KAFKA_ZOOKEEPER_CONNECT: 'zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181'
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka-2:9092
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
      KAFKA_DEFAULT_REPLICATION_FACTOR: 3
    deploy:
      placement:
        constraints:
          - node.hostname == manager-2

  kafka-3:
    image: confluentinc/cp-kafka:6.2.0
    hostname: kafka-3
    environment:
      KAFKA_BROKER_ID: 3
      KAFKA_ZOOKEEPER_CONNECT: 'zookeeper-1:2181,zookeeper-2:2181,zookeeper-3:2181'
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka-3:9092
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
      KAFKA_DEFAULT_REPLICATION_FACTOR: 3
    deploy:
      placement:
        constraints:
          - node.hostname == manager-3
```

### Verificar cluster Kafka

```bash
# Conectarse a cualquier broker
docker exec -it $(docker ps | grep kafka-1 | awk '{print $1}') bash

# Ver topics
kafka-topics.sh --bootstrap-server kafka-1:9092 --list

# Ver brokers
zookeeper-shell.sh zookeeper-1:2181 ls /brokers/ids
# Output: [1, 2, 3]

# Ver sincronización
kafka-topics.sh --bootstrap-server kafka-1:9092 --describe --topic ratings
```

---

## 💾 Almacenamiento distribuido con GlusterFS

Para evitar depender de un único servidor NFS.

### Instalación GlusterFS (en cada nodo)

```bash
# Instalar GlusterFS
sudo apt-get install glusterfs-server glusterfs-client

# Habilitar servicio
sudo systemctl enable glusterd
sudo systemctl start glusterd

# Verificar
sudo gluster --version
```

### Configuración del cluster GlusterFS

```bash
# En manager-1
sudo gluster peer probe 192.168.1.101  # manager-2
sudo gluster peer probe 192.168.1.102  # manager-3

# Verificar peers
sudo gluster peer status

# Crear volumen (3 replicas)
sudo gluster volume create storage-vol replica 3 \
  manager-1:/exports/storage \
  manager-2:/exports/storage \
  manager-3:/exports/storage

# Iniciar volumen
sudo gluster volume start storage-vol

# Verificar
sudo gluster volume info storage-vol
```

### Montar en Docker Swarm

```yaml
volumes:
  namenode_data:
    driver: local
    driver_opts:
      type: glusterfs
      o: "addr=manager-1,backup-volfile-servers=manager-2:manager-3,volume-id=storage-vol"
      device: ":storage-vol/namenode_data"
```

---

## 📊 Monitoreo con Prometheus + Grafana

Añadir monitoreo completo del cluster.

### docker-compose.swarm.yml (Monitoreo)

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    hostname: prometheus
    volumes:
      - prometheus_data:/prometheus
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    ports:
      - target: 9090
        published: 9090
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - datapipeline
    deploy:
      placement:
        constraints:
          - node.hostname == manager-1

  grafana:
    image: grafana/grafana:latest
    hostname: grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - target: 3000
        published: 3000
    networks:
      - datapipeline
    deploy:
      placement:
        constraints:
          - node.hostname == manager-1

  node-exporter:
    image: prom/node-exporter:latest
    command: --path.procfs=/host/proc --path.sysfs=/host/sys
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
    networks:
      - datapipeline
    deploy:
      mode: global  # En cada nodo

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
    networks:
      - datapipeline
    deploy:
      mode: global  # En cada nodo

volumes:
  prometheus_data:
  grafana_data:
```

### prometheus.yml

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'docker-swarm'
    static_configs:
      - targets: ['cadvisor:8080']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'spark'
    static_configs:
      - targets: ['spark-master:8080']

  - job_name: 'hadoop'
    static_configs:
      - targets: ['namenode:9870']
```

### Acceso a Grafana

```
URL: http://manager-1:3000
Usuario: admin
Contraseña: admin
```

---

## 🔄 Backup automático

Script de backup periódico con rotación.

### backup-volumes.sh

```bash
#!/bin/bash

BACKUP_DIR="/mnt/backups"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_PATH="$BACKUP_DIR/backup-$TIMESTAMP"

# Crear directorio
mkdir -p "$BACKUP_PATH"

# Listar volúmenes
docker volume ls -q | while read vol; do
    echo "Respaldando volumen: $vol"
    docker run --rm \
        -v "$vol:/data" \
        -v "$BACKUP_PATH:/backup" \
        alpine tar czf "/backup/$vol.tar.gz" -C /data .
done

# Limpiar backups antiguos
find "$BACKUP_DIR" -type d -name "backup-*" -mtime +$RETENTION_DAYS -exec rm -rf {} \;

echo "✓ Backup completado: $BACKUP_PATH"
```

### Ejecutar automáticamente con cron

```bash
# Crontab
0 2 * * * /path/to/backup-volumes.sh >> /var/log/swarm-backup.log 2>&1
```

---

## ⚖️ Load balancing avanzado

Configurar ingress load balancing con Traefik.

### docker-compose.swarm.yml (Traefik)

```yaml
services:
  traefik:
    image: traefik:v2.9
    command:
      - "--api.insecure=true"
      - "--providers.docker.swarmmode=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    ports:
      - target: 80
        published: 80
        mode: ingress
      - target: 8080
        published: 8080
        mode: ingress
    networks:
      - datapipeline
    deploy:
      placement:
        constraints:
          - node.role == manager

  api:
    image: localhost:5000/recs-api:latest
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.api.rule=Path(`/`)"
      - "traefik.http.services.api.loadbalancer.server.port=8000"
    deploy:
      replicas: 3
```

### Acceder a través de Traefik

```
API: http://manager-1  (enrutado a cualquier replica)
Traefik Dashboard: http://manager-1:8080
```

---

## 🏢 Configuración de producción

Recomendaciones para ambiente productivo.

### Checklist de seguridad

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
      restart_policy:
        condition: on-failure
        delay: 10s
        max_attempts: 5
        window: 120s
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
      rollback_config:
        parallelism: 1
        delay: 10s

secrets:
  kafka_username:
    external: true
  kafka_password:
    external: true

environment:
  - KAFKA_USERNAME_FILE=/run/secrets/kafka_username
  - KAFKA_PASSWORD_FILE=/run/secrets/kafka_password
```

### Crear secretos

```bash
echo "production_user" | docker secret create kafka_username -
echo "secure_password_123!" | docker secret create kafka_password -

docker secret ls
```

### Logs centralizados

```yaml
services:
  api:
    logging:
      driver: "splunk"
      options:
        splunk-token: "your-splunk-hec-token"
        splunk-url: "https://your-splunk-instance:8088"
        tag: "{{.Name}}/{{.ID}}"
        splunk-format: "json"
```

---

## 🚨 Disaster Recovery

Plan de recuperación ante fallos catastróficos.

### Escenario 1: Leader manager cae

```bash
# El Swarm elige automáticamente nuevo leader
# Los datos persisten en NFS/GlusterFS

# Cuando vuelva online
docker node ls
# Debe mostrarse como "Ready"
```

### Escenario 2: Todos los managers caen

```bash
# ⚠️ CRÍTICO: Necesitas recovery mode

# En un nodo manager (cuando vuelve)
docker swarm init --force-new-cluster

# Otros managers deben reenconectarse
docker swarm join --token SWMTKN-1-xxx...
```

### Escenario 3: Pérdida de datos

```bash
# Restaurar desde backup
./scripts/swarm-manager.sh restore ./backups/backup-20251216-120000

# Verificar integridad
docker stack ps recomendacion
```

### Plan de continuidad

```bash
#!/bin/bash
# Automatizar backup continuo en servidor externo

while true; do
    ./scripts/swarm-manager.sh backup /tmp/backup-$(date +%s)
    
    # Enviar a servidor remoto
    rsync -avz /tmp/backup-* user@backup-server:/remote/backups/
    
    # Limpiar locales
    find /tmp/backup-* -mtime +1 -delete
    
    sleep 3600  # Cada hora
done
```

---

## 📚 Recursos adicionales

- [Documentación oficial Docker Swarm](https://docs.docker.com/engine/swarm/)
- [Mejores prácticas de Swarm](https://docs.docker.com/engine/swarm/how-swarm-mode-works/nodes/)
- [GlusterFS Documentation](https://docs.gluster.org/)
- [Prometheus Setup](https://prometheus.io/docs/prometheus/latest/installation/)

---

**Última actualización:** 16 de diciembre de 2025
