# Analyse de logs web en Python

Ce projet contient un script Python permettant d'analyser un fichier de logs web compressé au format `.gz`.

## Objectif

Le script recherche les requêtes `GET` vers :

- `/assur/am24...`
- `/cyberpme/cyb...`

Il permet ensuite de :

- filtrer les requêtes sur une période donnée ;
- regrouper les accès par adresse IP et par ressource ;
- compter le nombre d'accès ;
- repérer les accès effectués avant `11:15` ou après `11:30` ;
- appliquer les contraintes de longueur demandées dans l'exercice ;
- afficher les IP ayant consulté plusieurs fichiers ;
- exporter les résultats dans `resultats.json`.

## Structure

```text
analyse-logs/
├── README.md
├── Web_script.py
└── .gitignore
```

Le fichier de logs `.gz` n'est pas inclus dans le dépôt.

## Utilisation

Le script fonctionne avec Python 3 et n'utilise aucune bibliothèque externe.

Lancer l'analyse :

```bash
python3 Web_script.py copie_access.log.gz
```

Le fichier `resultats.json` sera créé automatiquement.

### Choisir le fichier JSON de sortie

```bash
python3 Web_script.py copie_access.log.gz -o analyse.json
```

### Modifier la période d'analyse

```bash
python3 Web_script.py copie_access.log.gz \
  --debut "2025-11-03T09:45:00+01:00" \
  --fin "2025-11-03T13:00:00+01:00"
```

Par défaut, le script utilise la période :

```text
03/11/2025 09:45 → 03/11/2025 13:00
```

avec le fuseau horaire `+01:00`.

## Fonctionnement

Le script :

1. ouvre le fichier `.gz` avec `gzip` ;
2. analyse chaque ligne avec une expression régulière ;
3. récupère l'adresse IP, la date et la ressource demandée ;
4. ignore les requêtes situées hors de la période choisie ;
5. compte les accès pour chaque couple IP / ressource ;
6. filtre les ressources selon les contraintes de l'exercice ;
7. affiche les résultats dans le terminal ;
8. exporte les données au format JSON.

## Exemple de sortie

```text
IP ayant accédé à plusieurs fichiers d'assurance maladie :
192.0.2.10 => /assur/am24..., /assur/am24...

IP ayant accédé à plusieurs fichiers cyber :
Aucune.

IP par fichier valide :
/assur/am24... => 192.0.2.10
```

## Fichier JSON

Le fichier généré contient une structure de ce type :

```json
{
  "192.0.2.10": {
    "/assur/am24...": {
      "count": 3,
      "before_1115": true,
      "after_1130": false
    }
  }
}
```

## Améliorations apportées

Cette version :

- ne contient plus de chemin Windows personnel ;
- accepte le fichier de logs en argument ;
- vérifie les erreurs de saisie et les fichiers manquants ;
- sépare le programme en fonctions ;
- utilise des noms de variables plus explicites ;
- permet de modifier la période depuis la ligne de commande ;
- produit un JSON lisible et trié.

## Remarque

Les fichiers de logs peuvent contenir des adresses IP et d'autres informations sensibles. Il est donc préférable de ne pas publier le fichier `.log.gz` sur un dépôt GitHub public.
