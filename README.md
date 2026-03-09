# Scraper Entreprises de Nettoyage - France

Scraper multi-sources pour trouver les entreprises de nettoyage en France avec **priorité sur la collecte d'emails**.

## Sources

| Source | Description |
|--------|-------------|
| **Pages Jaunes** | Annuaire professionnel français |
| **Societe.com** | Données légales d'entreprises (SIRET, NAF) |
| **Google Search** | Recherche directe de sites web |
| **118712.fr** | Annuaire téléphonique |
| **Sites web** | Crawl profond des sites pour trouver les emails |

## Installation

```bash
pip install -r requirements.txt
```

## Utilisation

```bash
# Scrape complet (toutes sources, toutes régions)
python main.py

# Mode rapide (5 régions, moins de résultats)
python main.py --quick

# Cibler des villes spécifiques
python main.py --regions Paris Lyon Marseille

# Utiliser une seule source
python main.py --source pagesjaunes
python main.py --source google

# N'exporter que les entreprises avec email
python main.py --emails-only
```

## Configuration

Modifier `config.json` pour ajuster :
- `search_queries` : termes de recherche
- `regions` : villes/régions à cibler (30 par défaut)
- `max_results_per_query` : nombre de résultats Google par requête
- `request_delay_min/max` : délai entre requêtes (anti-rate-limit)
- `crawl_depth` : profondeur de crawl sur les sites web

## Sortie

Les résultats sont exportés dans le dossier `output/` :
- `entreprises_nettoyage.csv` : toutes les entreprises (trié: emails en premier)
- `entreprises_nettoyage_YYYYMMDD_HHMMSS.csv` : copie horodatée
- `emails_nettoyage_YYYYMMDD_HHMMSS.csv` : liste plate email → entreprise

### Colonnes CSV

| Colonne | Description |
|---------|-------------|
| name | Nom de l'entreprise |
| emails | Adresses email (séparées par \|) |
| phone | Téléphone |
| website | Site web |
| address | Adresse |
| siret | Numéro SIRET |
| siren | Numéro SIREN |
| naf_code | Code NAF/APE |
| source | Source de la donnée |

## Architecture

```
scraper/
├── __init__.py
├── utils.py              # Utilitaires (HTTP, emails, regex)
├── google_scraper.py     # Recherche Google
├── pagesjaunes_scraper.py # Pages Jaunes
├── societe_scraper.py    # Societe.com
├── annuaire_scraper.py   # Autres annuaires
└── email_hunter.py       # Crawl profond de sites web
main.py                   # Orchestrateur principal
config.json               # Configuration
```

## Stratégie de recherche d'emails

1. **Extraction directe** depuis les annuaires
2. **Crawl des sites web** en priorité sur les pages contact/about/mentions-légales
3. **Désobfuscation** des emails masqués ([at], (dot), etc.)
4. **Vérification MX** des domaines pour valider les emails devinés
5. **Patterns communs** (contact@, info@, commercial@) si le domaine a des records MX
