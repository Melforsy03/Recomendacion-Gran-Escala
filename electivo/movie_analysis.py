from pyspark.sql import SparkSession
from pyspark.sql.functions import *
import os
import subprocess

print("📊 INICIANDO MOVIES ANALYSIS (MODO LOCAL)")

# Configurar Spark
spark = SparkSession.builder \
    .appName("MoviesAnalysis") \
    .master("local[*]") \
    .getOrCreate()

def cargar_datos_procesados():
    """Cargar datos procesados"""
    # Intentar desde HDFS primero, luego local
    try:
        movies_df = spark.read \
            .format("parquet") \
            .load("hdfs://localhost:9000/user/movies/processed/cleaned_movies")
        print("✅ Datos cargados desde HDFS")
        return movies_df
    except:
        try:
            movies_df = spark.read \
                .format("parquet") \
                .load("file:///" + os.path.abspath("data/processed/cleaned_movies"))
            print("✅ Datos cargados localmente")
            return movies_df
        except Exception as e:
            print(f"❌ Error cargando datos: {e}")
            return None

def ejecutar_analisis():
    """Ejecutar análisis"""
    movies_df = cargar_datos_procesados()
    if movies_df is None:
        return
    
    print(f"📖 Datos cargados: {movies_df.count()} películas")
    
    print("\n" + "="*60)
    print("              ANÁLISIS DE PELÍCULAS")
    print("="*60)
    
    # 1. Top películas
    print("\n1. 🏆 TOP 5 PELÍCULAS MEJOR PUNTUADAS:")
    movies_df.orderBy(desc("puan")) \
        .select("name", "puan", "popularity_level", "rating_category") \
        .show(5)
    
    # 2. Análisis por género
    print("\n2. 🎭 ESTADÍSTICAS POR GÉNERO:")
    genre_stats = movies_df.select(explode(col("genres")).alias("genre"), "puan", "pop") \
        .groupBy("genre") \
        .agg(
            count("*").alias("cantidad_peliculas"),
            round(avg("puan"), 2).alias("puntuacion_promedio"),
            round(avg("pop"), 2).alias("popularidad_promedio")
        ) \
        .orderBy(desc("cantidad_peliculas"))
    
    genre_stats.show()
    
    # 3. Distribuciones
    print("\n3. 📈 DISTRIBUCIÓN DE POPULARIDAD:")
    movies_df.groupBy("popularity_level") \
        .agg(count("*").alias("cantidad")) \
        .orderBy(desc("cantidad")) \
        .show()
    
    print("\n4. ⭐ DISTRIBUCIÓN DE RATING:")
    movies_df.groupBy("rating_category") \
        .agg(count("*").alias("cantidad")) \
        .orderBy(desc("cantidad")) \
        .show()
    
    print("\n5. 📊 ESTADÍSTICAS GENERALES:")
    movies_df.select("puan", "pop").describe().show()

def main():
    """Función principal"""
    print("=" * 50)
    print("          MOVIES ANALYSIS - MODO LOCAL")
    print("=" * 50)
    
    ejecutar_analisis()
    print("\n🎉 ANÁLISIS COMPLETADO!")

if __name__ == "__main__":
    main()
    spark.stop()