#!/usr/bin/env python3
"""
Script de verificación de integridad de datos CSV en HDFS
Cuenta líneas y muestra primeras filas de cada archivo
"""
from pyspark.sql import SparkSession
import sys

def verify_csv_integrity():
    """Verificar integridad de archivos CSV en HDFS"""
    
    spark = SparkSession.builder \
        .appName("VerifyMovieLensCSV") \
        .master("spark://spark-master:7077") \
        .config("spark.sql.shuffle.partitions", "50") \
        .getOrCreate()
    
    hdfs_base = "hdfs://namenode:9000/data/movielens/csv"
    
    csv_files = {
        "movie.csv": ["movieId", "title", "genres"],
        "rating.csv": ["userId", "movieId", "rating", "timestamp"],
        "tag.csv": ["userId", "movieId", "tag", "timestamp"],
        "genome_tags.csv": ["tagId", "tag"],
        "genome_scores.csv": ["movieId", "tagId", "relevance"],
        "link.csv": ["movieId", "imdbId", "tmdbId"]
    }
    
    print("\n" + "="*60)
    print("VERIFICACIÓN DE INTEGRIDAD - MovieLens en HDFS")
    print("="*60 + "\n")
    
    total_lines = 0
    results = []
    
    for filename, columns in csv_files.items():
        path = f"{hdfs_base}/{filename}"
        print(f"📄 Procesando: {filename}")
        
        try:
            # Leer CSV (con header)
            df = spark.read.option("header", "true").csv(path)
            
            # Contar líneas (sin header)
            count = df.count()
            total_lines += count
            
            # Primeras filas
            print(f"   ✓ Líneas (sin header): {count:,}")
            print(f"   ✓ Columnas esperadas: {', '.join(columns)}")
            print(f"   ✓ Columnas leídas: {', '.join(df.columns)}")
            
            # Verificar schema match
            cols_match = set(df.columns) == set(columns)
            if cols_match:
                print(f"   ✓ Schema: OK")
            else:
                print(f"   ⚠ Schema mismatch!")
                print(f"      Esperado: {columns}")
                print(f"      Obtenido: {df.columns}")
            
            # Muestra
            print(f"   📊 Muestra (3 filas):")
            df.show(3, truncate=False)
            
            results.append({
                'file': filename,
                'lines': count,
                'schema_ok': cols_match
            })
            
        except Exception as e:
            print(f"   ✗ ERROR: {str(e)}")
            results.append({
                'file': filename,
                'lines': 0,
                'schema_ok': False,
                'error': str(e)
            })
        
        print("-" * 60 + "\n")
    
    # Resumen
    print("="*60)
    print("RESUMEN DE VERIFICACIÓN")
    print("="*60)
    print(f"\n{'Archivo':<25} {'Líneas':>15} {'Schema':>10}")
    print("-" * 60)
    
    for r in results:
        status = "✓ OK" if r.get('schema_ok', False) else "✗ FAIL"
        lines_str = f"{r['lines']:,}" if r['lines'] > 0 else "ERROR"
        print(f"{r['file']:<25} {lines_str:>15} {status:>10}")
    
    print("-" * 60)
    print(f"{'TOTAL':<25} {total_lines:>15,}")
    print("="*60 + "\n")
    
    # Comparación con conteos esperados
    expected = {
        "movie.csv": 27278,  # 27279 - 1 header
        "rating.csv": 20000263,  # 20000264 - 1 header
        "tag.csv": 465564,  # 465565 - 1 header
        "genome_tags.csv": 1128,  # 1129 - 1 header
        "genome_scores.csv": 11709768,  # 11709769 - 1 header
        "link.csv": 27278  # 27279 - 1 header
    }
    
    print("COMPARACIÓN CON DATOS LOCALES:")
    print("-" * 60)
    all_match = True
    for r in results:
        fname = r['file']
        hdfs_count = r['lines']
        expected_count = expected.get(fname, 0)
        
        if hdfs_count == expected_count:
            status = "✓ MATCH"
        else:
            status = f"✗ DIFF ({hdfs_count - expected_count:+,})"
            all_match = False
        
        print(f"{fname:<25} HDFS: {hdfs_count:>12,}  Local: {expected_count:>12,}  {status}")
    
    print("="*60)
    
    if all_match:
        print("\n✅ VERIFICACIÓN EXITOSA: Todos los archivos coinciden")
        spark.stop()
        return 0
    else:
        print("\n⚠️ ADVERTENCIA: Algunos archivos difieren")
        spark.stop()
        return 1

if __name__ == "__main__":
    sys.exit(verify_csv_integrity())
