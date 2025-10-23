"""
Spark Structured Streaming para computar métricas en tiempo real del sistema
de recomendaciones leyendo eventos desde Kafka (topic: 'events') y publicando
métricas agregadas en otro topic (topic: 'metrics').

Métricas:
- acceptance_rate: aceptaciones / ítems recomendados (ventana 1m slide 10s)
- top_products: top-N por número de veces sugeridos (ventana 1m)
- active_users_per_min: usuarios únicos por minuto
- engagement: eventos por usuario (promedio) en ventana
- precision: alias de acceptance_rate (proxy sin ground truth explícito)

Ejecución dentro del contenedor spark-master (recomendado):
  spark-submit --master spark://spark-master:7077 \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1 \
    /opt/spark/work-dir/movies/src/streaming/metrics_streaming.py
"""
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, explode, size, expr, window, approx_count_distinct, count, avg,
    to_json, struct, lit, collect_list, struct as fstruct, sort_array, transform
)
from pyspark.sql.types import (
    StructType, StructField, StringType, ArrayType, TimestampType, BooleanType
)


def build_spark():
    spark = (
        SparkSession.builder
        .appName("MetricsStreaming")
        .master("spark://spark-master:7077")
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1")
        .config("spark.sql.shuffle.partitions", "4")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


def main():
    spark = build_spark()

    events_schema = StructType([
        StructField("type", StringType(), True),
        StructField("ts", TimestampType(), True),
        StructField("user_id", StringType(), True),
        StructField("items", ArrayType(StringType()), True),
        StructField("item_id", StringType(), True),
        StructField("action", StringType(), True),
        StructField("recommended", BooleanType(), True),
    ])

    kafka_bootstrap = "kafka:9092"
    events_topic = "events"
    metrics_topic = "metrics"

    # Lectura desde Kafka
    raw = (
        spark.readStream
        .format("kafka")
        .option("kafka.bootstrap.servers", kafka_bootstrap)
        .option("subscribe", events_topic)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .load()
    )

    events = raw.select(from_json(col("value").cast("string"), events_schema).alias("e")).select("e.*")

    # Ventanas base
    recommendations = (
        events.filter(col("type") == "recommendation")
        .withWatermark("ts", "2 minutes")
    )

    interactions = (
        events.filter((col("type") == "interaction") & col("recommended"))
        .withWatermark("ts", "2 minutes")
    )

    # Total ítems recomendados por ventana: contamos longitud del array items
    rec_items = recommendations.select(
        window(col("ts"), "1 minute", "10 seconds").alias("w"),
        size(col("items")).alias("k")
    )
    rec_items_agg = rec_items.groupBy("w").agg(expr("sum(k) as rec_items"))

    # Aceptaciones: interactions con action='accept'
    accepts = interactions.filter(col("action") == "accept").select(
        window(col("ts"), "1 minute", "10 seconds").alias("w"),
        lit(1).alias("one")
    )
    accepts_agg = accepts.groupBy("w").agg(expr("sum(one) as accepts"))

    # Métrica acceptance_rate y precision (proxy)
    acc = rec_items_agg.join(accepts_agg, on=["w"], how="left").fillna({"accepts": 0})
    acc = acc.select(
        col("w.start").alias("window_start"),
        col("w.end").alias("window_end"),
        (col("accepts") / expr("case when rec_items=0 then 1 else rec_items end")).alias("acceptance_rate"),
        col("accepts").alias("accepts"),
        col("rec_items")
    )

    # Para sinks Kafka, usaremos modo append; aseguramos watermarks en todas las ramas
    events_wm = events.withWatermark("ts", "2 minutes")

    # Usuarios activos por minuto
    active_users = events_wm.select(
        window(col("ts"), "1 minute", "10 seconds").alias("w"),
        col("user_id")
    ).groupBy("w").agg(approx_count_distinct("user_id").alias("active_users"))
    active_users = active_users.select(
        col("w.start").alias("window_start"),
        col("w.end").alias("window_end"),
        col("active_users")
    )

    # Engagement: eventos por usuario (promedio) en la ventana
    events_per_user = events_wm.select(
        window(col("ts"), "1 minute", "10 seconds").alias("w"),
        col("user_id")
    ).groupBy("w", "user_id").agg(count(lit(1)).alias("evs"))
    engagement = events_per_user.groupBy("w").agg(avg("evs").alias("avg_events_per_user"))
    engagement = engagement.select(
        col("w.start").alias("window_start"),
        col("w.end").alias("window_end"),
        col("avg_events_per_user")
    )

    # Top productos sugeridos: explotar arrays de recomendaciones
    rec_exploded = recommendations.select(
        window(col("ts"), "1 minute", "30 seconds").alias("w"),
        explode(col("items")).alias("item_id")
    )
    top_products = rec_exploded.groupBy("w", "item_id").agg(count(lit(1)).alias("suggested"))
    # Top-N por ventana sin window functions (no soportadas en streaming):
    # 1) Agrupamos por ventana y recolectamos pares (suggested, item_id)
    pairs = top_products.groupBy("w").agg(
        collect_list(fstruct(col("suggested"), col("item_id"))).alias("pairs")
    )
    # 2) Ordenamos desc por 'suggested' y nos quedamos con los 10 primeros
    pairs_sorted = pairs.select("w", sort_array(col("pairs"), asc=False).alias("pairs"))
    top10 = pairs_sorted.select("w", expr("slice(pairs, 1, 10)").alias("pairs"))
    # 3) Reconstruimos como lista de structs {item_id, suggested}
    top_compact = top10.select(
        col("w.start").alias("window_start"),
        col("w.end").alias("window_end"),
        transform(col("pairs"), lambda x: fstruct(x["item_id"].alias("item_id"), x["suggested"].alias("suggested"))).alias("top")
    )

    # Salidas a Kafka: empaquetamos como {metric, window_start, window_end, value}
    def to_kafka_stream(df, metric_name):
        out = df.select(
            lit(metric_name).alias("key_str"),
            to_json(struct(*df.columns)).alias("value_str")
        )
        # Kafka sink soporta modo 'append'. Para joins streaming-streaming es obligatorio 'append'.
        output_mode = "append"
        return (
            out.selectExpr("CAST(key_str AS STRING) AS key", "CAST(value_str AS STRING) AS value")
            .writeStream
            .format("kafka")
            .option("kafka.bootstrap.servers", kafka_bootstrap)
            .option("topic", metrics_topic)
            .option("checkpointLocation", f"/opt/spark/data/checkpoints/{metric_name}")
            .outputMode(output_mode)
            .start()
        )

    q1 = to_kafka_stream(acc, "acceptance_rate")
    # También publicamos precision como el mismo valor (proxy)
    precision = acc.select("window_start", "window_end", col("acceptance_rate").alias("precision"))
    q2 = to_kafka_stream(precision, "precision")
    q3 = to_kafka_stream(active_users, "active_users")
    q4 = to_kafka_stream(engagement, "engagement")
    q5 = to_kafka_stream(top_compact, "top_products")

    # Log a consola para debug
    console_q = acc.writeStream.outputMode("append").format("console").option("truncate", False).start()

    print("Streaming de métricas iniciado. Esperando eventos…")
    q1.awaitTermination()
    # Por diseño, si q1 termina, terminan el resto
    console_q.stop()


if __name__ == "__main__":
    main()
