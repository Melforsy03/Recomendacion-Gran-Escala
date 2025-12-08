#!/bin/bash
###############################################################################
# Script para Importar Modelo ALS desde Kaggle
###############################################################################
#
# Uso: ./import_kaggle_model.sh /ruta/al/archivo.tar.gz [nombre_version]
#
# Ejemplo:
#   ./import_kaggle_model.sh ~/Downloads/als_model_v1_20251208.tar.gz
#   ./import_kaggle_model.sh ~/Downloads/als_model.tar.gz model_kaggle_v1
#
###############################################################################

set -e  # Salir si hay error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir con color
print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

###############################################################################
# Validar argumentos
###############################################################################

if [ "$#" -lt 1 ]; then
    print_error "Faltan argumentos"
    echo ""
    echo "Uso: $0 <archivo.tar.gz> [nombre_version]"
    echo ""
    echo "Ejemplo:"
    echo "  $0 ~/Downloads/als_model_v1_20251208.tar.gz"
    echo "  $0 ~/Downloads/model.tar.gz model_kaggle_v1"
    exit 1
fi

TAR_FILE="$1"
VERSION_NAME="${2:-}"

# Validar que el archivo existe
if [ ! -f "$TAR_FILE" ]; then
    print_error "Archivo no encontrado: $TAR_FILE"
    exit 1
fi

# Validar que es un .tar.gz
if [[ ! "$TAR_FILE" =~ \.tar\.gz$ ]]; then
    print_error "El archivo debe ser .tar.gz"
    exit 1
fi

###############################################################################
# Configuración de rutas
###############################################################################

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.."
MODELS_DIR="$PROJECT_ROOT/movies/trained_models/als"
TEMP_DIR="/tmp/kaggle_model_import_$$"

print_step "Configuración"
echo "  Archivo: $TAR_FILE"
echo "  Destino: $MODELS_DIR"
echo ""

###############################################################################
# Crear directorio temporal
###############################################################################

print_step "Creando directorio temporal..."
mkdir -p "$TEMP_DIR"
print_success "Directorio temporal: $TEMP_DIR"

###############################################################################
# Extraer archivo
###############################################################################

print_step "Extrayendo archivo .tar.gz..."
tar -xzf "$TAR_FILE" -C "$TEMP_DIR"

# Encontrar el directorio del modelo
MODEL_DIR=$(find "$TEMP_DIR" -maxdepth 2 -type d -name "als_model*" | head -1)

if [ -z "$MODEL_DIR" ]; then
    # Buscar cualquier directorio que contenga spark_model
    MODEL_DIR=$(find "$TEMP_DIR" -type d -name "spark_model" -exec dirname {} \; | head -1)
fi

if [ -z "$MODEL_DIR" ]; then
    print_error "No se encontró el modelo en el archivo"
    rm -rf "$TEMP_DIR"
    exit 1
fi

print_success "Modelo extraído: $(basename $MODEL_DIR)"

###############################################################################
# Determinar nombre de versión
###############################################################################

if [ -z "$VERSION_NAME" ]; then
    # Extraer del nombre del archivo o usar timestamp
    BASE_NAME=$(basename "$MODEL_DIR")
    
    if [[ "$BASE_NAME" =~ als_model ]]; then
        VERSION_NAME="$BASE_NAME"
    else
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        VERSION_NAME="als_model_kaggle_${TIMESTAMP}"
    fi
fi

print_step "Nombre de versión: $VERSION_NAME"

###############################################################################
# Mover modelo al directorio final
###############################################################################

FINAL_MODEL_PATH="$MODELS_DIR/$VERSION_NAME"

print_step "Instalando modelo..."

# Crear directorio de modelos si no existe
mkdir -p "$MODELS_DIR"

# Si ya existe, hacer backup
if [ -d "$FINAL_MODEL_PATH" ]; then
    print_warning "Ya existe un modelo con ese nombre"
    BACKUP_PATH="${FINAL_MODEL_PATH}_backup_$(date +%Y%m%d_%H%M%S)"
    print_step "Creando backup en: $(basename $BACKUP_PATH)"
    mv "$FINAL_MODEL_PATH" "$BACKUP_PATH"
fi

# Mover modelo
mv "$MODEL_DIR" "$FINAL_MODEL_PATH"
print_success "Modelo instalado en: $FINAL_MODEL_PATH"

###############################################################################
# Verificar estructura del modelo
###############################################################################

print_step "Verificando estructura del modelo..."

REQUIRED_ITEMS=("spark_model" "metadata.json")
MISSING_ITEMS=()

for item in "${REQUIRED_ITEMS[@]}"; do
    if [ ! -e "$FINAL_MODEL_PATH/$item" ]; then
        MISSING_ITEMS+=("$item")
    fi
done

if [ ${#MISSING_ITEMS[@]} -eq 0 ]; then
    print_success "Estructura del modelo válida"
else
    print_warning "Faltan algunos archivos opcionales: ${MISSING_ITEMS[*]}"
    echo "  El modelo puede funcionar, pero algunos metadatos no están disponibles"
fi

###############################################################################
# Actualizar symlink model_latest
###############################################################################

print_step "Actualizando symlink model_latest..."

LATEST_LINK="$MODELS_DIR/model_latest"

# Eliminar symlink anterior si existe
if [ -L "$LATEST_LINK" ]; then
    rm "$LATEST_LINK"
fi

# Crear nuevo symlink
ln -s "$VERSION_NAME" "$LATEST_LINK"
print_success "Symlink actualizado: model_latest -> $VERSION_NAME"

###############################################################################
# Mostrar información del modelo
###############################################################################

print_step "Información del modelo:"
echo ""

# Leer metadata si existe
if [ -f "$FINAL_MODEL_PATH/metadata.json" ]; then
    if command -v jq &> /dev/null; then
        echo "Metadatos:"
        jq '.' "$FINAL_MODEL_PATH/metadata.json" | head -20
    else
        echo "Metadatos (instala 'jq' para formato mejorado):"
        cat "$FINAL_MODEL_PATH/metadata.json" | head -20
    fi
else
    print_warning "No se encontró metadata.json"
fi

echo ""

###############################################################################
# Listar todos los modelos
###############################################################################

print_step "Modelos disponibles en $MODELS_DIR:"
echo ""
ls -lh "$MODELS_DIR" | grep -E "^d|^l" | awk '{print "  " $9 " (" $5 ")"}'
echo ""

###############################################################################
# Limpiar
###############################################################################

print_step "Limpiando archivos temporales..."
rm -rf "$TEMP_DIR"
print_success "Limpieza completada"

###############################################################################
# Ejemplo de uso
###############################################################################

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_success "Modelo importado exitosamente!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Para usar el modelo en Python:"
echo ""
echo "  from pyspark.sql import SparkSession"
echo "  from movies.src.recommendation.models.als_model import ALSRecommender"
echo ""
echo "  spark = SparkSession.builder.appName('Recommendations').getOrCreate()"
echo "  recommender = ALSRecommender(spark, model_path='movies/trained_models/als/model_latest')"
echo "  recommendations = recommender.recommend_for_user(user_id=123, n=10)"
echo ""
echo "O ejecutar el ejemplo:"
echo ""
echo "  python movies/src/recommendation/example_usage.py"
echo ""
