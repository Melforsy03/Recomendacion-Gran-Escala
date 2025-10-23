from pyspark.sql import SparkSession
from pyspark.sql.functions import *
import os
import json
from datetime import datetime

print("📤 INICIANDO EXPORTACIÓN DE HDFS A JSON")

# Configurar Spark para YARN
spark = SparkSession.builder \
    .appName("ExportHDFStoJSON") \
    .master("yarn") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.executor.memory", "512m") \
    .getOrCreate()

def cargar_datos_desde_hdfs(hdfs_path):
    """
    Cargar datos procesados desde HDFS
    
    Args:
        hdfs_path: Ruta en HDFS donde están los datos
    
    Returns:
        DataFrame de Spark con los datos o None si hay error
    """
    try:
        print(f"📖 Leyendo datos desde: {hdfs_path}")
        df = spark.read.format("parquet").load(hdfs_path)
        count = df.count()
        print(f"✅ Datos cargados exitosamente: {count} registros")
        return df
    except Exception as e:
        print(f"❌ Error cargando desde HDFS: {e}")
        return None

def exportar_a_json(df, output_path, modo="completo"):
    """
    Exportar DataFrame a formato JSON
    
    Args:
        df: DataFrame de Spark
        output_path: Ruta donde guardar el JSON
        modo: 'completo' (todos los datos) o 'muestra' (solo algunos registros)
    """
    if df is None:
        print("❌ No hay datos para exportar")
        return False
    
    try:
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Determinar cantidad de registros a exportar
        if modo == "muestra":
            print("📝 Exportando muestra de 100 registros...")
            df_export = df.limit(100)
        else:
            total = df.count()
            print(f"📝 Exportando {total} registros completos...")
            df_export = df
        
        # Convertir a Pandas y luego a JSON (para archivos pequeños/medianos)
        # Si los datos son muy grandes, usar df.write.json() en su lugar
        pandas_df = df_export.toPandas()
        
        # Exportar a JSON con formato legible
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(
                pandas_df.to_dict(orient='records'),
                f,
                ensure_ascii=False,
                indent=2
            )
        
        print(f"✅ Datos exportados exitosamente a: {output_path}")
        print(f"📊 Tamaño del archivo: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")
        return True
        
    except Exception as e:
        print(f"❌ Error exportando a JSON: {e}")
        # Intentar método alternativo para archivos grandes
        try:
            print("🔄 Intentando método alternativo (Spark write)...")
            temp_path = output_path.replace('.json', '_spark_output')
            df_export.coalesce(1).write.mode('overwrite').json(temp_path)
            print(f"✅ Datos exportados a: {temp_path}")
            print("⚠️  Nota: Los datos están en formato de carpeta de Spark")
            return True
        except Exception as e2:
            print(f"❌ Error en método alternativo: {e2}")
            return False

def exportar_estadisticas(df, output_path):
    """
    Exportar estadísticas resumidas a JSON
    
    Args:
        df: DataFrame de Spark
        output_path: Ruta donde guardar las estadísticas
    """
    try:
        print("📊 Generando estadísticas...")
        
        # Calcular estadísticas
        total = df.count()
        
        stats = {
            "metadata": {
                "fecha_exportacion": datetime.now().isoformat(),
                "total_registros": total
            },
            "estadisticas_generales": {},
            "distribucion_popularidad": {},
            "distribucion_rating": {},
            "top_generos": []
        }
        
        # Estadísticas numéricas
        if "puan" in df.columns and "pop" in df.columns:
            numeric_stats = df.select("puan", "pop").describe().collect()
            stats["estadisticas_generales"] = {
                "puntuacion": {row["summary"]: {
                    "puan": float(row["puan"]) if row["puan"] else None,
                    "pop": float(row["pop"]) if row["pop"] else None
                } for row in numeric_stats}
            }
        
        # Distribución de popularidad
        if "popularity_level" in df.columns:
            pop_dist = df.groupBy("popularity_level") \
                .count() \
                .orderBy(desc("count")) \
                .collect()
            stats["distribucion_popularidad"] = {
                row["popularity_level"]: row["count"] for row in pop_dist
            }
        
        # Distribución de rating
        if "rating_category" in df.columns:
            rating_dist = df.groupBy("rating_category") \
                .count() \
                .orderBy(desc("count")) \
                .collect()
            stats["distribucion_rating"] = {
                row["rating_category"]: row["count"] for row in rating_dist
            }
        
        # Top géneros
        if "genres" in df.columns:
            top_genres = df.select(explode(col("genres")).alias("genre")) \
                .groupBy("genre") \
                .count() \
                .orderBy(desc("count")) \
                .limit(10) \
                .collect()
            stats["top_generos"] = [
                {"genero": row["genre"], "cantidad": row["count"]} 
                for row in top_genres
            ]
        
        # Guardar estadísticas
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Estadísticas exportadas a: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error exportando estadísticas: {e}")
        return False

