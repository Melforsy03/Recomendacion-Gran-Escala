from pyspark.sql import SparkSession
from pyspark.sql.functions import *
import os

def setup_spark():
    """Configura Spark Session para HDFS"""
    return SparkSession.builder \
        .appName("MovieBatchAnalysis") \
        .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000") \
        .config("spark.sql.adaptive.enabled", "true") \
        .getOrCreate()

def analyze_movie_data():
    """Análisis batch de datos de películas"""
    print("🎬 Iniciando análisis batch...")
    
    spark = setup_spark()
    
    try:
        # Leer datos de HDFS
        print("📖 Leyendo datos de HDFS...")
        df = spark.read.json("hdfs://namenode:9000/data/*.json")
        
        if df.count() == 0:
            print("❌ No hay datos en HDFS")
            return
        
        print(f"📊 Total de registros: {df.count()}")
        
        # Análisis básico
        print("\n📈 ANÁLISIS BATCH:")
        print("1. Conteo por acción:")
        df.groupBy("action").count().show()
        
        print("2. Top 10 películas más interactivas:")
        df.groupBy("movie_id").count() \
          .orderBy(desc("count")) \
          .limit(10) \
          .show()
        
        print("3. Distribución temporal:")
        df.withColumn("hour", hour(from_unixtime("timestamp"))) \
          .groupBy("hour").count() \
          .orderBy("hour") \
          .show()
        
        # Guardar resultados en HDFS
        results = df.groupBy("movie_id").agg(
            count("*").alias("total_interactions"),
            count(when(col("action") == "view", True)).alias("views"),
            count(when(col("action") == "rating", True)).alias("ratings")
        )
        
        results.write.mode("overwrite").json("hdfs://namenode:9000/results/movie_analytics")
        print("✅ Resultados guardados en HDFS: /results/movie_analytics")
        
        # Mostrar estadísticas finales
        print(f"\n🎯 ESTADÍSTICAS FINALES:")
        print(f"   - Total interacciones: {df.count()}")
        print(f"   - Películas únicas: {df.select('movie_id').distinct().count()}")
        print(f"   - Acciones únicas: {[row[0] for row in df.select('action').distinct().collect()]}")
        
    except Exception as e:
        print(f"❌ Error en análisis batch: {e}")
    finally:
        spark.stop()

if __name__ == "__main__":
    analyze_movie_data()