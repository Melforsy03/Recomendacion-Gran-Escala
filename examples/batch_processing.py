"""
Ejemplo de procesamiento de datos en batch con Spark
Lee datos desde HDFS, procesa y guarda resultados
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, avg, desc

def main():
    # Crear SparkSession
    spark = SparkSession.builder \
        .appName("BatchProcessingExample") \
        .master("spark://spark-master:7077") \
        .config("spark.executor.memory", "1g") \
        .config("spark.executor.cores", "1") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    print("=" * 50)
    print("Ejemplo de Procesamiento Batch con Spark")
    print("=" * 50)
    
    # Crear datos de ejemplo
    data = [
        ("user1", "item1", 5.0),
        ("user1", "item2", 4.0),
        ("user2", "item1", 3.0),
        ("user2", "item3", 5.0),
        ("user3", "item2", 4.5),
        ("user3", "item3", 2.0),
        ("user4", "item1", 5.0),
        ("user4", "item4", 3.5),
    ]
    
    # Crear DataFrame
    df = spark.createDataFrame(data, ["user_id", "item_id", "rating"])
    
    print("\nDatos originales:")
    df.show()
    
    # Análisis 1: Rating promedio por item
    print("\nRating promedio por item:")
    avg_ratings = df.groupBy("item_id") \
        .agg(
            avg("rating").alias("avg_rating"),
            count("*").alias("num_ratings")
        ) \
        .orderBy(desc("avg_rating"))
    
    avg_ratings.show()
    
    # Análisis 2: Items más populares
    print("\nItems más populares (por número de ratings):")
    popular_items = df.groupBy("item_id") \
        .agg(count("*").alias("popularity")) \
        .orderBy(desc("popularity"))
    
    popular_items.show()
    
    # Análisis 3: Actividad de usuarios
    print("\nActividad de usuarios:")
    user_activity = df.groupBy("user_id") \
        .agg(
            count("*").alias("num_ratings"),
            avg("rating").alias("avg_rating")
        ) \
        .orderBy(desc("num_ratings"))
    
    user_activity.show()
    
    # Guardar resultados en HDFS (descomenta para usar)
    # avg_ratings.write.mode("overwrite").parquet("hdfs://namenode:9000/results/avg_ratings")
    # popular_items.write.mode("overwrite").parquet("hdfs://namenode:9000/results/popular_items")
    
    print("\n✓ Procesamiento completado!")
    
    spark.stop()

if __name__ == "__main__":
    main()
