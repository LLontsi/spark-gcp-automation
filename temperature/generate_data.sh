#!/bin/bash
set -e

echo "=========================================="
echo "  GÉNÉRATION DONNÉES MÉTÉO (2MB) - BASH"
echo "=========================================="

# Configuration
HDFS_URL="hdfs://10.0.0.10:9000"
OUTPUT_HDFS="$HDFS_URL/user/spark/temperature/data.csv"
TEMP_FILE="/tmp/temperature_data.csv"
TARGET_SIZE_MB=2

# Nettoyage préalable
rm -f "$TEMP_FILE"
/opt/hadoop/current/bin/hdfs dfs -rm -f "$OUTPUT_HDFS" 2>/dev/null || true
/opt/hadoop/current/bin/hdfs dfs -mkdir -p /user/spark/temperature

# Villes
CITIES=("Paris" "Lyon" "Marseille" "Toulouse" "Nice" "Berlin" "Hamburg" "Munich" "London" "Manchester" "Madrid" "Rome" "Milan" "Brussels" "Vienna" "Zurich" "Geneva" "Amsterdam" "Dublin" "Oslo")

echo "🔄 Génération des données en cours..."
echo "date,city,temperature" > "$TEMP_FILE"

# 2MB représente environ 66,000 lignes
TOTAL_LINES=70000
CHUNK_SIZE=5000
LINES_GENERATED=0

while [ $LINES_GENERATED -lt $TOTAL_LINES ]; do
    for ((i=1; i<=CHUNK_SIZE; i++)); do
        YEAR=$((2020 + RANDOM % 6))
        MONTH=$(printf "%02d" $((1 + RANDOM % 12)))
        DAY=$(printf "%02d" $((1 + RANDOM % 28)))
        HOUR=$(printf "%02d" $((RANDOM % 24)))
        
        # Sélection ville aléatoire
        RAND_CITY_IDX=$((RANDOM % ${#CITIES[@]}))
        CITY=${CITIES[$RAND_CITY_IDX]}
        
        # Température simplifiée
        BASE_TEMP=15
        VARIATION=$((RANDOM % 20 - 5))
        TEMP=$((BASE_TEMP + VARIATION))
        
        echo "${YEAR}-${MONTH}-${DAY}T${HOUR}:00:00,${CITY},${TEMP}" >> "$TEMP_FILE"
    done
    
    LINES_GENERATED=$((LINES_GENERATED + CHUNK_SIZE))
    
    # Vérification taille
    CURRENT_SIZE=$(du -m "$TEMP_FILE" | cut -f1)
    if [ $CURRENT_SIZE -ge $TARGET_SIZE_MB ]; then
        break
    fi
done

echo "📤 Upload vers HDFS..."
/opt/hadoop/current/bin/hdfs dfs -put "$TEMP_FILE" "$OUTPUT_HDFS"
rm -f "$TEMP_FILE"

echo "✅ Terminé !"
/opt/hadoop/current/bin/hdfs dfs -du -h "$OUTPUT_HDFS"