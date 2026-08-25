# Rendu 360° — Pipeline de stitching & visionneuse WebGL/Three.js

Projet en deux blocs : assemblage panoramique (stitching) à partir de photos
avec recouvrement, puis préparation des assets et visionneuse interactive
360° pour navigateur.

## Sommaire

- [Aperçu](#aperçu)
- [Structure du projet](#structure-du-projet)
- [Installation](#installation)
- [Bloc 1 — Pipeline de stitching](#bloc-1--pipeline-de-stitching)
- [Bloc 2 — Assets & visionneuse](#bloc-2--assets--visionneuse)
- [Déploiement Streamlit](#déploiement-streamlit)
- [Dépannage](#dépannage)

## Aperçu

| Bloc | Objectif | Fichier(s) principal(aux) |
|---|---|---|
| **Bloc 1** | Assembler des photos avec recouvrement en un panorama équirectangulaire (360°) | `stitching_pipeline.py` |
| **Bloc 2** | Générer des assets optimisés et les visualiser en navigation 360° interactive | `asset_prep.py`, `panorama_viewer.html` |
| — | Déploiement web des deux blocs | `streamlit_app.py` |

## Structure du projet

```
Projet_WTM/
├── data/
│   ├── raw/                    # photos sources brutes (jamais modifiées)
│   └── processed/              # panoramas assemblés (sorties du Bloc 1)
├── src/
│   ├── stitching_pipeline.py   # pipeline de stitching (Bloc 1)
│   └── asset_prep.py           # préparation des assets (Bloc 2)
├── notebooks/
│   └── main.ipynb              # notebook de test/exploration
├── outputs/
│   ├── panoramas/               # résultats finaux Bloc 1
│   └── assets_360/              # assets optimisés Bloc 2
├── panorama_viewer.html         # visionneuse Three.js (Bloc 2)
├── streamlit_app.py             # point d'entrée déploiement Streamlit
├── requirements.txt
├── .gitignore
└── README.md
```

## Installation

```bash
git clone <url-de-ce-repo>
cd Projet_WTM
pip install -r requirements.txt
```

`requirements.txt` :
```
opencv-python
opencv-contrib-python
numpy
Pillow
streamlit
```

## Bloc 1 — Pipeline de stitching

Assemble un dossier de photos avec chevauchement en un panorama
équirectangulaire. Deux modes : `auto` (cv2.Stitcher, rapide) et `manual`
(pipeline pas-à-pas, plus robuste sur un 360° complet).

**En ligne de commande :**
```bash
python stitching_pipeline.py --input data/raw/mon_dataset --output outputs/panoramas/panorama.jpg --mode auto
```

**Depuis un notebook Jupyter** (l'exécution CLI ne fonctionne pas dans
Jupyter, `ipykernel_launcher` intercepte les arguments) :
```python
from stitching_pipeline import run_pipeline

run_pipeline(
    input_dir="data/raw/mon_dataset",
    output_path="outputs/panoramas/panorama.jpg",
    mode="auto",             # ou "manual"
    output_width=4096,
    output_height=2048,
)
```

Options principales : `--detector` (`sift`/`orb`/`akaze`), `--blend`
(`multiband`/`feather`), `--out-width`, `--out-height`. Détail des 6 étapes
du pipeline (prétraitement → détection → matching → homographie → warping →
blending) dans les commentaires du script.

## Bloc 2 — Assets & visionneuse

### Génération des assets optimisés

Produit plusieurs résolutions (haute qualité, standard, aperçu) en JPEG et/ou
WebP à partir d'un panorama, avec un manifeste JSON documentant chaque fichier.

```bash
python asset_prep.py --input outputs/panoramas/panorama.jpg --output-dir outputs/assets_360 --name mon_panorama --formats jpg webp
```

Depuis un notebook :
```python
from asset_prep import prepare_assets

prepare_assets("outputs/panoramas/panorama.jpg", "outputs/assets_360", name="mon_panorama")
```

### Visionneuse 360°

`panorama_viewer.html` est un prototype autonome (Three.js via CDN, aucune
installation nécessaire) :

1. Ouvrir le fichier directement dans un navigateur (double-clic), ou le
   servir via `streamlit run streamlit_app.py`.
2. Glisser-déposer un ou plusieurs panoramas équirectangulaires, ou utiliser
   le bouton **Charger panorama(s)**.
3. Chaque image chargée devient une **scène** listée dans le panneau de
   gauche — cliquer dessus pour y naviguer.
4. **Mode édition hotspots** : cliquer sur l'image affiche un menu pour créer
   un point de navigation vers une autre scène chargée ; cliquer sur un
   marqueur existant en mode édition le supprime ; en navigation normale, un
   clic sur un marqueur bascule vers la scène liée.
5. **Exporter config (JSON)** télécharge la structure des scènes et hotspots
   (angles en degrés), à adapter avec les chemins réels des assets pour une
   intégration en production.

Contrôles additionnels : rotation automatique, zoom (FOV), plein écran.

## Déploiement Streamlit

`streamlit_app.py` embarque la visionneuse (`panorama_viewer.html` via
`st.components.v1.html`) et expose `asset_prep.py` comme formulaire
upload → génération → téléchargement.

**Test local :**
```bash
streamlit run streamlit_app.py
```

**Déploiement sur Streamlit Community Cloud :**
1. Pousser ce repo sur GitHub (`panorama_viewer.html`, `asset_prep.py` et
   `streamlit_app.py` doivent être à la racine, ou adapter les chemins dans
   `streamlit_app.py`).
2. Sur [share.streamlit.io](https://share.streamlit.io), connecter le repo.
3. Indiquer `streamlit_app.py` comme fichier principal.

La visionneuse charge Three.js depuis `cdnjs.cloudflare.com` et
`cdn.jsdelivr.net` : un accès internet sortant est nécessaire côté serveur
de déploiement (généralement le cas sur Streamlit Cloud).

## Dépannage

- **`ImportError: cannot import name 'run_pipeline'`** : le fichier
  `stitching_pipeline.py` local est une version obsolète — le retélécharger
  et redémarrer le kernel Jupyter (`importlib.reload` en dépannage rapide).
- **Écriture du panorama en échec silencieux** : vérifier qu'aucun dossier
  ne porte déjà le nom du fichier de sortie (`os.path.isdir` déclenche une
  erreur explicite dans la version actuelle du script).
- **« Échec du chargement » dans la visionneuse** : ouvrir la console
  navigateur (F12) pour le détail ; le chargement passe par `FileReader`
  (Data URL), plus robuste que les Blob URLs en ouverture `file://` directe.
- **Page blanche dans la visionneuse** : vérifier la connexion internet —
  Three.js est chargé depuis un CDN externe, non embarqué dans le fichier.
