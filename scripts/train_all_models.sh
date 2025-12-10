#!/bin/bash
#
# Script para entrenar todos los modelos de recomendación localmente
# ====================================================================
#
# Este script:
# 1. Crea un entorno virtual Python (si no existe)
# 2. Instala dependencias (PySpark, pandas, numpy)
# 3. Ejecuta el script de entrenamiento
# 4. Verifica que los modelos se guardaron correctamente
#
# Uso:
#   ./scripts/train_all_models.sh [--models ALS,ITEM_CF,CONTENT,HYBRID]
#
# Requirements:
#   - Python 3.8+
#   - Java 8+ (para PySpark)
#   - ~8GB RAM disponible
#
# Autor: Sistema de Recomendación a Gran Escala
# Fecha: 8 de diciembre de 2025
#

set -e  # Exit on error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ==========================================
# Funciones de utilidad
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
# Configuración
# ==========================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_ROOT/.venv-training"
TRAINING_SCRIPT="$PROJECT_ROOT/movies/src/recommendation/training/train_local_all.py"
DATASET_DIR="$PROJECT_ROOT/Dataset"
TRAINED_MODELS_DIR="$PROJECT_ROOT/movies/trained_models"

# Parse argumentos
MODELS_ARG="ALS,ITEM_CF,CONTENT,HYBRID"
FORCE_FLAG=""

for arg in "$@"; do
    case $arg in
        --models=*)
            MODELS_ARG="${arg#--models=}"
            shift
            ;;
        --force)
            FORCE_FLAG="--force"
            shift
            ;;
        *)
            ;;
    esac
done

echo ""
echo "================================================================================"
echo "  ENTRENAMIENTO LOCAL DE MODELOS DE RECOMENDACIÓN"
echo "================================================================================"
echo ""
echo "  Proyecto: $(basename "$PROJECT_ROOT")"
echo "  Modelos: $MODELS_ARG"
echo "  Dataset: $DATASET_DIR"
echo "  Output: $TRAINED_MODELS_DIR"
if [ -n "$FORCE_FLAG" ]; then
    echo "  Modo: FORZAR RE-ENTRENAMIENTO"
else
    echo "  Modo: OMITIR MODELOS EXISTENTES"
fi
echo ""
echo "================================================================================"
echo ""

# ==========================================
# 1. Verificar prerequisitos
# ==========================================

log_info "Verificando prerequisitos..."

# Verificar Python
if ! command -v python3 &> /dev/null; then
    log_error "Python3 no encontrado. Por favor, instala Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
log_success "Python $PYTHON_VERSION encontrado"

# Verificar Java (para PySpark)
if ! command -v java &> /dev/null; then
    log_warning "Java no encontrado. PySpark requiere Java 8+."
    log_warning "Instala Java con: sudo apt install openjdk-11-jdk"
    exit 1
fi

JAVA_VERSION=$(java -version 2>&1 | head -n 1 | awk -F '"' '{print $2}')
log_success "Java $JAVA_VERSION encontrado"

# Verificar que existen los datos
if [ ! -f "$DATASET_DIR/rating.csv" ]; then
    log_error "No se encuentra $DATASET_DIR/rating.csv"
    log_error "Por favor, asegúrate de que los datos estén en la carpeta Dataset/"
    exit 1
fi

log_success "Archivos de datos encontrados"

# Verificar memoria disponible
AVAILABLE_MEM=$(free -g | awk '/^Mem:/{print $7}')
if [ "$AVAILABLE_MEM" -lt 6 ]; then
    log_warning "Memoria disponible: ${AVAILABLE_MEM}GB (recomendado: 8GB+)"
    log_warning "El entrenamiento puede ser lento o fallar con poca memoria"
    read -p "¿Continuar de todos modos? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    log_success "Memoria disponible: ${AVAILABLE_MEM}GB"
fi

echo ""

# ==========================================
# 2. Crear/activar entorno virtual
# ==========================================

log_info "Configurando entorno virtual Python..."

if [ ! -d "$VENV_DIR" ]; then
    log_info "Creando nuevo entorno virtual en $VENV_DIR"
    python3 -m venv "$VENV_DIR"
    log_success "Entorno virtual creado"
else
    log_success "Entorno virtual existente encontrado"
fi