def main():
    """Función principal"""
    print("=" * 60)
    print("          EXPORTACIÓN DE HDFS A JSON")
    print("=" * 60)
    
    # Configuración
    HDFS_PATH = "hdfs://localhost:9000/user/movies/processed/cleaned_movies"
    OUTPUT_DIR = "outputs/exported_data"
    
    # Timestamp para archivos únicos
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Rutas de salida
    json_completo = f"{OUTPUT_DIR}/movies_completo_{timestamp}.json"
    json_muestra = f"{OUTPUT_DIR}/movies_muestra_{timestamp}.json"
    json_stats = f"{OUTPUT_DIR}/movies_stats_{timestamp}.json"
    
    try:
        # 1. Cargar datos desde HDFS
        print("\n" + "="*60)
        print("PASO 1: CARGAR DATOS DESDE HDFS")
        print("="*60)
        movies_df = cargar_datos_desde_hdfs(HDFS_PATH)
        
        if movies_df is None:
            print("❌ No se pudieron cargar los datos. Abortando...")
            return
        
        # Mostrar esquema y muestra
        print("\n📋 Esquema de los datos:")
        movies_df.printSchema()
        print("\n📝 Muestra de datos:")
        movies_df.show(5, truncate=False)
        
        # 2. Exportar muestra
        print("\n" + "="*60)
        print("PASO 2: EXPORTAR MUESTRA (100 registros)")
        print("="*60)
        exportar_a_json(movies_df, json_muestra, modo="muestra")
        
        # 3. Exportar estadísticas
        print("\n" + "="*60)
        print("PASO 3: EXPORTAR ESTADÍSTICAS")
        print("="*60)
        exportar_estadisticas(movies_df, json_stats)
        
        # 4. Preguntar por exportación completa
        print("\n" + "="*60)
        print("PASO 4: EXPORTACIÓN COMPLETA")
        print("="*60)
        total_registros = movies_df.count()
        print(f"⚠️  ADVERTENCIA: Se exportarán {total_registros} registros")
        print(f"   Esto puede generar un archivo grande.")
        print(f"   Ruta: {json_completo}")
        
        # Exportar automáticamente (puedes comentar esta línea si prefieres confirmación manual)
        exportar_a_json(movies_df, json_completo, modo="completo")
        
        # Resumen final
        print("\n" + "="*60)
        print("✅ EXPORTACIÓN COMPLETADA")
        print("="*60)
        print(f"📁 Archivos generados:")
        print(f"   • Muestra: {json_muestra}")
        print(f"   • Estadísticas: {json_stats}")
        print(f"   • Completo: {json_completo}")
        
    except Exception as e:
        print(f"\n❌ ERROR EN EXPORTACIÓN: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🔌 Cerrando Spark...")
        spark.stop()
        print("✅ Spark cerrado correctamente")

if __name__ == "__main__":
    main()
