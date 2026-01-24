#!/bin/bash
set -e

echo "=========================================="
echo "   ANALYSE TEMPÉRATURE - WORKFLOW COMPLET"
echo "=========================================="
echo ""

HDFS_URL="hdfs://10.0.0.10:9000"
DATA_PATH="$HDFS_URL/user/spark/temperature/data.csv"
RESULTS_PATH="$HDFS_URL/user/spark/temperature/results"

# Vérifier HDFS
echo "🔍 Vérification HDFS..."
if ! /opt/hadoop/current/bin/hdfs dfs -test -e /user/spark 2>/dev/null; then
    echo " HDFS non accessible!"
    exit 1
fi
echo " HDFS accessible"
echo ""

# Étape 1: Générer les données si nécessaire
echo " Étape 1/3: Vérification des données..."
if /opt/hadoop/current/bin/hdfs dfs -test -e "$DATA_PATH" 2>/dev/null; then
    FILE_SIZE=$(/opt/hadoop/current/bin/hdfs dfs -du -h "$DATA_PATH" | awk '{print $1, $2}')
    echo " Données existantes ($FILE_SIZE)"
else
    echo "  Données manquantes, génération..."
    ./generate_data.sh
fi
echo ""

# Étape 2: Supprimer anciens résultats
echo "Étape 2/3: Nettoyage résultats précédents..."
/opt/hadoop/current/bin/hdfs dfs -rm -r -f "$RESULTS_PATH" 2>/dev/null || true
echo "Nettoyage effectué"
echo ""

# Étape 3: Lancer l'analyse Spark
echo " Étape 3/3: Lancement analyse Spark..."
echo ""

START_TIME=$(date +%s)

/opt/spark/current/bin/spark-submit \
    --master spark://10.0.0.10:7077 \
    --deploy-mode client \
    --executor-memory 4G \
    --driver-memory 2G \
    --num-executors 4 \
    --executor-cores 1 \
    ./analyze_temperature.py

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "=========================================="
echo "           ANALYSE TERMINÉE"
echo "=========================================="
echo "  Durée totale: ${DURATION}s"
echo ""
echo "Résultats disponibles dans HDFS:"
echo "   hdfs dfs -cat $RESULTS_PATH/result.txt/part-00000"
echo "   hdfs dfs -cat $RESULTS_PATH/result.json/part-00000"
echo ""

# Afficher le résultat texte
echo " RÉSULTAT:"
echo ""
/opt/hadoop/current/bin/hdfs dfs -cat "$RESULTS_PATH/result.txt/part-00000"