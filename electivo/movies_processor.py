from pyspark.sql import SparkSession
from pyspark.sql.functions import *

print("🔄 MOVIES PROCESSOR CON YARN")

# Configurar Spark para YARN
spark = SparkSession.builder \
    .appName("MoviesProcessorYARN") \
    .master("yarn") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.executor.memory", "512m") \
    .getOrCreate()

def main():
    print("=" * 50)
    print("       MOVIES PROCESSOR - YARN")
    print("=" * 50)
    
    # Leer desde HDFS
    print("\n1. 📖 LEYENDO DESDE HDFS...")
    try:
        movies_df = spark.read \
            .format("parquet") \
            .load("hdfs://localhost:9000/user/movies/raw/movies_dataset")
        
        print(f"✅ {movies_df.count()} películas leídas desde HDFS")
        movies_df.show(5)
        
    except Exception as e:
        print(f"❌ Error leyendo de HDFS: {e}")
        return
    
    # Procesar datos
    print("\n2. 🧹 PROCESANDO DATOS CON SPARK EN YARN...")
    processed_df = movies_df \
        .filter(col("ID").isNotNull()) \
        .filter(col("name").isNotNull()) \
        .filter(col("puan").between(0, 10)) \
        .filter(col("pop").between(0, 100)) \
        .withColumn("genres", 
                   when(col("genre_2").isNull(), array(col("genre_1")))
                   .otherwise(array(col("genre_1"), col("genre_2")))) \
        .withColumn("popularity_level",
                   when(col("pop") >= 90, "Alta")
                   .when(col("pop") >= 70, "Media") 
                   .otherwise("Baja")) \
        .withColumn("rating_category",
                   when(col("puan") >= 9.0, "Excelente")
                   .when(col("puan") >= 8.0, "Muy Bueno")
                   .when(col("puan") >= 7.0, "Bueno")
                   .otherwise("Regular")) \
        .drop("genre_1", "genre_2")
    
    print("✅ Datos procesados:")
    processed_df.show(5)
    
    # Guardar procesados en HDFS
    print("\n3. 💾 GUARDANDO EN HDFS...")
    try:
        processed_df.write \
            .mode("overwrite") \
            .format("parquet") \
            .save("hdfs://localhost:9000/user/movies/processed/cleaned_movies")
        
        print("✅ Datos procesados guardados en HDFS")
        
    except Exception as e:
        print(f"❌ Error guardando en HDFS: {e}")
        return
    
    print("\n🎉 PROCESAMIENTO CON YARN COMPLETADO!")

if __name__ == "__main__":
    main()
    spark.stop()