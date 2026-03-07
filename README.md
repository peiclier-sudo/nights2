# nights2

Generateur automatique de carrousels video TikTok.

## Architecture

```
[DeepSeek API] -> [Texte + mots-cles] -> [Images libres] -> [Assemblage video] -> [Export TikTok]
```

## Workflow

1. **DeepSeek API** genere le texte de chaque slide + mots-cles pour les images
2. **Pexels/Pixabay** fournissent les images gratuitement via leurs APIs
3. **Pillow** ajoute le texte sur les images avec fond semi-transparent
4. **MoviePy + FFmpeg** assemble le tout en video 9:16 (1080x1920)

## Installation

```bash
# Python 3.10+
pip install -r requirements.txt

# FFmpeg (requis par MoviePy)
# Linux:   sudo apt install ffmpeg
# macOS:   brew install ffmpeg
# Windows: choco install ffmpeg
```

## Configuration

```bash
cp .env.example .env
# Editer .env avec vos cles API
```

| Cle | Source | Cout |
|-----|--------|------|
| `DEEPSEEK_API_KEY` | [deepseek.com](https://platform.deepseek.com) | Tres faible |
| `PEXELS_API_KEY` | [pexels.com/api](https://www.pexels.com/api/) | Gratuit (200 req/h) |
| `PIXABAY_API_KEY` | [pixabay.com/api](https://pixabay.com/api/docs/) | Gratuit |

## Utilisation

```bash
# Generer un carrousel de 6 slides
python main.py "Les bienfaits du sommeil"

# 8 slides avec musique
python main.py --slides 8 --music audio/chill.mp3 "Crypto pour debutants"
```

## Structure du projet

```
src/
  content/generator.py    # Generation de contenu (DeepSeek)
  images/downloader.py    # Telechargement d'images (Pexels/Pixabay)
  images/text_overlay.py  # Superposition de texte (Pillow)
  video/assembler.py      # Assemblage video (MoviePy)
  utils/config.py         # Configuration centralisee
main.py                   # Point d'entree CLI
```

## Polices

Placez des fichiers `.ttf` dans le dossier `fonts/`. Par defaut, le script cherche `Roboto-Bold.ttf` (disponible sur [Google Fonts](https://fonts.google.com/specimen/Roboto)).
