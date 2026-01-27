# Analyse des Températures avec Spark 🌡️

## Description

Projet de démonstration CI/CD qui génère 2GB de données de température (2020-2025) et utilise Apache Spark pour analyser l'année la plus chaude.

## Architecture

- **Données** : 2GB stockées dans HDFS
- **Période** : 2020-2025
- **Locations** : 100 villes
- **Fréquence** : Mesures toutes les heures
- **Total** : ~68 millions de lignes

## Fichiers

- `generate_data.sh` : Génère les données synthétiques
- `analyze_temperature.py` : Job Spark pour l'analyse
- `run_temperature.sh` : Orchestre génération + analyse
- `README.md` : Cette documentation

## Utilisation Locale
```bash
# Générer les données
./generate_data.sh

# Analyser
./run_temperature.sh

# Voir les résultats
hdfs dfs -cat /user/spark/temperature/results/result.txt
```

## CI/CD

Le workflow GitHub Actions se déclenche automatiquement à chaque push sur `main` avec des modifications dans `temperature/`.

## Résultats Attendus

Le script affiche :
- L'année la plus chaude
- Températures moyennes par année .....
- Temps d'exécution
- Statistiques des données