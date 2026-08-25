"""
============================================================================
 APP STREAMLIT — Rendu 360° (Bloc 1 & Bloc 2)
============================================================================
Point d'entrée pour un déploiement sur Streamlit Community Cloud.

Streamlit ne sert pas de fichiers HTML statiques directement : cette app
embarque panorama_viewer.html via st.components.v1.html (rendu dans un
iframe) et expose la préparation d'assets (asset_prep.py) comme un
formulaire d'upload/génération/téléchargement.

Structure de repo attendue (à la racine) :
    streamlit_app.py       <- ce fichier (point d'entrée)
    panorama_viewer.html   <- la visionneuse Three.js (Bloc 2)
    asset_prep.py          <- la génération d'assets optimisés (Bloc 2)
    stitching_pipeline.py  <- le pipeline de stitching (Bloc 1, optionnel ici)
    requirements.txt

Lancement local :
    pip install -r requirements.txt
    streamlit run streamlit_app.py

Déploiement : pousser le repo sur GitHub, puis sur share.streamlit.io
choisir ce repo et streamlit_app.py comme fichier principal.
============================================================================
"""

import io
import os
import zipfile

import streamlit as st
import streamlit.components.v1 as components

from asset_prep import DEFAULT_PROFILES, prepare_assets

st.set_page_config(page_title="Rendu 360° — Bloc 1 & 2", page_icon="🌐", layout="wide")

PAGE = st.sidebar.radio(
    "Navigation",
    ["Visionneuse 360°", "Préparation des assets"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Prototype Bloc 1 (stitching) & Bloc 2 (assets WebGL / Three.js) — "
    "cf. cahier des charges Rendu 360°."
)

# ============================================================================
# Page 1 — Visionneuse (embarque panorama_viewer.html)
# ============================================================================
if PAGE == "Visionneuse 360°":
    st.title("Visionneuse panoramique 360°")
    st.caption(
        "Chargez un ou plusieurs panoramas équirectangulaires directement dans la "
        "visionneuse ci-dessous (glisser-déposer ou bouton dédié). Le mode édition "
        "permet de créer des hotspots de navigation entre plusieurs scènes."
    )

    html_path = os.path.join(os.path.dirname(__file__), "panorama_viewer.html")
    if not os.path.exists(html_path):
        st.error(f"Fichier introuvable : {html_path}. Vérifiez qu'il est bien à la racine du repo.")
    else:
        with open(html_path, "r", encoding="utf-8") as f:
            components.html(f.read(), height=820, scrolling=False)

# ============================================================================
# Page 2 — Préparation des assets (upload -> génération -> téléchargement)
# ============================================================================
else:
    st.title("Préparation des assets 360°")
    st.caption(
        "Génère les déclinaisons optimisées (haute qualité / standard / aperçu, "
        "JPEG et WebP) d'un panorama équirectangulaire — cf. cahier des charges §4.3."
    )

    uploaded = st.file_uploader("Panorama source (équirectangulaire, ratio 2:1)", type=["jpg", "jpeg", "png"])

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Nom de base (préfixe des fichiers)", value="panorama")
        formats = st.multiselect("Formats à générer", ["jpg", "webp"], default=["jpg"])
    with col2:
        profile_labels = st.multiselect(
            "Profils de résolution",
            [p.label for p in DEFAULT_PROFILES],
            default=[p.label for p in DEFAULT_PROFILES],
            format_func=lambda l: {
                "hq": "Haute qualité (8192×4096)",
                "standard": "Standard (4096×2048)",
                "preview": "Aperçu léger (2048×1024)",
            }.get(l, l),
        )

    if st.button("Générer les assets", type="primary", disabled=uploaded is None):
        with st.spinner("Génération en cours…"):
            tmp_dir = "/tmp/asset_prep_output"
            os.makedirs(tmp_dir, exist_ok=True)
            input_path = os.path.join(tmp_dir, uploaded.name)
            with open(input_path, "wb") as f:
                f.write(uploaded.getbuffer())

            selected_profiles = [p for p in DEFAULT_PROFILES if p.label in profile_labels]
            manifest = prepare_assets(
                input_path, tmp_dir, name=name,
                profiles=selected_profiles, formats=formats or ["jpg"],
            )

        st.success(f"{len(manifest['assets'])} assets générés.")
        st.json(manifest, expanded=False)

        # Empaquetage en zip pour téléchargement en un clic
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for asset in manifest["assets"]:
                asset_path = os.path.join(tmp_dir, asset["file"])
                zf.write(asset_path, arcname=asset["file"])
            manifest_path = os.path.join(tmp_dir, f"{name}_manifest.json")
            zf.write(manifest_path, arcname=f"{name}_manifest.json")
        zip_buffer.seek(0)

        st.download_button(
            "Télécharger les assets (.zip)",
            data=zip_buffer,
            file_name=f"{name}_assets_360.zip",
            mime="application/zip",
        )
