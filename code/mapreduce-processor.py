# mapreduce_processor.py
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
import os
from datetime import datetime

def run_mapreduce_yarn_job():
    """Ejecuta un trabajo MapReduce usando YARN"""
    print("🔄 Iniciando trabajo MapReduce con YARN...")
    
    # Configurar Spark para usar YARN
    spark = SparkSession.builder \
        .appName("MovieRecommendationMapReduce") \
        .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000") \
        .config("spark.master", "yarn") \
        .config("spark.submit.deployMode", "client") \
        .config("spark.hadoop.yarn.resourcemanager.address", "resourcemanager:8088") \
        .config("spark.executor.instances", "2") \
        .config("spark.executor.cores", "1") \
        .config("spark.executor.memory", "1g") \
        .config("spark.sql.adaptive.enabled", "true") \
        .getOrCreate()
    
    try:
        # Leer datos de HDFS
        print("📖 Leyendo datos de HDFS...")
        df = spark.read.json("hdfs://namenode:9000/data/*.json")
        
        if df.count() == 0:
            print("❌ No hay datos en HDFS para procesar")
            return
        
        print(f"📊 Total de registros a procesar: {df.count()}")
        
        # ========== TRABAJO 1: ANÁLISIS DE POPULARIDAD (MapReduce) ==========
        print("\n🎬 EJECUTANDO MAPREDUCE - Análisis de Popularidad...")
        
        # MAP: Contar interacciones por película
        movie_popularity = df.rdd \
            .map(lambda row: (row.movie_id, 1)) \
            .reduceByKey(lambda a, b: a + b) \
            .map(lambda x: (x[1], x[0])) \
            .sortByKey(False) \
            .map(lambda x: (x[1], x[0]))
        
        top_movies = movie_popularity.take(10)
        
        print("\n🏆 TOP 10 PELÍCULAS MÁS POPULARES:")
        for movie_id, count in top_movies:
            print(f"   🎥 Película {movie_id}: {count} interacciones")
        
        # ========== TRABAJO 2: ANÁLISIS DE USUARIOS (MapReduce) ==========
        print("\n👤 EJECUTANDO MAPREDUCE - Análisis de Usuarios...")
        
        # MAP: Contar actividades por usuario
        user_activity = df.rdd \
            .map(lambda row: (row.user_id, 1)) \
            .reduceByKey(lambda a, b: a + b) \
            .map(lambda x: (x[1], x[0])) \
            .sortByKey(False) \
            .map(lambda x: (x[1], x[0]))
        
        top_users = user_activity.take(5)
        
        print("\n👑 TOP 5 USUARIOS MÁS ACTIVOS:")
        for user_id, count in top_users:
            print(f"   👤 Usuario {user_id}: {count} actividades")
        
        # ========== TRABAJO 3: ANÁLISIS DE INTERACCIONES (MapReduce) ==========
        print("\n📊 EJECUTANDO MAPREDUCE - Análisis de Interacciones...")
        
        # MAP: Contar por tipo de interacción
        interaction_analysis = df.rdd \
            .map(lambda row: (row.interaction_type, 1)) \
            .reduceByKey(lambda a, b: a + b) \
            .collect()
        
        print("\n📈 DISTRIBUCIÓN DE INTERACCIONES:")
        for interaction_type, count in interaction_analysis:
            print(f"   📝 {interaction_type}: {count}")
        
        # ========== GUARDAR RESULTADOS EN HDFS ==========
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Guardar popularidad de películas
        popularity_rdd = spark.sparkContext.parallelize(top_movies)
        popularity_df = popularity_rdd.toDF(["movie_id", "interaction_count"])
        popularity_path = f"hdfs://namenode:9000/results/mapreduce/popularity_{timestamp}"
        popularity_df.write.mode("overwrite").json(popularity_path)
        
        # Guardar análisis de usuarios
        users_rdd = spark.sparkContext.parallelize(top_users)
        users_df = users_rdd.toDF(["user_id", "activity_count"])
        users_path = f"hdfs://namenode:9000/results/mapreduce/users_{timestamp}"
        users_df.write.mode("overwrite").json(users_path)
        
        # Guardar análisis de interacciones
        interactions_rdd = spark.sparkContext.parallelize(interaction_analysis)
        interactions_df = interactions_rdd.toDF(["interaction_type", "count"])
        interactions_path = f"hdfs://namenode:9000/results/mapreduce/interactions_{timestamp}"
        interactions_df.write.mode("overwrite").json(interactions_path)
        
        print(f"\n✅ RESULTADOS GUARDADOS EN HDFS:")
        print(f"   📁 Popularidad: {popularity_path}")
        print(f"   📁 Usuarios: {users_path}")
        print(f"   📁 Interacciones: {interactions_path}")
        
        # ========== ESTADÍSTICAS FINALES ==========
        print(f"\n🎯 ESTADÍSTICAS DEL TRABAJO MAPREDUCE:")
        print(f"   • Total registros procesados: {df.count()}")
        print(f"   • Películas únicas: {df.select('movie_id').distinct().count()}")
        print(f"   • Usuarios únicos: {df.select('user_id').distinct().count()}")
        print(f"   • Tipos de interacción: {len(interaction_analysis)}")
        print(f"   • Timestamp: {timestamp}")
        
        print("\n🎉 TRABAJO MAPREDUCE COMPLETADO EXITOSAMENTE CON YARN!")
        
    except Exception as e:
        print(f"❌ Error en trabajo MapReduce: {e}")
        import traceback
        traceback.print_exc()
    finally:
        spark.stop()

if __name__ == "__main__":
    run_mapreduce_yarn_job()