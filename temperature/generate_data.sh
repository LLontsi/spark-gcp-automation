#!/bin/bash
set -e

echo "=========================================="
echo "  GÉNÉRATION DONNÉES DE TEMPÉRATURE (5MB)"
echo "=========================================="
echo ""

# Configuration
HDFS_URL="hdfs://10.0.0.10:9000"
OUTPUT_HDFS="$HDFS_URL/user/spark/temperature/data.csv"
TEMP_FILE="/tmp/temperature_data.csv"
TARGET_SIZE_MB=5  # <--- MODIFIÉ ICI POUR 5MB

# Nettoyage préventif (local et HDFS) pour être sûr de régénérer
rm -f "$TEMP_FILE"
/opt/hadoop/current/bin/hdfs dfs -rm -f "$OUTPUT_HDFS" 2>/dev/null || true

echo "📊 Configuration:"
echo "   Taille cible: ${TARGET_SIZE_MB}MB"
echo "   Format: CSV (date,city,temperature)"
echo ""

# Créer le répertoire HDFS si nécessaire
/opt/hadoop/current/bin/hdfs dfs -mkdir -p /user/spark/temperature

echo "🔄 Génération des données avec Python (Rapide)..."

# Génération via Python pour la vitesse et la précision
python3 -c "
import random
import datetime
import os

target_size = $TARGET_SIZE_MB * 1024 * 1024
filename = '$TEMP_FILE'

cities = [
    'Paris', 'Lyon', 'Marseille', 'Toulouse', 'Nice', 
    'Berlin', 'Hamburg', 'Munich', 'Cologne', 'Frankfurt',
    'London', 'Birmingham', 'Manchester', 'Liverpool', 'Leeds',
    'Madrid', 'Barcelona', 'Valencia', 'Seville', 'Bilbao',
    'Rome', 'Milan', 'Naples', 'Turin', 'Florence',
    'Amsterdam', 'Rotterdam', 'Utrecht', 'Eindhoven', 'Groningen',
    'Brussels', 'Antwerp', 'Ghent', 'Liege', 'Bruges',
    'Vienna', 'Graz', 'Linz', 'Salzburg', 'Innsbruck',
    'Zurich', 'Geneva', 'Basel', 'Bern', 'Lausanne',
    'Stockholm', 'Oslo', 'Copenhagen', 'Helsinki', 'Dublin'
]

start_date = datetime.date(2020, 1, 1)
end_date = datetime.date(2025, 12, 31)
delta_days = (end_date - start_date).days

with open(filename, 'w') as f:
    # Écriture de l'en-tête
    header = 'date,city,temperature\n'
    f.write(header)
    current_size = len(header)
    
    while current_size < target_size:
        buffer = []
        # Générer par bloc de 1000 lignes pour la performance
        for _ in range(1000):
            # Date aléatoire
            random_days = random.randint(0, delta_days)
            date = start_date + datetime.timedelta(days=random_days)
            year = date.year
            month = date.month
            
            # Heure aléatoire
            hour = random.randint(0, 23)
            
            # Ville
            city = random.choice(cities)
            
            # Logique de température (reproduction de la logique bash)
            base_temp = 17
            if year == 2020: base_temp = 15
            elif year == 2021: base_temp = 16
            elif year == 2022: base_temp = 17
            elif year == 2023: base_temp = 19 # Année chaude
            elif year == 2024: base_temp = 18
            
            seasonal = 0
            if 6 <= month <= 8: seasonal = 10
            elif month >= 12 or month <= 2: seasonal = -5
            
            variation = random.randint(-5, 5)
            temp = base_temp + seasonal + variation
            
            # Format: 2023-05-12T14:00:00,Paris,24
            line = f'{date}T{hour:02d}:00:00,{city},{temp}\n'
            buffer.append(line)
        
        chunk = ''.join(buffer)
        f.write(chunk)
        current_size += len(chunk)

print(f'   ✅ Fichier généré : {current_size / (1024*1024):.2f} MB')
"

echo ""
echo "📤 Upload vers HDFS..."
/opt/hadoop/current/bin/hdfs dfs -put "$TEMP_FILE" "$OUTPUT_HDFS"

echo "🧹 Nettoyage fichier temporaire..."
rm -f "$TEMP_FILE"

echo ""
echo "✅ Génération terminée !"
FILE_SIZE=$(/opt/hadoop/current/bin/hdfs dfs -du -h "$OUTPUT_HDFS" | awk '{print $1, $2}')
echo "   Fichier : $OUTPUT_HDFS"
echo "   Taille  : $FILE_SIZE"
echo ""
echo "Pour vérifier le contenu :"
echo "   hdfs dfs -head $OUTPUT_HDFS"