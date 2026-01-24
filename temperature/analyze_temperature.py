#!/usr/bin/env python3
"""
Analyse des températures avec Apache Spark
Trouve l'année la plus chaude entre 2020 et 2025
"""
import sys
import time
from pyspark.sql import SparkSession
from pyspark.sql.functions import year, avg, col, count, min as spark_min, max as spark_max
import json

def main():
    # Configuration
    hdfs_url = "hdfs://10.0.0.10:9000"
    input_path = f"{hdfs_url}/user/spark/temperature/data.csv"
    output_path = f"{hdfs_url}/user/spark/temperature/results"
    
    print("="*60)
    print("        ANALYSE DES TEMPÉRATURES AVEC SPARK")
    print("="*60)
    print()
    
    # Créer session Spark
    spark = SparkSession.builder \
        .appName("Temperature-Analysis") \
        .config("spark.eventLog.enabled", "false") \
        .getOrCreate()
    
    start_time = time.time()
    
    try:
        # Lire les données
        print(f"📖 Lecture des données depuis: {input_path}")
        df = spark.read.csv(input_path, header=True, inferSchema=True)
        
        # Statistiques de base
        total_rows = df.count()
        print(f"   Total de lignes: {total_rows:,}")
        
        # Extraire l'année et calculer moyennes
        print()
        print("🔢 Calcul des températures moyennes par année...")
        
        yearly_avg = df.withColumn("year", year(col("date"))) \
            .groupBy("year") \
            .agg(
                avg("temperature").alias("avg_temp"),
                count("*").alias("records"),
                spark_min("temperature").alias("min_temp"),
                spark_max("temperature").alias("max_temp")
            ) \
            .orderBy("year")
        
        # Collecter les résultats
        results = yearly_avg.collect()
        
        # Trouver l'année la plus chaude
        hottest_year_row = max(results, key=lambda x: x.avg_temp)
        hottest_year = hottest_year_row.year
        hottest_temp = round(hottest_year_row.avg_temp, 2)
        
        # Préparer les résultats
        results_data = {
            "hottest_year": int(hottest_year),
            "hottest_avg_temperature": hottest_temp,
            "total_records": int(total_rows),
            "execution_time_seconds": round(time.time() - start_time, 2),
            "years_analysis": []
        }
        
        print()
        print("📊 RÉSULTATS PAR ANNÉE:")
        print("-" * 60)
        print(f"{'Année':<8} {'Temp Moy':<12} {'Min':<8} {'Max':<8} {'Mesures':<12}")
        print("-" * 60)
        
        for row in results:
            year_data = {
                "year": int(row.year),
                "avg_temperature": round(row.avg_temp, 2),
                "min_temperature": int(row.min_temp),
                "max_temperature": int(row.max_temp),
                "records": int(row.records)
            }
            results_data["years_analysis"].append(year_data)
            
            print(f"{row.year:<8} {row.avg_temp:>10.2f}°C  "
                  f"{row.min_temp:>6}°C  {row.max_temp:>6}°C  "
                  f"{row.records:>10,}")
        
        print("-" * 60)
        print()
        
        # Afficher le résultat principal
        print("="*60)
        print(f"🔥 ANNÉE LA PLUS CHAUDE : {hottest_year}")
        print(f"   Température moyenne  : {hottest_temp}°C")
        print("="*60)
        
        # Sauvegarder les résultats dans HDFS
        
        # 1. Résultat texte formaté
        result_text = f"""====================================
   ANALYSE DES TEMPÉRATURES
====================================

Année la plus chaude : {hottest_year}
Température moyenne  : {hottest_temp}°C
Temps d'exécution    : {results_data['execution_time_seconds']}s
Total de mesures     : {total_rows:,}

Détails par année:
{'Année':<8} {'Temp Moy':<12}
{'─'*25}
"""
        for year_data in results_data["years_analysis"]:
            result_text += f"{year_data['year']:<8} {year_data['avg_temperature']:>10.2f}°C\n"
        
        result_text += "\n====================================\n"
        
        # Sauvegarder le texte
        text_rdd = spark.sparkContext.parallelize([result_text])
        text_rdd.saveAsTextFile(f"{output_path}/result.txt")
        
        # 2. Résultat JSON
        json_str = json.dumps(results_data, indent=2)
        json_rdd = spark.sparkContext.parallelize([json_str])
        json_rdd.saveAsTextFile(f"{output_path}/result.json")
        
        execution_time = time.time() - start_time
        print()
        print(f"⏱️  Temps d'exécution total: {execution_time:.2f}s")
        print(f"💾 Résultats sauvegardés dans: {output_path}")
        print()
        
    except Exception as e:
        print(f"\n❌ ERREUR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        spark.stop()

if __name__ == "__main__":
    main()