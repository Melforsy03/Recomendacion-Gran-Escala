#!/bin/bash

# ==========================================
# GESTOR DE STACK SWARM
# ==========================================
# Script para facilitar operaciones comunes en Docker Swarm
#
# Uso:
#   ./swarm-manager.sh init [--advertise-addr IP]
#   ./swarm-manager.sh join-token
#   ./swarm-manager.sh deploy
#   ./swarm-manager.sh status
#   ./swarm-manager.sh scale SERVICE REPLICAS
#   ./swarm-manager.sh update SERVICE IMAGE
#   ./swarm-manager.sh logs SERVICE [lines]
#   ./swarm-manager.sh remove
#   ./swarm-manager.sh help

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

STACK_NAME="recomendacion"
COMPOSE_FILE="docker-compose.swarm.yml"
PROJECT_ROOT=$(dirname "$(readlink -f "$0")")

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# ==========================================
# INIT - Inicializar Swarm
# ==========================================

init_swarm() {
    local advertise_addr="${1:---advertise-addr}"
    
    log_info "Inicializando Docker Swarm..."
    
    if docker info | grep -q "Swarm: active"; then
        log_warning "Swarm ya está activo"
        docker node ls
        return 0
    fi
    
    if [[ "$advertise_addr" == "--advertise-addr" ]]; then
        # Detectar IP automáticamente
        local ip=$(hostname -I | awk '{print $1}')
        log_info "Usando IP detectada: $ip"
        advertise_addr="$ip"
    fi
    
    docker swarm init --advertise-addr "$advertise_addr"
    
    log_success "Swarm inicializado"
    docker node ls
}

# ==========================================
# JOIN-TOKEN - Obtener token para unirse
# ==========================================

get_join_token() {
    local role="${1:-manager}"
    
    if ! docker info | grep -q "Swarm: active"; then
        log_error "Swarm no está activo"
        return 1
    fi
    
    log_info "Token para unirse como $role:"
    echo ""
    docker swarm join-token "$role" | grep "docker swarm join"
    echo ""
}

# ==========================================
# DEPLOY - Desplegar stack
# ==========================================

deploy_stack() {
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Archivo $COMPOSE_FILE no encontrado"
        return 1
    fi
    
    if ! docker info | grep -q "Swarm: active"; then
        log_error "Swarm no está activo. Ejecuta: $0 init"
        return 1
    fi
    
    log_info "Validando configuración..."
    docker compose -f "$COMPOSE_FILE" config > /dev/null || {
        log_error "Configuración inválida"
        return 1
    }
    
    log_info "Desplegando stack '$STACK_NAME'..."
    docker stack deploy -c "$COMPOSE_FILE" "$STACK_NAME"
    
    log_success "Stack desplegado"
    sleep 2
    show_status
}

# ==========================================
# STATUS - Ver estado del stack
# ==========================================

show_status() {
    log_info "Estado del stack '$STACK_NAME':\n"
    
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}SERVICIOS${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    docker service ls --filter "label=com.docker.stack.namespace=$STACK_NAME" \
        --format "table {{.Name}}\t{{.Mode}}\t{{.Replicas}}\t{{.Image}}" | \
        awk '{if(NR>1) printf "%-40s %-15s %-10s %s\n", $1, $2, $3, $4; else print}' || true
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}TAREAS${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    docker stack ps "$STACK_NAME" --no-trunc \
        --format "table {{.Name}}\t{{.Node}}\t{{.DesiredState}}\t{{.CurrentState}}" | \
        awk '{if(NR>1) printf "%-40s %-15s %-15s %s\n", $1, $2, $3, $4; else print}' || true
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}NODOS${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    docker node ls --format "table {{.Hostname}}\t{{.Status}}\t{{.ManagerStatus}}\t{{.EngineVersion}}" | \
        awk '{if(NR>1) printf "%-20s %-10s %-15s %s\n", $1, $2, $3, $4; else print}' || true
}

# ==========================================
# SCALE - Escalar servicio
# ==========================================

scale_service() {
    local service="${STACK_NAME}_${1}"
    local replicas="$2"
    
    if [ -z "$service" ] || [ -z "$replicas" ]; then
        log_error "Uso: $0 scale SERVICE_NAME REPLICAS"
        return 1
    fi
    
    log_info "Escalando $service a $replicas replicas..."
    docker service scale "$service=$replicas"
    
    log_success "Servicio escalado"
    sleep 1
    docker service ps "$service" --no-trunc
}

