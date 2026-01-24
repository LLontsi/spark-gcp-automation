#!/bin/bash
set -e

echo "=========================================="
echo "  GÉNÉRATION DONNÉES DE TEMPÉRATURE"
echo "=========================================="
echo ""

# Configuration
HDFS_URL="hdfs://10.0.0.10:9000"
OUTPUT_HDFS="$HDFS_URL/user/spark/temperature/data.csv"
TEMP_FILE="/tmp/temperature_data.csv"
TARGET_SIZE_MB=100

# Vérifier si les données existent déjà
if /opt/hadoop/current/bin/hdfs dfs -test -e "$OUTPUT_HDFS" 2>/dev/null; then
    echo "✅ Données existent déjà dans HDFS"
    echo "   Localisation: $OUTPUT_HDFS"
    FILE_SIZE=$(/opt/hadoop/current/bin/hdfs dfs -du -h "$OUTPUT_HDFS" | awk '{print $1, $2}')
    echo "   Taille: $FILE_SIZE"
    echo ""
    echo "Pour régénérer, supprimez d'abord:"
    echo "   hdfs dfs -rm $OUTPUT_HDFS"
    exit 0
fi

echo "📊 Configuration:"
echo "   Taille cible: ${TARGET_SIZE_MB}MB"
echo "   Années: 2020-2025 (6 ans)"
echo "   Villes: 50"
echo "   Fréquence: horaire"
echo ""

# Créer le répertoire HDFS si nécessaire
echo "📁 Création répertoire HDFS..."
/opt/hadoop/current/bin/hdfs dfs -mkdir -p /user/spark/temperature

# Liste de 50 villes européennes
CITIES=(
    "Paris" "Lyon" "Marseille" "Toulouse" "Nice" 
    "Berlin" "Hamburg" "Munich" "Cologne" "Frankfurt"
    "London" "Birmingham" "Manchester" "Liverpool" "Leeds"
    "Madrid" "Barcelona" "Valencia" "Seville" "Bilbao"
    "Rome" "Milan" "Naples" "Turin" "Florence"
    "Amsterdam" "Rotterdam" "Utrecht" "Eindhoven" "Groningen"
    "Brussels" "Antwerp" "Ghent" "Liege" "Bruges"
    "Vienna" "Graz" "Linz" "Salzburg" "Innsbruck"
    "Zurich" "Geneva" "Basel" "Bern" "Lausanne"
    "Stockholm" "Oslo" "Copenhagen" "Helsinki" "Dublin"
)

echo "🔄 Génération des données..."

# En-tête CSV
echo "date,city,temperature" > "$TEMP_FILE"

# Calcul du nombre de lignes
# 100MB ≈ 3.3 millions de lignes (30 bytes par ligne)
# Pour plus de précision, générons en chunks
TOTAL_LINES=3300000
LINES_GENERATED=0
CHUNK_SIZE=100000

echo "   Génération de ${TOTAL_LINES} lignes par chunks de ${CHUNK_SIZE}..."

while [ $LINES_GENERATED -lt $TOTAL_LINES ]; do
    # Générer un chunk
    for i in $(seq 1 $CHUNK_SIZE); do
        # Année aléatoire entre 2020 et 2025
        YEAR=$((2020 + RANDOM % 6))
        
        # Mois et jour aléatoires
        MONTH=$(printf "%02d" $((1 + RANDOM % 12)))
        DAY=$(printf "%02d" $((1 + RANDOM % 28)))
        
        # Heure aléatoire
        HOUR=$(printf "%02d" $((RANDOM % 24)))
        
        # Ville aléatoire (50 villes)
        CITY=${CITIES[$((RANDOM % 50))]}
        
        # Température : Base selon année + variation saisonnière + aléatoire
        # 2023 sera l'année la plus chaude
        case $YEAR in
            2020) BASE_TEMP=15 ;;
            2021) BASE_TEMP=16 ;;
            2022) BASE_TEMP=17 ;;
            2023) BASE_TEMP=19 ;;  # Année la plus chaude
            2024) BASE_TEMP=18 ;;
            2025) BASE_TEMP=17 ;;
        esac
        
        # Variation saisonnière
        MONTH_INT=$((10#$MONTH))
        if [ $MONTH_INT -ge 6 ] && [ $MONTH_INT -le 8 ]; then
            SEASONAL=10  # Été
        elif [ $MONTH_INT -ge 12 ] || [ $MONTH_INT -le 2 ]; then
            SEASONAL=-5  # Hiver
        else
            SEASONAL=0   # Printemps/Automne
        fi
        
        # Aléatoire ±5
        RANDOM_VARIATION=$((RANDOM % 11 - 5))
        
        TEMP=$((BASE_TEMP + SEASONAL + RANDOM_VARIATION))
        
        # Ajouter au fichier
        echo "${YEAR}-${MONTH}-${DAY}T${HOUR}:00:00,${CITY},${TEMP}" >> "$TEMP_FILE"
    done
    
    LINES_GENERATED=$((LINES_GENERATED + CHUNK_SIZE))
    PROGRESS=$((LINES_GENERATED * 100 / TOTAL_LINES))
    CURRENT_SIZE=$(du -m "$TEMP_FILE" | cut -f1)
    echo "   Progress: ${PROGRESS}% - Taille actuelle: ${CURRENT_SIZE}MB"
    
    # Arrêter si on atteint 100MB
    if [ $CURRENT_SIZE -ge $TARGET_SIZE_MB ]; then
        echo "   ✅ Taille cible atteinte: ${CURRENT_SIZE}MB"
        break
    fi
done

FINAL_SIZE=$(du -h "$TEMP_FILE" | cut -f1)
FINAL_LINES=$(wc -l < "$TEMP_FILE")

echo ""
echo "📊 Statistiques du fichier généré:"
echo "   Taille: $FINAL_SIZE"
echo "   Lignes: $(printf "%'d" $FINAL_LINES)"
echo ""

echo "📤 Upload vers HDFS..."
/opt/hadoop/current/bin/hdfs dfs -put "$TEMP_FILE" "$OUTPUT_HDFS"

echo "🧹 Nettoyage fichier temporaire..."
rm -f "$TEMP_FILE"

echo ""
echo "✅ Génération terminée!"
FILE_SIZE=$(/opt/hadoop/current/bin/hdfs dfs -du -h "$OUTPUT_HDFS" | awk '{print $1, $2}')
echo "   Fichier: $OUTPUT_HDFS"
echo "   Taille: $FILE_SIZE"
echo ""
echo "Vérification:"
echo "   hdfs dfs -ls -h /user/spark/temperature/"
echo "   hdfs dfs -head /user/spark/temperature/data.csv"