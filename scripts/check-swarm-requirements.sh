#!/bin/bash

# ==========================================
# VERIFICADOR DE REQUISITOS PARA SWARM
# ==========================================
# Script para validar que todas las dependencias y configuraciones
# necesarias estén presentes antes de desplegar el stack
#
# Uso: ./check-swarm-requirements.sh

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Contadores
PASSED=0
FAILED=0
WARNINGS=0

# ==========================================
# FUNCIONES DE LOGGING
# ==========================================

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

check_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_section() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# ==========================================
# VERIFICACIONES
# ==========================================

check_docker() {
    print_section "1. DOCKER"
    
    # Verificar si Docker está instalado
    if ! command -v docker &> /dev/null; then
        check_fail "Docker no está instalado"
        return 1
    fi
    check_pass "Docker instalado"
    
    # Verificar versión de Docker
    local docker_version=$(docker version --format '{{.Server.Version}}')
    check_pass "Versión de Docker: $docker_version"
    
    # Verificar si Docker daemon está corriendo
    if ! docker info &> /dev/null; then
        check_fail "Docker daemon no está corriendo"
        return 1
    fi
    check_pass "Docker daemon activo"
    
    # Verificar permisos
    if ! docker ps &> /dev/null; then
        check_warn "Posible problema de permisos - usuario no en grupo docker"
        return 0
    fi
    check_pass "Permisos de Docker correctos"
}

check_docker_compose() {
    print_section "2. DOCKER COMPOSE"
    
    # Verificar docker compose
    if ! command -v docker &> /dev/null; then
        check_fail "docker compose CLI no disponible"
        return 1
    fi
    
    if ! docker compose version &> /dev/null; then
        check_fail "docker compose plugin no está instalado"
        return 1
    fi
    
    local compose_version=$(docker compose version --short)
    check_pass "Docker Compose instalado: $compose_version"
}

check_swarm() {
    print_section "3. DOCKER SWARM"
    
    # Verificar si Swarm está activo
    if docker info 2>/dev/null | grep -q "Swarm: active"; then
        check_pass "Swarm está activo"
        
        # Mostrar rol
        local role=$(docker info 2>/dev/null | grep "Is Manager" | awk '{print $NF}')
        if [ "$role" = "true" ]; then
            check_pass "Este nodo es MANAGER"
        else
            check_warn "Este nodo es WORKER (necesita manager para desplegar)"
        fi
        
        # Contar nodos
        local node_count=$(docker node ls 2>/dev/null | tail -n +2 | wc -l)
        check_pass "Nodos en cluster: $node_count"
        
        # Verificar estado de nodos
        local down_nodes=$(docker node ls 2>/dev/null | grep -i "down" | wc -l)
        if [ "$down_nodes" -gt 0 ]; then
            check_warn "$down_nodes nodo(s) en estado Down"
        else
            check_pass "Todos los nodos activos"
        fi
    else
        check_warn "Swarm no está inicializado (usar: docker swarm init)"
    fi
}

check_network() {
    print_section "4. RED OVERLAY"
    
    local overlay_networks=$(docker network ls --driver overlay -q 2>/dev/null | wc -l)
    
    if [ "$overlay_networks" -eq 0 ]; then
        check_warn "No hay redes overlay (se crearán automáticamente al desplegar)"
    else
        check_pass "Redes overlay encontradas: $overlay_networks"
    fi
    
    # Verificar conectividad entre nodos (si hay múltiples)
    local node_count=$(docker node ls -q 2>/dev/null | wc -l)
    if [ "$node_count" -gt 1 ]; then
        check_info "Cluster multi-nodo detectado - verificar conectividad entre nodos"
        check_warn "Puertos requeridos: 2377/tcp, 7946/tcp, 7946/udp, 4789/udp"
    fi
}

check_volumes() {
    print_section "5. VOLÚMENES Y ALMACENAMIENTO"
    
    # Verificar volúmenes locales
    local local_volumes=$(docker volume ls --driver local -q 2>/dev/null | wc -l)
    check_pass "Volúmenes locales disponibles: $local_volumes"
    
    # Verificar si NFS está disponible
    if command -v mount &> /dev/null; then
        if grep -q "nfs" /proc/filesystems; then
            check_pass "NFS soportado en el kernel"
            
            # Intentar conectar a NFS (si está configurado)
            if command -v showmount &> /dev/null; then
                check_pass "Cliente NFS instalado"
            fi
        else
            check_warn "NFS no soportado - considerar volúmenes locales o GlusterFS"
        fi
    fi
    
    # Verificar espacio disponible
    local available_space=$(df / | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 5242880 ]; then  # < 5GB
        check_warn "Espacio disponible bajo: $(df -h / | awk 'NR==2 {print $4}')"
    else
        check_pass "Espacio disponible: $(df -h / | awk 'NR==2 {print $4}')"
    fi
}

