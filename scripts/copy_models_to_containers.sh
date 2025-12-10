#!/bin/bash
#
# Script para copiar modelos entrenados a contenedores Docker
# ==============================================================
#
# Este script copia los modelos entrenados localmente al contenedor de la API
# y reinicia el servicio para que cargue los nuevos modelos.
#
# Uso:
#   ./scripts/copy_models_to_containers.sh [--restart]
#
# Opciones:
#   --restart: Reinicia el contenedor API después de copiar (default: true)
#
# Autor: Sistema de Recomendación a Gran Escala
# Fecha: 8 de diciembre de 2025
#

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Funciones de logging
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
# Configuración
# ==========================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TRAINED_MODELS_DIR="$PROJECT_ROOT/movies/trained_models"
DATASET_DIR="$PROJECT_ROOT/Dataset"
API_CONTAINER="recs-api"

# Parse argumentos
RESTART=true
if [[ "$1" == "--no-restart" ]]; then
    RESTART=false
fi

echo ""
echo "================================================================================"
echo "  COPIA DE MODELOS A CONTENEDORES DOCKER"
echo "================================================================================"
echo ""
echo "  Proyecto: $(basename "$PROJECT_ROOT")"
echo "  Modelos: $TRAINED_MODELS_DIR"
echo "  Contenedor: $API_CONTAINER"
echo "  Reiniciar: $RESTART"
echo ""
echo "================================================================================"
echo ""

# ==========================================
# 1. Verificar prerequisitos
# ==========================================

log_info "Verificando prerequisitos..."

# Verificar Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker no encontrado. Por favor, instala Docker."
    exit 1
fi

log_success "Docker encontrado"

# Verificar que el contenedor existe y está corriendo
if ! docker ps --format '{{.Names}}' | grep -q "^${API_CONTAINER}$"; then
    log_error "Contenedor $API_CONTAINER no está corriendo"
    log_info "Inicia el sistema con: docker-compose up -d"
    exit 1
fi

log_success "Contenedor $API_CONTAINER está corriendo"

# Verificar que existen modelos entrenados
if [ ! -d "$TRAINED_MODELS_DIR" ]; then
    log_error "Directorio de modelos no encontrado: $TRAINED_MODELS_DIR"
    log_info "Entrena los modelos con: ./scripts/train_all_models.sh"
    exit 1
fi

# Contar modelos disponibles
MODELS_COUNT=0
for model_type in als item_cf content_based hybrid; do
    if [ -L "$TRAINED_MODELS_DIR/$model_type/model_latest" ]; then
        MODELS_COUNT=$((MODELS_COUNT + 1))
    fi
done

if [ $MODELS_COUNT -eq 0 ]; then
    log_error "No se encontraron modelos entrenados"
    log_info "Entrena los modelos con: ./scripts/train_all_models.sh"
    exit 1
fi

log_success "Encontrados $MODELS_COUNT modelos entrenados"

echo ""

# ==========================================
# 2. Preparar metadata de películas
# ==========================================

log_info "Preparando metadata de películas..."

# El archivo movie.csv ya está montado como volumen en docker-compose.yml
# Pero verificamos que existe
if [ ! -f "$DATASET_DIR/movie.csv" ]; then
    log_warning "movie.csv no encontrado en $DATASET_DIR"
    log_warning "Las respuestas de la API no tendrán títulos de películas"
else
    log_success "movie.csv disponible"
fi

echo ""

# ==========================================
# 3. Mostrar información de modelos
# ==========================================

log_info "Modelos a desplegar:"
echo ""

for model_type in als item_cf content_based hybrid; do
    LATEST_LINK="$TRAINED_MODELS_DIR/$model_type/model_latest"
    
    if [ -L "$LATEST_LINK" ]; then
        MODEL_PATH=$(readlink -f "$LATEST_LINK")
        MODEL_NAME=$(basename "$MODEL_PATH")
        MODEL_SIZE=$(du -sh "$MODEL_PATH" | awk '{print $1}')
        
        echo "  📦 $model_type:"
        echo "     Versión: $MODEL_NAME"
        echo "     Tamaño: $MODEL_SIZE"
        
        # Leer metadata si existe
        METADATA_FILE="$MODEL_PATH/metadata.json"
        if [ -f "$METADATA_FILE" ]; then
            TIMESTAMP=$(jq -r '.timestamp // "unknown"' "$METADATA_FILE" 2>/dev/null | cut -c1-19)
            echo "     Fecha: $TIMESTAMP"
            
            # Métricas específicas por tipo
            if [ "$model_type" == "als" ]; then
                RMSE=$(jq -r '.metrics.rmse // "N/A"' "$METADATA_FILE" 2>/dev/null)
                echo "     RMSE: $RMSE"
            fi
        fi
        
        echo ""
    fi
