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
TARGET_SIZE_MB=5  # ✅ CHANGÉ: 5MB au lieu de 100MB

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

echo "🔄 Génération des données (Python)..."

# Utiliser Python pour générer rapidement (30x plus rapide que bash)
python3 << 'PYTHON_EOF'
import random
import csv
from datetime import datetime, timedelta

TARGET_SIZE_MB = 5
TARGET_BYTES = TARGET_SIZE_MB * 1024 * 1024
OUTPUT_FILE = "/tmp/temperature_data.csv"

# 50 villes européennes
CITIES = [
    "Paris", "Lyon", "Marseille", "Toulouse", "Nice",
    "Berlin", "Hamburg", "Munich", "Cologne", "Frankfurt",
    "London", "Birmingham", "Manchester", "Liverpool", "Leeds",
    "Madrid", "Barcelona", "Valencia", "Seville", "Bilbao",
    "Rome", "Milan", "Naples", "Turin", "Florence",
    "Amsterdam", "Rotterdam", "Utrecht", "Eindhoven", "Groningen",
    "Brussels", "Antwerp", "Ghent", "Liege", "Bruges",
    "Vienna", "Graz", "Linz", "Salzburg", "Innsbruck",
    "Zurich", "Geneva", "Basel", "Bern", "Lausanne",
    "Stockholm", "Oslo", "Copenhagen", "Helsinki", "Dublin"
]

# Températures de base par année (2023 = la plus chaude)
YEAR_BASE_TEMPS = {
    2020: 15,
    2021: 16,
    2022: 17,
    2023: 19,  # Année la plus chaude
    2024: 18,
    2025: 17
}

# Variation saisonnière par mois
SEASONAL_VARIATION = {
    1: -5, 2: -5, 3: 0, 4: 3, 5: 7, 6: 10,
    7: 12, 8: 11, 9: 7, 10: 3, 11: 0, 12: -5
}

print("   Génération en cours...")

with open(OUTPUT_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['date', 'city', 'temperature'])
    
    current_size = 0
    lines_written = 0
    
    # Générer jusqu'à atteindre 5MB
    while current_size < TARGET_BYTES:
        # Année aléatoire
        year = random.choice([2020, 2021, 2022, 2023, 2024, 2025])
        
        # Date aléatoire
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        hour = random.randint(0, 23)
        
        date_str = f"{year}-{month:02d}-{day:02d}T{hour:02d}:00:00"
        
        # Ville aléatoire
        city = random.choice(CITIES)
        
        # Température = base_année + variation_mois + aléatoire
        base_temp = YEAR_BASE_TEMPS[year]
        seasonal = SEASONAL_VARIATION[month]
        random_var = random.randint(-5, 5)
        
        temperature = base_temp + seasonal + random_var
        
        # Écrire la ligne
        writer.writerow([date_str, city, temperature])
        
        lines_written += 1
        
        # Estimer la taille (30 bytes par ligne environ)
        current_size = lines_written * 30
        
        # Afficher progression tous les 50k lignes
        if lines_written % 50000 == 0:
            size_mb = current_size / (1024 * 1024)
            progress = (current_size / TARGET_BYTES) * 100
            print(f"   Progress: {progress:.0f}% - {lines_written:,} lignes - {size_mb:.1f}MB")

size_mb = current_size / (1024 * 1024)
print(f"   ✅ Terminé: {lines_written:,} lignes - {size_mb:.1f}MB")

PYTHON_EOF

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