check_images() {
    print_section "6. IMÁGENES DOCKER"
    
    # Verificar imágenes requeridas
    local required_images=(
        "bde2020/hadoop-namenode:2.0.0-hadoop3.2.1-java8"
        "bde2020/hadoop-datanode:2.0.0-hadoop3.2.1-java8"
        "apache/spark:3.4.1"
        "confluentinc/cp-zookeeper:6.2.0"
        "confluentinc/cp-kafka:6.2.0"
    )
    
    for img in "${required_images[@]}"; do
        if docker images --quiet "$img" 2>/dev/null | grep -q .; then
            check_pass "Imagen disponible: $img"
        else
            check_warn "Imagen no encontrada: $img (se descargará al desplegar)"
        fi
    done
    
    # Verificar imágenes personalizadas
    if docker images --quiet "localhost:5000/recs-api" 2>/dev/null | grep -q .; then
        check_pass "Imagen personalizada: recs-api"
    else
        check_warn "Imagen personalizada recs-api no encontrada (compilar: docker build ./movies/api)"
    fi
    
    if docker images --quiet "localhost:5000/recs-dashboard" 2>/dev/null | grep -q .; then
        check_pass "Imagen personalizada: recs-dashboard"
    else
        check_warn "Imagen personalizada recs-dashboard no encontrada (compilar: docker build ./movies/dashboard)"
    fi
}

check_resources() {
    print_section "7. RECURSOS DEL SISTEMA"
    
    # CPU
    local cpu_count=$(nproc 2>/dev/null || echo "desconocido")
    if [ "$cpu_count" != "desconocido" ] && [ "$cpu_count" -lt 4 ]; then
        check_warn "CPU cores limitados: $cpu_count (recomendado: 4+)"
    else
        check_pass "CPU cores: $cpu_count"
    fi
    
    # Memoria
    if command -v free &> /dev/null; then
        local total_mem=$(free -m 2>/dev/null | awk 'NR==2 {print $2}')
        if [ "$total_mem" -lt 8192 ]; then
            check_warn "Memoria limitada: ${total_mem}MB (recomendado: 8GB+)"
        else
            check_pass "Memoria disponible: ${total_mem}MB"
        fi
    fi
    
    # Límites de archivos abiertos
    if command -v ulimit &> /dev/null; then
        local open_files=$(ulimit -n 2>/dev/null || echo "desconocido")
        if [ "$open_files" != "desconocido" ] && [ "$open_files" -lt 65536 ]; then
            check_warn "Límite de archivos abiertos bajo: $open_files (recomendado: 65536+)"
        else
            check_pass "Límite de archivos abiertos: $open_files"
        fi
    fi
}

check_configuration() {
    print_section "8. CONFIGURACIÓN"
    
    # Verificar archivo docker-compose.swarm.yml
    if [ -f "docker-compose.swarm.yml" ]; then
        check_pass "Archivo docker-compose.swarm.yml encontrado"
        
        # Validar sintaxis
        if docker compose -f docker-compose.swarm.yml config > /dev/null 2>&1; then
            check_pass "Sintaxis de docker-compose.swarm.yml válida"
        else
            check_fail "Error en sintaxis de docker-compose.swarm.yml"
        fi
    else
        check_fail "Archivo docker-compose.swarm.yml no encontrado"
    fi
    
    # Verificar archivo de configuración
    if [ -f "docs/GUIA_DESPLIEGUE_SWARM.md" ]; then
        check_pass "Guía de despliegue encontrada"
    else
        check_warn "Guía de despliegue no encontrada"
    fi
}

check_connectivity() {
    print_section "9. CONECTIVIDAD"
    
    # Verificar DNS
    if command -v nslookup &> /dev/null; then
        if nslookup google.com &> /dev/null; then
            check_pass "Resolución DNS funcional"
        else
            check_warn "No se puede resolver DNS (importante para descargar imágenes)"
        fi
    fi
    
    # Verificar acceso a Docker Hub
    if docker pull --quiet "hello-world" 2>/dev/null; then
        check_pass "Acceso a Docker Hub funcional"
        docker rmi "hello-world:latest" 2>/dev/null || true
    else
        check_warn "No se puede acceder a Docker Hub"
    fi
}

print_summary() {
    print_section "RESUMEN"
    
    local total=$((PASSED + FAILED + WARNINGS))
    
    echo ""
    echo -e "Verificaciones completadas: $total"
    echo -e "${GREEN}✓ Pasadas: $PASSED${NC}"
    echo -e "${YELLOW}⚠ Advertencias: $WARNINGS${NC}"
    echo -e "${RED}✗ Fallos: $FAILED${NC}"
    echo ""
    
    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ ¡LISTO PARA DESPLEGAR!${NC}"
        echo ""
        echo "Próximos pasos:"
        echo "  1. Compilar imágenes personalizadas:"
        echo "     docker build -t localhost:5000/recs-api:latest ./movies/api/"
        echo "     docker build -t localhost:5000/recs-dashboard:latest ./movies/dashboard/"
        echo ""
        echo "  2. Desplegar stack:"
        echo "     ./scripts/swarm-manager.sh deploy"
        echo ""
        echo "  3. Monitorear:"
        echo "     ./scripts/swarm-manager.sh status"
        echo ""
    else
        echo -e "${RED}✗ FALLOS DETECTADOS${NC}"
        echo "Soluciona los problemas anteriores antes de desplegar"
        echo ""
    fi
}

# ==========================================
# MAIN
# ==========================================

main() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║      VERIFICADOR DE REQUISITOS - DOCKER SWARM              ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    check_docker
    check_docker_compose
    check_swarm
    check_network
    check_volumes
    check_images
    check_resources
    check_configuration
    check_connectivity
    
    print_summary
    
    # Retornar código de error si hay fallos
    if [ $FAILED -gt 0 ]; then
        exit 1
    fi
}

main "$@"
