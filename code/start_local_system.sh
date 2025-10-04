#!/bin/bash

echo "🎬 INICIANDO SISTEMA DE RECOMENDACIÓN (MODO LOCAL MEJORADO)"
echo "=========================================================="

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Función para mostrar mensajes
log_info() { echo -e "${BLUE}ℹ️ $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Función para matar procesos en puertos
kill_port() {
    log_warning "Cerrando procesos en puerto $1..."
    sudo lsof -ti:$1 | xargs kill -9 2>/dev/null || true
}

# Función para verificar si un puerto está en uso
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        return 0
    else
        return 1
    fi
}

# Función para esperar puerto
wait_for_port() {
    local port=$1
    local service=$2
    local max_attempts=20
    local attempt=1
    
    log_info "Esperando a $service en puerto $port..."
    
    while ! check_port $port; do
        if [ $attempt -eq $max_attempts ]; then
            log_error "$service no se inició en puerto $port"
            return 1
        fi
        sleep 2
        ((attempt++))
    done
    log_success "$service listo en puerto $port"
}

# Verificar que estamos en el directorio correcto
if [ ! -f "movies.json" ]; then
    log_error "No se encuentra movies.json. Ejecuta desde ~/Escritorio/Big-Data/code/"
    exit 1
fi

# Activar entorno virtual
log_info "Activando entorno virtual Python..."
source ../myenv/bin/activate

# Limpiar procesos anteriores
log_info "Limpiando procesos anteriores..."
kill_port 2181  # Zookeeper
kill_port 9092  # Kafka
kill_port 8050  # Dashboard
pkill -f "python.*producer" 2>/dev/null || true
pkill -f "python.*consumer" 2>/dev/null || true
sleep 2

# Verificar e iniciar Hadoop
log_info "Verificando Hadoop..."
if ! jps | grep -q "NameNode"; then
    log_warning "Iniciando Hadoop..."
    cd ../hadoop-3.3.1
    start-dfs.sh > /dev/null 2>&1
    start-yarn.sh > /dev/null 2>&1
    cd ../code
    sleep 5
fi
log_success "Hadoop funcionando"

# Iniciar Zookeeper
log_info "Iniciando Zookeeper..."
cd ../kafka_2.13-2.8.1
nohup bin/zookeeper-server-start.sh config/zookeeper.properties > zookeeper.log 2>&1 &
ZOOKEEPER_PID=$!
log_success "Zookeeper iniciado (PID: $ZOOKEEPER_PID)"

wait_for_port 2181 "Zookeeper"

# Iniciar Kafka
log_info "Iniciando Kafka..."
nohup bin/kafka-server-start.sh config/server.properties > kafka.log 2>&1 &
KAFKA_PID=$!
log_success "Kafka iniciado (PID: $KAFKA_PID)"

wait_for_port 9092 "Kafka"

# Crear topic
log_info "Configurando topic de Kafka..."
bin/kafka-topics.sh --create --topic movie-interactions --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1 2>/dev/null || log_warning "El topic ya existe"

cd ../code

# Iniciar Consumer
log_info "Iniciando Consumer de Métricas..."
nohup python simple_consumer.py > consumer.log 2>&1 &
CONSUMER_PID=$!
log_success "Consumer iniciado (PID: $CONSUMER_PID)"

# Iniciar Producer
log_info "Iniciando Producer de Datos..."
nohup python producer.py > producer.log 2>&1 &
PRODUCER_PID=$!
log_success "Producer iniciado (PID: $PRODUCER_PID)"

# Esperar a que se generen algunos datos
log_info "Esperando a que se generen datos iniciales..."
sleep 5

# Iniciar Dashboard
log_info "Iniciando Dashboard..."
echo ""
echo "🎉 ========================================="
echo "🎬 SISTEMA INICIADO CORRECTAMENTE!"
echo "📊 Dashboard: ${GREEN}http://localhost:8050${NC}"
echo "📋 Logs: producer.log, consumer.log"
echo "🛑 Para detener: ./stop_local_system.sh"
echo "🔍 Para ver logs en tiempo real: tail -f consumer.log"
echo "=========================================="
echo ""

# Guardar PIDs para limpieza
echo "ZOOKEEPER_PID=$ZOOKEEPER_PID" > running_pids.txt
echo "KAFKA_PID=$KAFKA_PID" >> running_pids.txt
echo "PRODUCER_PID=$PRODUCER_PID" >> running_pids.txt
echo "CONSUMER_PID=$CONSUMER_PID" >> running_pids.txt

# Función de limpieza
cleanup() {
    echo ""
    log_warning "Deteniendo sistema..."
    
    # Leer y matar procesos guardados
    if [ -f running_pids.txt ]; then
        while IFS='=' read -r key pid; do
            if [ ! -z "$pid" ] && kill -0 $pid 2>/dev/null; then
                kill $pid 2>/dev/null && log_success "Detenido: $key ($pid)" || log_error "Error deteniendo $key"
            fi
        done < running_pids.txt
        rm -f running_pids.txt
    fi
    
    # Limpieza adicional
    kill_port 2181
    kill_port 9092
    kill_port 8050
    
    log_success "Sistema completamente detenido"
    exit 0
}

# Configurar trap para Ctrl+C
trap cleanup SIGINT SIGTERM

# Iniciar Dashboard (en primer plano)
python dashboard.py

# Si el dashboard se cierra, limpiar
cleanup