done

# ==========================================
# 4. Confirmación del usuario
# ==========================================

read -p "¿Continuar con la copia de modelos? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warning "Operación cancelada por el usuario"
    exit 0
fi

echo ""

# ==========================================
# 5. Nota sobre volúmenes
# ==========================================

log_info "Verificando montaje de volúmenes..."

# Verificar que el volumen está montado
MOUNT_INFO=$(docker inspect $API_CONTAINER | jq -r '.[0].Mounts[] | select(.Destination == "/app/trained_models") | .Source')

if [ -z "$MOUNT_INFO" ]; then
    log_error "El volumen /app/trained_models NO está montado en el contenedor"
    log_error "Verifica docker-compose.yml:"
    echo ""
    echo "  api:"
    echo "    volumes:"
    echo "      - ./movies/trained_models:/app/trained_models:ro"
    echo ""
    exit 1
fi

log_success "Volumen montado correctamente: $MOUNT_INFO"

echo ""

# ==========================================
# 6. Los modelos ya están disponibles via volumen
# ==========================================

log_info "Los modelos están disponibles automáticamente via volumen montado"
log_success "No es necesario copiar archivos manualmente"

echo ""

# ==========================================
# 7. Reiniciar contenedor API (si solicitado)
# ==========================================

if [ "$RESTART" = true ]; then
    log_info "Reiniciando contenedor API para cargar nuevos modelos..."
    
    docker restart $API_CONTAINER > /dev/null
    
    log_success "Contenedor reiniciado"
    
    # Esperar a que el servicio esté disponible
    log_info "Esperando a que el servicio esté listo..."
    
    MAX_RETRIES=30
    RETRY=0
    
    while [ $RETRY -lt $MAX_RETRIES ]; do
        if docker exec $API_CONTAINER curl -sf http://localhost:8000/recommendations/health > /dev/null 2>&1; then
            log_success "Servicio listo"
            break
        fi
        
        RETRY=$((RETRY + 1))
        echo -n "."
        sleep 2
    done
    
    echo ""
    
    if [ $RETRY -eq $MAX_RETRIES ]; then
        log_warning "Timeout esperando al servicio"
        log_info "Verifica logs con: docker logs $API_CONTAINER"
    fi
else
    log_info "Contenedor NO reiniciado (usa --restart para reiniciar)"
fi

echo ""

# ==========================================
# 8. Verificar deployment
# ==========================================

log_info "Verificando deployment..."

# Verificar health check
if docker exec $API_CONTAINER curl -sf http://localhost:8000/recommendations/health > /dev/null 2>&1; then
    HEALTH_STATUS=$(docker exec $API_CONTAINER curl -s http://localhost:8000/recommendations/health | jq -r '.status // "unknown"')
    MODEL_VERSION=$(docker exec $API_CONTAINER curl -s http://localhost:8000/recommendations/health | jq -r '.model_version // "unknown"')
    
    if [ "$HEALTH_STATUS" == "healthy" ]; then
        log_success "API está funcionando correctamente"
        echo "  Versión del modelo: $MODEL_VERSION"
    else
        log_warning "API responde pero el servicio no está healthy"
        log_info "Status: $HEALTH_STATUS"
    fi
else
    log_warning "No se pudo verificar health check"
    log_info "El servicio podría estar iniciándose aún"
fi

echo ""

# ==========================================
# 9. Resumen y próximos pasos
# ==========================================

echo ""
echo "================================================================================"
echo "  ✅ DEPLOYMENT COMPLETADO"
echo "================================================================================"
echo ""
echo "  Modelos desplegados: $MODELS_COUNT"
echo "  Contenedor: $API_CONTAINER"
echo ""
echo "  Próximos pasos:"
echo "  ---------------"
echo "  1. Verificar logs:"
echo "     docker logs -f $API_CONTAINER"
echo ""
echo "  2. Probar recomendaciones para usuario 123:"
echo "     curl http://localhost:8000/recommendations/recommend/123?n=10"
echo ""
echo "  3. Ver documentación interactiva:"
echo "     http://localhost:8000/docs"
echo ""
echo "  4. Simular tráfico:"
echo "     python scripts/simulate_traffic.py --rate 50 --duration 300"
echo ""
echo "  5. Verificar métricas:"
echo "     curl http://localhost:8000/recommendations/health"
echo ""
echo "================================================================================"
echo ""

log_success "Script completado exitosamente"
exit 0
