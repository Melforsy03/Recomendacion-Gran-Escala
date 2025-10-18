from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import json
import subprocess

print("🎬 MOVIES PRODUCER CON YARN, SPARK Y HDFS")

# Configurar Spark para YARN
spark = SparkSession.builder \
    .appName("MoviesProducerYARN") \
    .master("yarn") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.executor.memory", "512m") \
    .config("spark.driver.memory", "512m") \
    .getOrCreate()

# Esquema de datos
movies_schema = StructType([
    StructField("ID", IntegerType(), True),
    StructField("name", StringType(), True),
    StructField("puan", DoubleType(), True),
    StructField("genre_1", StringType(), True),
    StructField("genre_2", StringType(), True),
    StructField("pop", IntegerType(), True),
    StructField("description", StringType(), True)
])

def verificar_servicios():
    """Verificar que HDFS y YARN estén funcionando"""
    try:
        # Verificar HDFS
        result = subprocess.run(["hdfs", "dfs", "-ls", "/"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print("❌ HDFS no está disponible")
            return False
        
        # Verificar YARN
        result = subprocess.run(["yarn", "node", "-list"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print("❌ YARN no está disponible")
            return False
            
        print("✅ HDFS y YARN funcionando correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error verificando servicios: {e}")
        return False

def main():
    print("=" * 60)
    print("       MOVIES PRODUCER - YARN & HDFS")
    print("=" * 60)
    
    # Verificar servicios
    if not verificar_servicios():
        print("❌ Los servicios no están disponibles. Ejecuta start_services.sh primero")
        return
    
    # Cargar datos desde JSON
    print("\n1. 📥 CARGANDO DATOS DESDE JSON...")
    try:
        with open('movies.json', 'r', encoding='utf-8') as f:
            movies_data = json.load(f)
        
        movies_df = spark.createDataFrame(movies_data, schema=movies_schema)
        print(f"✅ {movies_df.count()} películas cargadas")
        movies_df.show(5)
        
    except Exception as e:
        print(f"❌ Error cargando datos: {e}")
        return
    
    # Escribir a HDFS usando YARN
    print("\n2. 📤 ESCRIBIENDO A HDFS CON YARN...")
    try:
        # Escribir en formato Parquet a HDFS
        movies_df.write \
            .mode("overwrite") \
            .format("parquet") \
            .save("hdfs://localhost:9000/user/movies/raw/movies_dataset")
        
        print("✅ Datos escritos en HDFS (Parquet)")
        
        # También escribir en JSON
        movies_df.write \
            .mode("overwrite") \
            .format("json") \
            .save("hdfs://localhost:9000/user/movies/raw/movies_json")
        
        print("✅ Datos escritos en HDFS (JSON)")
        
    except Exception as e:
        print(f"❌ Error escribiendo a HDFS: {e}")
        return
    
    # Verificar datos en HDFS
    print("\n3. 🔍 VERIFICANDO DATOS EN HDFS...")
    try:
        # Leer desde HDFS para verificación
        hdfs_df = spark.read \
            .format("parquet") \
            .load("hdfs://localhost:9000/user/movies/raw/movies_dataset")
        
        print(f"✅ Verificación exitosa: {hdfs_df.count()} registros en HDFS")
        print("📊 Muestra de datos en HDFS:")
        hdfs_df.show(3)
        
    except Exception as e:
        print(f"❌ Error verificando HDFS: {e}")
        return
    
    print("\n🎉 PRODUCER COMPLETADO CON YARN Y HDFS!")
    print("📍 HDFS: hdfs://localhost:9000/user/movies/raw/")
    print("📍 YARN UI: http://localhost:8088")

if __name__ == "__main__":
    main()
    spark.stop()