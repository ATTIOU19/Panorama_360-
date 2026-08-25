"""
============================================================================
 APP STREAMLIT — Rendu 360° (Bloc 1 & Bloc 2)
============================================================================
Point d'entrée pour un déploiement sur Streamlit Community Cloud.

Streamlit ne sert pas de fichiers HTML statiques directement : cette app
embarque panorama_viewer.html via st.components.v1.html (rendu dans un
iframe), enchaîne automatiquement le pipeline de stitching (Bloc 1) sur des
photos uploadées pour afficher directement le panorama résultant, et expose
la préparation d'assets (asset_prep.py) comme formulaire dédié.

Structure de repo attendue (à la racine) :
    streamlit_app.py       <- ce fichier (point d'entrée)
    panorama_viewer.html   <- la visionneuse Three.js (Bloc 2)
    asset_prep.py          <- la génération d'assets optimisés (Bloc 2)
    stitching_pipeline.py  <- le pipeline de stitching (Bloc 1)
    requirements.txt

Lancement local :
    pip install -r requirements.txt
    streamlit run streamlit_app.py

Déploiement : pousser le repo sur GitHub, puis sur share.streamlit.io
choisir ce repo et streamlit_app.py comme fichier principal.
============================================================================
"""

import base64
import io
import os
import shutil
import zipfile

import cv2
import streamlit as st
import streamlit.components.v1 as components

from asset_prep import DEFAULT_PROFILES, prepare_assets
from stitching_pipeline import PipelineConfig, check_seam_continuity, run_auto_pipeline, run_manual_pipeline

st.set_page_config(page_title="Rendu 360° — Bloc 1 & 2", page_icon="🌐", layout="wide")

PAGE = st.sidebar.radio(
    "Navigation",
    ["Assembler & visualiser", "Visionneuse (panorama existant)", "Préparation des assets"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Prototype Bloc 1 (stitching) & Bloc 2 (assets WebGL / Three.js) — "
    "cf. cahier des charges Rendu 360°."
)

HTML_PATH = os.path.join(os.path.dirname(__file__), "panorama_viewer.html")


def render_viewer(auto_panorama_path: str = None, auto_panorama_name: str = "panorama", height: int = 820):
    """
    Affiche la visionneuse panorama_viewer.html.
    Si auto_panorama_path est fourni, injecte ce panorama pour un chargement
    et une activation automatiques au démarrage (pas d'action manuelle requise).
    """
    if not os.path.exists(HTML_PATH):
        st.error(f"Fichier introuvable : {HTML_PATH}. Vérifiez qu'il est bien à la racine du repo.")
        return

    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    if auto_panorama_path:
        with open(auto_panorama_path, "rb") as img_f:
            b64 = base64.b64encode(img_f.read()).decode("ascii")
        ext = os.path.splitext(auto_panorama_path)[1].lstrip(".").lower() or "jpg"
        mime = "image/png" if ext == "png" else "image/jpeg"
        data_url = f"data:{mime};base64,{b64}"
        inject = (
            "<script>window.__AUTO_PANORAMA__ = {dataURL: \"" + data_url + "\", "
            "name: \"" + auto_panorama_name.replace('"', "") + "\"};</script>"
        )
        html = html.replace("<!-- AUTO_LOAD_PLACEHOLDER -->", inject, 1)

    components.html(html, height=height, scrolling=False)


# ============================================================================
# Page 1 — Assembler & visualiser (Bloc 1 -> Bloc 2 enchaînés)
# ============================================================================
if PAGE == "Assembler & visualiser":
    st.title("Assembler des photos en panorama 360°")
    st.caption(
        "Uploadez vos photos avec chevauchement (~20-30% entre prises consécutives) : "
        "le pipeline de stitching (Bloc 1) les assemble, puis le panorama obtenu "
        "s'affiche automatiquement dans la visionneuse ci-dessous (Bloc 2)."
    )

    uploaded_files = st.file_uploader(
        "Photos sources (ordre de prise de vue = ordre alphabétique des noms)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        mode = st.selectbox("Mode du pipeline", ["auto", "manual"], help="auto = cv2.Stitcher (rapide) ; manual = pas-à-pas, plus robuste sur un 360° complet")
    with col2:
        resolution = st.selectbox("Résolution de sortie", ["2048×1024 (rapide)", "4096×2048 (standard)"])
        out_w, out_h = (2048, 1024) if "2048" in resolution else (4096, 2048)
    with col3:
        blend = st.selectbox("Blending (mode manual uniquement)", ["multiband", "feather"])

    run_clicked = st.button(
        "Assembler et afficher",
        type="primary",
        disabled=not uploaded_files or len(uploaded_files) < 2,
    )
    if uploaded_files and len(uploaded_files) < 2:
        st.info("Au moins 2 photos sont nécessaires pour l'assemblage.")

    if run_clicked:
        tmp_input_dir = "/tmp/stitch_input"
        tmp_output_path = "/tmp/stitch_output/panorama_assemble.jpg"
        if os.path.exists(tmp_input_dir):
            shutil.rmtree(tmp_input_dir)
        os.makedirs(tmp_input_dir, exist_ok=True)
        os.makedirs(os.path.dirname(tmp_output_path), exist_ok=True)

        for f in uploaded_files:
            with open(os.path.join(tmp_input_dir, f.name), "wb") as out_f:
                out_f.write(f.getbuffer())

        cfg = PipelineConfig(blend_mode=blend, output_width=out_w, output_height=out_h)

        with st.spinner(f"Assemblage en cours (mode {mode})…"):
            if mode == "auto":
                ok = run_auto_pipeline(tmp_input_dir, tmp_output_path, cfg)
            else:
                ok = run_manual_pipeline(tmp_input_dir, tmp_output_path, cfg)

        if not ok or not os.path.exists(tmp_output_path):
            st.error(
                "Échec de l'assemblage. Causes fréquentes : chevauchement insuffisant "
                "entre les photos, ou photos trop peu texturées pour la détection de "
                "points d'intérêt. Essayez le mode 'manual' si 'auto' a échoué."
            )
        else:
            panorama = cv2.imread(tmp_output_path)
            score = check_seam_continuity(panorama) if panorama is not None else None

            st.success("Panorama assemblé avec succès.")
            if score is not None:
                st.metric("Score de continuité de jonction 0°/360°", f"{score:.3f}", help="1.0 = parfait")

            with open(tmp_output_path, "rb") as f:
                st.download_button(
                    "Télécharger le panorama (.jpg)",
                    data=f,
                    file_name="panorama_assemble.jpg",
                    mime="image/jpeg",
                )

            st.subheader("Visionneuse")
            render_viewer(auto_panorama_path=tmp_output_path, auto_panorama_name="panorama_assemble")

# ============================================================================
# Page 2 — Visionneuse manuelle (panorama déjà existant)
# ============================================================================
elif PAGE == "Visionneuse (panorama existant)":
    st.title("Visionneuse panoramique 360°")
    st.caption(
        "Chargez un ou plusieurs panoramas équirectangulaires déjà assemblés "
        "directement dans la visionneuse (glisser-déposer ou bouton dédié). "
        "Le mode édition permet de créer des hotspots de navigation entre scènes."
    )
    render_viewer()

# ============================================================================
# Page 3 — Préparation des assets (upload -> génération -> téléchargement)
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
