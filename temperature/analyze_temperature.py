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
        
        # Préparer les résultats JSON
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
        
        # Construire le texte de résultat
        result_text_lines = []
        result_text_lines.append("====================================")
        result_text_lines.append("   ANALYSE DES TEMPÉRATURES")
        result_text_lines.append("====================================")
        result_text_lines.append("")
        result_text_lines.append(f"Année la plus chaude : {hottest_year}")
        result_text_lines.append(f"Température moyenne  : {hottest_temp}°C")
        result_text_lines.append(f"Temps d'exécution    : {results_data['execution_time_seconds']}s")
        result_text_lines.append(f"Total de mesures     : {total_rows:,}")
        result_text_lines.append("")
        result_text_lines.append("Détails par année:")
        result_text_lines.append(f"{'Année':<8} {'Temp Moy':<12}")
        result_text_lines.append("─" * 25)
        
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
            
            result_text_lines.append(f"{row.year:<8} {row.avg_temp:>10.2f}°C")
        
        result_text_lines.append("")
        result_text_lines.append("====================================")
        
        print("-" * 60)
        print()
        
        # Afficher le résultat principal
        print("="*60)
        print(f"🔥 ANNÉE LA PLUS CHAUDE : {hottest_year}")
        print(f"   Température moyenne  : {hottest_temp}°C")
        print("="*60)
        
        # Sauvegarder dans HDFS
        print()
        print(f"💾 Sauvegarde des résultats dans HDFS: {output_path}")
        
        # 1. Sauvegarder le texte (chaque ligne = une ligne dans HDFS)
        text_rdd = spark.sparkContext.parallelize(result_text_lines, 1)
        text_rdd.saveAsTextFile(f"{output_path}/result.txt")
        print(f"   ✅ result.txt sauvegardé")
        
        # 2. Sauvegarder le JSON (une seule ligne)
        json_str = json.dumps(results_data, indent=2)
        json_rdd = spark.sparkContext.parallelize([json_str], 1)
        json_rdd.saveAsTextFile(f"{output_path}/result.json")
        print(f"   ✅ result.json sauvegardé")
        
        execution_time = time.time() - start_time
        print()
        print(f"⏱️  Temps d'exécution total: {execution_time:.2f}s")
        print()
        
        # Vérifier que les fichiers ont bien été écrits
        print("🔍 Vérification des fichiers HDFS:")
        import subprocess
        try:
            result = subprocess.run(
                ["/opt/hadoop/current/bin/hdfs", "dfs", "-ls", "-h", f"{output_path}/"],
                capture_output=True,
                text=True
            )
            print(result.stdout)
        except Exception as e:
            print(f"   Impossible de lister: {e}")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        spark.stop()

if __name__ == "__main__":
    main()