#!/usr/bin/env python3
import sys
import time
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, count, min as spark_min, max as spark_max, substring
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

def main():
    # Configuration
    hdfs_url = "hdfs://10.0.0.10:9000"
    input_path = f"{hdfs_url}/user/spark/temperature/data.csv"
    output_path = f"{hdfs_url}/user/spark/temperature/results"
    
    spark = SparkSession.builder.appName("Temperature-Analysis-CICD").getOrCreate()
    start_time = time.time()
    
    try:
        # Définition du schéma
        schema = StructType([
            StructField("date", StringType(), True),
            StructField("city", StringType(), True),
            StructField("temperature", IntegerType(), True)
        ])
        
        # Lecture
        df = spark.read.option("header", "true").schema(schema).csv(input_path)
        df = df.filter(col("date").isNotNull() & col("temperature").isNotNull())
        
        # Extraction année
        df_with_year = df.withColumn("year", substring(col("date"), 1, 4).cast(IntegerType()))
        
        # Agrégation
        yearly_avg = df_with_year.groupBy("year").agg(
            avg("temperature").alias("avg_temp"),
            count("*").alias("records"),
            spark_min("temperature").alias("min_temp"),
            spark_max("temperature").alias("max_temp")
        ).orderBy("year")
        
        results = yearly_avg.collect()
        
        if not results:
            raise Exception("Aucune donnée trouvée après analyse")

        # --- Préparation des sorties ---

        # 1. Format Texte (lisible par humain)
        result_lines = ["annee,temp_moyenne,min,max,nb_mesures"]
        for r in results:
            result_lines.append(f"{r.year},{r.avg_temp:.2f},{r.min_temp},{r.max_temp},{r.records}")
        
        # 2. Format JSON (pour parsing machine/API)
        json_data = {
            "metadata": {"execution_time": 0, "status": "success"},
            "data": []
        }
        for r in results:
            json_data["data"].append({
                "year": r.year,
                "avg": round(r.avg_temp, 2),
                "records": r.records
            })
        json_str = json.dumps(json_data)

        # --- Sauvegarde HDFS ---
        
        # Sauvegarde result.txt (sous-dossier)
        spark.sparkContext.parallelize(result_lines, 1).saveAsTextFile(f"{output_path}/result_txt")
        
        # Sauvegarde result.json (sous-dossier)
        spark.sparkContext.parallelize([json_str], 1).saveAsTextFile(f"{output_path}/result_json")
        
        print(f"✅ Analyse terminée en {time.time() - start_time:.2f}s")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)
    finally:
        spark.stop()

if __name__ == "__main__":
    main()