from pyspark.sql import SparkSession
from pyspark.sql.functions import *
import os
import subprocess

# SILENCIAR TODOS LOS LOGS DE SPARK
os.environ['PYSPARK_PYTHON'] = 'python3'
os.environ['PYSPARK_DRIVER_PYTHON'] = 'python3'
os.environ['SPARK_LOCAL_IP'] = '127.0.0.1'

# Configurar Spark para ser SILENCIOSO
spark = SparkSession.builder \
    .appName("MoviesAnalysis") \
    .master("local[*]") \
    .config("spark.ui.enabled", "false") \
    .config("spark.driver.bindAddress", "127.0.0.1") \
    .config("spark.driver.host", "127.0.0.1") \
    .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse") \
    .getOrCreate()

# SILENCIAR LOGS
spark.sparkContext.setLogLevel("ERROR")
sc = spark.sparkContext
sc.setLogLevel("ERROR")

def main():
    print("=" * 50)
    print("          MOVIES ANALYSIS - MODO LOCAL")
    print("=" * 50)
    
# Configurar Spark para YARN
spark = SparkSession.builder \
    .appName("MoviesAnalysisYARN") \
    .master("yarn") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.executor.memory", "512m") \
    .getOrCreate()

def cargar_datos_procesados():
    """Cargar datos procesados desde HDFS"""
    try:
        # Intentar desde HDFS
        movies_df = spark.read \
            .format("parquet") \
            .load("hdfs://localhost:9000/user/movies/processed/cleaned_movies")
        print("✅ Datos cargados desde HDFS")
        return movies_df
    except Exception as e:
        print(f"❌ Error cargando desde HDFS: {e}")
        
        # Intentar localmente como fallback
        try:
            movies_df = spark.read \
                .format("parquet") \
                .load("file:///" + os.path.abspath("data/processed/cleaned_movies"))
            print("✅ Datos cargados localmente")
            return movies_df
        except Exception as e2:
            print(f"❌ Error cargando localmente: {e2}")
            return None

def ejecutar_analisis():
    """Ejecutar análisis"""
    movies_df = cargar_datos_procesados()
    if movies_df is None:
        print("❌ No se pudieron cargar los datos para análisis")
        return
    
    print(f"📖 Datos cargados: {movies_df.count()} películas")
    
    print("\n" + "="*60)
    print("              ANÁLISIS DE PELÍCULAS - YARN")
    print("="*60)
    
    # 1. Top películas
    print("\n1. 🏆 TOP 5 PELÍCULAS MEJOR PUNTUADAS:")
    top_movies = movies_df.orderBy(desc("puan")) \
        .select("name", "puan", "popularity_level", "rating_category") \
        .limit(5)
    top_movies.show(truncate=False)
    
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
    
    genre_stats.show(truncate=False)
    
    # 3. Distribuciones
    print("\n3. 📈 DISTRIBUCIÓN DE POPULARIDAD:")
    pop_dist = movies_df.groupBy("popularity_level") \
        .agg(count("*").alias("cantidad")) \
        .orderBy(desc("cantidad"))
    pop_dist.show()
    
    print("\n4. ⭐ DISTRIBUCIÓN DE RATING:")
    rating_dist = movies_df.groupBy("rating_category") \
        .agg(count("*").alias("cantidad")) \
        .orderBy(desc("cantidad"))
    rating_dist.show()
    
    print("\n5. 📊 ESTADÍSTICAS GENERALES:")
    stats = movies_df.select("puan", "pop").describe()
    stats.show()
    
    # 6. Resumen ejecutivo
    print("\n6. 📋 RESUMEN EJECUTIVO:")
    total_movies = movies_df.count()
    avg_rating = movies_df.select(avg("puan")).collect()[0][0]
    avg_popularity = movies_df.select(avg("pop")).collect()[0][0]
    
    print(f"   • Total de películas: {total_movies}")
    print(f"   • Puntuación promedio: {avg_rating:.2f}")
    print(f"   • Popularidad promedio: {avg_popularity:.2f}")

def main():
    """Función principal"""
    print("=" * 50)
    print("          MOVIES ANALYSIS - YARN")
    print("=" * 50)
    
    try:
        ejecutar_analisis()
        print("\n🎉 ANÁLISIS COMPLETADO CON YARN!")
    except Exception as e:
        print(f"\n❌ ERROR EN ANÁLISIS: {e}")
    finally:
        spark.stop()

if __name__ == "__main__":
    main()