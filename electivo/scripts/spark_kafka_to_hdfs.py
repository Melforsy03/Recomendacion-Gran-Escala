import os
from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import from_json, col

# Importante para que funcione sin spark-submit
os.environ["PYSPARK_SUBMIT_ARGS"] = (
    "--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 pyspark-shell"
)

spark = (SparkSession.builder
    .appName("MoviesKafkaToHDFS")
    .master("yarn")
    .config("spark.sql.streaming.schemaInference","true")
    .getOrCreate())

spark.sparkContext.setLogLevel("WARN")

schema = StructType([
    StructField("ID", IntegerType(), True),
    StructField("name", StringType(), True),
    StructField("puan", DoubleType(), True),
    StructField("genre_1", StringType(), True),
    StructField("genre_2", StringType(), True),
    StructField("pop", IntegerType(), True),
    StructField("description", StringType(), True),
])

df = (spark.readStream
      .format("kafka")
      .option("kafka.bootstrap.servers","172.17.0.1:9092")
      .option("subscribe","movies")
      .option("startingOffsets","latest")
      .load())

movies = (df
    .selectExpr("CAST(value AS STRING) AS json")
    .select(from_json(col("json"), schema).alias("data"))
    .select("data.*"))


output = "hdfs://localhost:9000/user/movies/bronze/movies"
chkpt = "hdfs://localhost:9000/user/movies/checkpoints/movies_kafka"

query = (movies.writeStream
         .format("parquet")
         .option("path", output)
         .option("checkpointLocation", chkpt)
         .outputMode("append")
         .trigger(processingTime="5 seconds")
         .start())

query.awaitTermination()
