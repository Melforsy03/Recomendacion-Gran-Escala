#!/bin/bash

echo "🛑 DETENIENDO SISTEMA LOCAL"
echo "==========================="

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }

# Matar procesos por puerto
kill_port() {
    sudo lsof -ti:$1 | xargs kill -9 2>/dev/null || true
}

# Detener procesos guardados
if [ -f running_pids.txt ]; then
    log_warning "Deteniendo procesos guardados..."
    while IFS='=' read -r key pid; do
        if [ ! -z "$pid" ]; then
            if kill -0 $pid 2>/dev/null; then
                kill $pid 2>/dev/null
                log_success "Detenido: $key (PID: $pid)"
            fi
        fi
    done < running_pids.txt
    rm -f running_pids.txt
fi

# Limpieza de puertos
kill_port 2181
kill_port 9092  
kill_port 8050

# Detener procesos Python
pkill -f "python.*producer" 2>/dev/null && log_success "Producer detenido"
pkill -f "python.*consumer" 2>/dev/null && log_success "Consumer detenido"
pkill -f "python.*dashboard" 2>/dev/null && log_success "Dashboard detenido"

echo ""
log_success "Sistema local completamente detenido"