# ==========================================
# UPDATE - Actualizar servicio
# ==========================================

update_service() {
    local service="${STACK_NAME}_${1}"
    local image="$2"
    
    if [ -z "$service" ] || [ -z "$image" ]; then
        log_error "Uso: $0 update SERVICE_NAME IMAGE:TAG"
        return 1
    fi
    
    log_info "Actualizando $service con imagen $image..."
    docker service update --image "$image" "$service"
    
    log_success "Servicio en actualización"
    log_info "Esperando a que se complete..."
    sleep 2
    docker service ps "$service" --no-trunc
}

# ==========================================
# LOGS - Ver logs de servicio
# ==========================================

show_logs() {
    local service="${STACK_NAME}_${1}"
    local lines="${2:-50}"
    
    if [ -z "$service" ]; then
        log_error "Uso: $0 logs SERVICE_NAME [LINES]"
        return 1
    fi
    
    log_info "Logs de $service (últimas $lines líneas):"
    docker service logs "$service" --tail "$lines" -f 2>/dev/null || {
        log_warning "No hay logs disponibles. Intenta más tarde."
    }
}

# ==========================================
# REMOVE - Eliminar stack
# ==========================================

remove_stack() {
    log_warning "¿Estás seguro de que deseas eliminar el stack '$STACK_NAME'?"
    echo -e "Escribe '${YELLOW}SI${NC}' para confirmar:"
    read -r confirmation
    
    if [ "$confirmation" != "SI" ]; then
        log_warning "Operación cancelada"
        return 0
    fi
    
    log_info "Eliminando stack '$STACK_NAME'..."
    docker stack rm "$STACK_NAME"
    
    log_success "Stack eliminado"
    log_info "Los volúmenes persistentes se mantienen"
}

# ==========================================
# HEALTH-CHECK - Verificar salud del cluster
# ==========================================

health_check() {
    log_info "Verificando salud del cluster...\n"
    
    # Verificar Swarm
    if docker info | grep -q "Swarm: active"; then
        log_success "Swarm está activo"
    else
        log_error "Swarm no está activo"
        return 1
    fi
    
    # Verificar nodos
    local down_nodes=$(docker node ls --filter "status=Down" -q | wc -l)
    if [ "$down_nodes" -gt 0 ]; then
        log_warning "$down_nodes nodos están caídos"
    else
        log_success "Todos los nodos activos"
    fi
    
    # Verificar servicios
    local stack_exists=$(docker service ls --filter "label=com.docker.stack.namespace=$STACK_NAME" -q | wc -l)
    if [ "$stack_exists" -eq 0 ]; then
        log_warning "Stack no está desplegado"
    else
        log_success "Stack activo"
    fi
    
    # Verificar réplicas
    local unhealthy=$(docker stack ps "$STACK_NAME" 2>/dev/null | grep -v "Running" | wc -l)
    if [ "$unhealthy" -gt 1 ]; then
        log_warning "$unhealthy tareas no están en estado Running"
    else
        log_success "Todas las tareas en estado Running"
    fi
    
    # Verificar volúmenes
    local volumes=$(docker volume ls -q | wc -l)
    log_success "$volumes volúmenes disponibles"
}

# ==========================================
# BACKUP/RESTORE - Respaldo de datos
# ==========================================

backup_volumes() {
    local backup_dir="${1:-./backup-$(date +%Y%m%d-%H%M%S)}"
    
    log_info "Creando respaldo en $backup_dir..."
    mkdir -p "$backup_dir"
    
    # Listar volúmenes del stack
    local volumes=$(docker volume ls --filter "label=com.docker.stack.namespace=$STACK_NAME" -q)
    
    for vol in $volumes; do
        log_info "Respaldando volumen: $vol"
        docker run --rm \
            -v "$vol:/data" \
            -v "$backup_dir:/backup" \
            alpine tar czf "/backup/$vol.tar.gz" -C /data .
    done
    
    log_success "Respaldo completado en $backup_dir"
}