# Activar entorno virtual
source "$VENV_DIR/bin/activate"
log_success "Entorno virtual activado"

# ==========================================
# 3. Instalar dependencias
# ==========================================

log_info "Instalando/verificando dependencias..."

# Actualizar pip
pip install --quiet --upgrade pip

# Instalar dependencias necesarias
REQUIREMENTS="pyspark pandas numpy"
log_info "Instalando: $REQUIREMENTS"
pip install --quiet $REQUIREMENTS

# Verificar instalación
if python3 -c "import pyspark" 2>/dev/null; then
    PYSPARK_VERSION=$(python3 -c "import pyspark; print(pyspark.__version__)")
    log_success "PySpark $PYSPARK_VERSION instalado"
else
    log_error "Error al instalar PySpark"
    exit 1
fi

echo ""

# ==========================================
# 4. Crear directorios de salida
# ==========================================

log_info "Preparando directorios de salida..."

mkdir -p "$TRAINED_MODELS_DIR"/{als,item_cf,content_based,hybrid}

for dir in als item_cf content_based hybrid; do
    mkdir -p "$TRAINED_MODELS_DIR/$dir"
    # Crear .gitkeep si no existe
    if [ ! -f "$TRAINED_MODELS_DIR/$dir/.gitkeep" ]; then
        touch "$TRAINED_MODELS_DIR/$dir/.gitkeep"
    fi
done

log_success "Directorios preparados"

echo ""

# ==========================================
# 5. Ejecutar entrenamiento
# ==========================================

log_info "Iniciando entrenamiento de modelos..."
log_info "Esto puede tomar 30-60 minutos dependiendo del hardware..."
echo ""

START_TIME=$(date +%s)

# Ejecutar script de entrenamiento
if python3 "$TRAINING_SCRIPT" --models "$MODELS_ARG" $FORCE_FLAG; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    MINUTES=$((DURATION / 60))
    SECONDS=$((DURATION % 60))
    
    echo ""
    log_success "Entrenamiento completado en ${MINUTES}m ${SECONDS}s"
else
    log_error "El entrenamiento falló. Revisa los logs arriba."
    exit 1
fi

echo ""

# ==========================================
# 6. Verificar modelos generados
# ==========================================

log_info "Verificando modelos generados..."
echo ""

MODELS_FOUND=0

for model_type in als item_cf content_based hybrid; do
    LATEST_LINK="$TRAINED_MODELS_DIR/$model_type/model_latest"
    
    if [ -L "$LATEST_LINK" ]; then
        MODEL_PATH=$(readlink -f "$LATEST_LINK")
        MODEL_SIZE=$(du -sh "$MODEL_PATH" | awk '{print $1}')
        log_success "$model_type: $MODEL_SIZE ($(basename "$MODEL_PATH"))"
        MODELS_FOUND=$((MODELS_FOUND + 1))
    else
        log_warning "$model_type: No encontrado"
    fi
done

echo ""

if [ $MODELS_FOUND -eq 0 ]; then
    log_error "No se generaron modelos. Revisa los errores arriba."
    exit 1
fi

# ==========================================
# 7. Resumen y próximos pasos
# ==========================================

echo ""
echo "================================================================================"
echo "  ✅ ENTRENAMIENTO COMPLETADO"
echo "================================================================================"
echo ""
echo "  Modelos generados: $MODELS_FOUND"
echo "  Ubicación: $TRAINED_MODELS_DIR"
echo ""
echo "  Próximos pasos:"
echo "  ---------------"
echo "  1. Verificar modelos:"
echo "     ls -lh $TRAINED_MODELS_DIR/*/model_latest"
echo ""
echo "  2. Copiar modelos a contenedores Docker:"
echo "     ./scripts/copy_models_to_containers.sh"
echo ""
echo "  3. Iniciar sistema (si no está corriendo):"
echo "     docker-compose up -d"
echo ""
echo "  4. Probar recomendaciones:"
echo "     curl http://localhost:8000/recommend/123?n=10"
echo ""
echo "  5. Simular tráfico:"
echo "     python scripts/simulate_traffic.py --rate 50 --duration 300"
echo ""
echo "================================================================================"
echo ""

# Desactivar entorno virtual
deactivate

log_success "Script completado exitosamente"
exit 0
