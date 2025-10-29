# export_bronze_to_json_fixed.py
from pyspark.sql import SparkSession
from pyspark.sql.types import *
import json
import os
from datetime import datetime

# DEFINIR EL ESQUEMA EXPLÍCITAMENTE (igual que en tu pipeline)
bronze_schema = StructType([
    StructField("movieId", IntegerType(), True),
    StructField("title", StringType(), True),
    StructField("genres", ArrayType(StringType()), True),
    StructField("imdbId", IntegerType(), True),
    StructField("tmdbId", IntegerType(), True),
    StructField("avg_rating", FloatType(), True),
    StructField("rating_count", IntegerType(), True),
    StructField("top_tags", ArrayType(StringType()), True),
    StructField("genome_relevance", ArrayType(
        StructType([
            StructField("tag", StringType(), True),
            StructField("relevance", FloatType(), True)
        ])
    ), True)
])

def export_bronze_to_json():
    spark = SparkSession.builder \
        .appName("Export-BRONZE-to-JSON") \
        .master("local[*]") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    print("📖 Leyendo datos BRONZE desde HDFS...")
    
    try:
        # Leer datos BRONZE CON ESQUEMA EXPLÍCITO
        bronze_path = "hdfs://localhost:9000/user/movies/bronze/movies"
        bronze_df = spark.read.schema(bronze_schema).parquet(bronze_path)
        
        record_count = bronze_df.count()
        print(f"📊 Total de registros: {record_count}")
        
        if record_count == 0:
            print("⚠️ No hay datos para exportar")
            spark.stop()
            return
        
        # Crear directorio de exportación
        export_dir = "/app/exports"
        os.makedirs(export_dir, exist_ok=True)
        
        # Convertir a Pandas y guardar como JSON
        pandas_df = bronze_df.toPandas()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{export_dir}/movies_data_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(
                pandas_df.to_dict('records'), 
                f, 
                indent=2, 
                ensure_ascii=False,
                default=str
            )
        
        print(f"✅ Exportación completada!")
        print(f"📁 Archivo: {output_file}")
        print(f"📊 Registros: {record_count}")
        
        # Mostrar preview
        print("\n🔍 Primeras 3 películas:")
        bronze_df.select("movieId", "title", "avg_rating", "genres").show(5, truncate=False)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        spark.stop()

if __name__ == "__main__":
    export_bronze_to_json()