restore_volumes() {
    local backup_dir="$1"
    
    if [ ! -d "$backup_dir" ]; then
        log_error "Directorio de respaldo no encontrado: $backup_dir"
        return 1
    fi
    
    log_warning "¿Estás seguro de que deseas restaurar desde $backup_dir?"
    echo -e "Escribe '${YELLOW}SI${NC}' para confirmar:"
    read -r confirmation
    
    if [ "$confirmation" != "SI" ]; then
        log_warning "Operación cancelada"
        return 0
    fi
    
    for backup_file in "$backup_dir"/*.tar.gz; do
        [ -f "$backup_file" ] || continue
        local vol=$(basename "$backup_file" .tar.gz)
        
        log_info "Restaurando volumen: $vol"
        docker run --rm \
            -v "$vol:/data" \
            -v "$backup_dir:/backup" \
            alpine tar xzf "/backup/$(basename "$backup_file")" -C /data
    done
    
    log_success "Restauración completada"
}

# ==========================================
# HELP - Mostrar ayuda
# ==========================================

show_help() {
    cat << EOF
${BLUE}╔════════════════════════════════════════════════════════════╗${NC}
${BLUE}║         GESTOR DE STACK DOCKER SWARM                       ║${NC}
${BLUE}╚════════════════════════════════════════════════════════════╝${NC}

${YELLOW}COMANDOS:${NC}

  ${GREEN}init${NC} [--advertise-addr IP]
    Inicializar Docker Swarm en esta máquina
    Ejemplo: ./swarm-manager.sh init --advertise-addr 192.168.1.100

  ${GREEN}join-token${NC} [manager|worker]
    Obtener token para unir otros nodos al Swarm
    Ejemplo: ./swarm-manager.sh join-token manager

  ${GREEN}deploy${NC}
    Desplegar el stack desde docker-compose.swarm.yml

  ${GREEN}status${NC}
    Ver estado del stack, servicios y tareas

  ${GREEN}scale${NC} SERVICE REPLICAS
    Escalar un servicio a N replicas
    Ejemplo: ./swarm-manager.sh scale api 4

  ${GREEN}update${NC} SERVICE IMAGE:TAG
    Actualizar imagen de un servicio
    Ejemplo: ./swarm-manager.sh update api localhost:5000/recs-api:v2

  ${GREEN}logs${NC} SERVICE [LINES]
    Ver logs de un servicio (seguimiento en tiempo real)
    Ejemplo: ./swarm-manager.sh logs api 100

  ${GREEN}health${NC}
    Verificar salud general del cluster

  ${GREEN}backup${NC} [DIRECTORIO]
    Crear respaldo de volúmenes persistentes
    Ejemplo: ./swarm-manager.sh backup ./backups

  ${GREEN}restore${NC} DIRECTORIO
    Restaurar volúmenes desde respaldo
    Ejemplo: ./swarm-manager.sh restore ./backups

  ${GREEN}remove${NC}
    Eliminar el stack completo (pide confirmación)

  ${GREEN}help${NC}
    Mostrar este mensaje de ayuda

${YELLOW}EJEMPLOS DE FLUJO COMPLETO:${NC}

  # Primera vez en manager-1
  ./swarm-manager.sh init --advertise-addr 192.168.1.100
  ./swarm-manager.sh join-token manager

  # En manager-2
  docker swarm join --token SWMTKN-1-xxx... 192.168.1.100:2377
  ./swarm-manager.sh status

  # Volver a manager-1
  ./swarm-manager.sh deploy
  ./swarm-manager.sh status
  ./swarm-manager.sh scale api 3

${YELLOW}TROUBLESHOOTING:${NC}

  docker node ls                    # Ver nodos del cluster
  docker service ls                 # Ver servicios activos
  docker stats                      # Ver uso de recursos
  docker events --filter "type=service"  # Monitorear eventos

${YELLOW}DOCUMENTACIÓN:${NC}

  Guía completa: docs/GUIA_DESPLIEGUE_SWARM.md

EOF
}

# ==========================================
# MAIN
# ==========================================

main() {
    local command="${1:-help}"
    
    case "$command" in
        init)
            init_swarm "${2:-}"
            ;;
        join-token)
            get_join_token "${2:-manager}"
            ;;
        deploy)
            deploy_stack
            ;;
        status)
            show_status
            ;;
        scale)
            scale_service "$2" "$3"
            ;;
        update)
            update_service "$2" "$3"
            ;;
        logs)
            show_logs "$2" "${3:-50}"
            ;;
        health)
            health_check
            ;;
        backup)
            backup_volumes "${2:-}"
            ;;
        restore)
            restore_volumes "$2"
            ;;
        remove)
            remove_stack
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Comando desconocido: $command"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
