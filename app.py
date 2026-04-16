"""
app.py — Interface Streamlit Slothia v2
=======================================
CHANGES v2:
  - Tab 3 Compositeur entièrement réécrit (suppression, réécriture propre)
  - "Écosystèmes" → "Mon Jardin" : plantes enregistrées avec emplacement / exposition / notes
  - Filtres & Suggestions : reset total de l'état fiche à chaque changement de plante
  - Tab 2 Demander : placeholder "Demander à Slothia…" + fiches cliquables dans le chat
  - Améliorations visuelles CSS (cards, tags, chat bubbles, animations)
"""

import streamlit as st
import time
import streamlit.components.v1 as components
import copy
import re
import requests as _requests

from ia import get_or_create_fiche, ask_plant, identify_photo, groq_chat, groq_chat_admin, groq_vision_chat, _clean_history, ADMIN_KEYWORD
from memory import search_db, get_db_stats, get_qa_summary, contains_alert, purge_corrupted_fiches, repair_nom_commun_from_description
from associations import (
    GARDEN_FILTERS, DISEASE_CATS, SOIL_SYMPTOMS,
    suggest_plants, check_compatibility,
    diagnose_problem, diagnose_soil,
    chat_associations,
)
from sloth import render_sloth, get_current_season

# ── Config ─────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Slothia", page_icon="🌿", layout="centered")

# ── Nettoyage DB au démarrage (une seule fois par session) ─────────────────────
if "db_purged" not in st.session_state:
    _n = purge_corrupted_fiches()
    if _n:
        print(f"[STARTUP] {_n} fiche(s) corrompue(s) réparée(s) en DB")
    st.session_state.db_purged = True

# Repair à chaque rerun (léger, corrige les noms comme "Saucisse" → "Sauge")
_r = repair_nom_commun_from_description()
if _r:
    print(f"[REPAIR] {_r} nom(s) commun(s) corrigé(s)")

# ── Nettoyage plant_history : supprimer les non-plantes ─────────────────────────
_NON_PLANTES_SIDEBAR = {
    "saucisse","saucisson","viande","poulet","poisson","fromage","beurre","lait",
    "sel","poivre","sucre","farine","huile","eau","vin","bière","café","thé",
    "insecte","abeille","papillon","ver","lombric","mulch","compost","engrais",
    "pierre","gravier","sable","pot","jardin","soleil","ombre","pluie",
}
if "plant_history" in st.session_state:
    st.session_state["plant_history"] = [
        p for p in st.session_state["plant_history"]
        if p.get("nom","").lower() not in _NON_PLANTES_SIDEBAR
        and len(p.get("nom","")) > 2
    ]

# ── CSS AMÉLIORÉ ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lora:wght@500;600&family=DM+Sans:wght@300;400;500;600&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background: #1a2d1a;
    color: #ddeedd;
}
.stApp { background: #1a2d1a; }

/* ── Typographie ── */
h1 {
    font-family: 'Lora', serif !important;
    color: #7dca7d !important;
    letter-spacing: -0.5px !important;
}
h2, h3, h4 { color: #6dba6d !important; font-weight: 600 !important; }
p, li, .stMarkdown p { color: #ddeedd !important; }
label { color: #c8e0c8 !important; font-weight: 500 !important; }

/* ── Boutons ── */
.stButton > button {
    background: linear-gradient(135deg, #243824, #2a3f2a) !important;
    color: #c8e0c8 !important;
    border: 1px solid #4a7a4a !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.18s ease !important;
    white-space: nowrap !important;
    letter-spacing: 0.3px !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #3a6a3a, #4a7a4a) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 14px rgba(109, 186, 109, 0.22) !important;
    border-color: #6dba6d !important;
    color: #eaf2ea !important;
}
[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #0e2a0e, #163216) !important;
    color: #7dda7d !important;
    border: 2px solid #6dba6d !important;
    box-shadow: 0 0 12px rgba(109, 186, 109, 0.28) !important;
}
[data-testid="baseButton-primary"]:hover {
    background: linear-gradient(135deg, #142d14, #1d3d1d) !important;
    box-shadow: 0 0 20px rgba(109, 186, 109, 0.45) !important;
}

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: #243824 !important;
    border: 1px solid #4a7a4a !important;
    color: #eaf2ea !important;
    border-radius: 10px !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #6dba6d !important;
    box-shadow: 0 0 0 2px rgba(109, 186, 109, 0.18) !important;
}
.stSelectbox > div > div {
    background: #243824 !important;
    border: 1px solid #4a7a4a !important;
    color: #eaf2ea !important;
    border-radius: 10px !important;
}
.stRadio > div { gap: 6px !important; }
.stRadio label { color: #c8e0c8 !important; }
.stFileUploader {
    background: #243824;
    border: 2px dashed #4a7a4a;
    border-radius: 14px;
    padding: 10px;
    transition: border-color 0.2s, background 0.2s;
}
.stFileUploader:hover { border-color: #6dba6d; background: #2a3f2a; }
.stCheckbox label p { color: #c8e0c8 !important; }

/* ── Cards ── */
.card {
    background: linear-gradient(150deg, #263c26 0%, #2a3f2a 100%);
    border: 1px solid #4a7a4a;
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 12px;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(109,186,109,0.08);
    transition: box-shadow 0.2s, transform 0.15s;
}
.card:hover { box-shadow: 0 6px 22px rgba(0,0,0,0.38), 0 0 0 1px rgba(109,186,109,0.18); }
.row { font-size: 13px; line-height: 1.85; margin-bottom: 5px; color: #c8e0c8; }
.lbl { color: #8ecf8e; font-weight: 600; }

/* ── Tags ── */
.tag {
    background: rgba(109,186,109,0.14);
    border: 1px solid rgba(109,186,109,0.42);
    color: #90e090;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 12px;
    margin: 2px;
    display: inline-block;
    font-weight: 500;
    transition: background 0.15s;
}
.tag:hover { background: rgba(109,186,109,0.24); }
.tag-red {
    background: rgba(220,100,100,0.13);
    border: 1px solid rgba(220,100,100,0.42);
    color: #f09090;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 12px;
    margin: 2px;
    display: inline-block;
    font-weight: 500;
}
.tag-gold {
    background: rgba(210,180,70,0.12);
    border: 1px solid rgba(210,180,70,0.42);
    color: #ddc060;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 12px;
    margin: 2px;
    display: inline-block;
    font-weight: 500;
}

/* ── Chat ── */
.chat-user {
    background: rgba(61,122,61,0.28);
    border: 1px solid rgba(109,186,109,0.32);
    border-radius: 14px 14px 4px 14px;
    padding: 10px 15px;
    margin: 7px 0;
    margin-left: 18%;
    font-size: 14px;
    line-height: 1.7;
    color: #eaf2ea;
}
.chat-bot {
    background: linear-gradient(135deg, #263c26, #2a3f2a);
    border: 1px solid #4a7a4a;
    border-radius: 14px 14px 14px 4px;
    padding: 10px 15px;
    margin: 7px 0;
    margin-right: 8%;
    font-size: 14px;
    line-height: 1.7;
    color: #ddeedd;
    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
}

/* ── Alertes ── */
.alert-box {
    background: rgba(200,80,80,0.12);
    border: 1px solid rgba(200,80,80,0.42);
    border-radius: 12px;
    padding: 10px 15px;
    color: #f09090;
    font-size: 13px;
    line-height: 1.6;
    margin: 7px 0;
}
.ok-box {
    background: rgba(109,186,109,0.11);
    border: 1px solid rgba(109,186,109,0.38);
    border-radius: 10px;
    padding: 7px 13px;
    font-size: 12px;
    color: #90e090;
    margin-bottom: 8px;
}
.warn-box {
    background: rgba(210,175,60,0.10);
    border: 1px solid rgba(210,175,60,0.38);
    border-radius: 10px;
    padding: 7px 13px;
    font-size: 12px;
    color: #ddc060;
    margin-bottom: 8px;
}

/* ── Badges Jardin ── */
.badge-terre {
    background: rgba(160,120,60,0.18);
    border: 1px solid rgba(160,120,60,0.48);
    color: #c8a870;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
}
.badge-pot {
    background: rgba(80,140,200,0.14);
    border: 1px solid rgba(80,140,200,0.42);
    color: #80b8e8;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
}
.badge-expo {
    background: rgba(220,180,60,0.11);
    border: 1px solid rgba(220,180,60,0.38);
    color: #d4c060;
    padding: 2px 9px;
    border-radius: 20px;
    font-size: 11px;
}

/* ── Section headers ── */
.sec-hdr {
    font-size: 10px;
    color: #9ac89a;
    text-transform: uppercase;
    letter-spacing: 1.6px;
    margin: 14px 0 7px;
    font-weight: 600;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #162616 !important;
    border-right: 1px solid #3a5a3a !important;
}

/* ── Onglets ── */
.stTabs [data-baseweb="tab-list"] {
    background: #243824 !important;
    border-radius: 12px !important;
    border: 1px solid #4a7a4a !important;
    padding: 3px !important;
}
.stTabs [data-baseweb="tab"] {
    color: #9ac89a !important;
    font-weight: 500 !important;
    border-radius: 9px !important;
    transition: all 0.15s !important;
}
.stTabs [aria-selected="true"] {
    color: #7dda7d !important;
    background: rgba(109,186,109,0.14) !important;
    font-weight: 600 !important;
}

/* ── Expander ── */
details summary p { color: #c8e0c8 !important; }
.streamlit-expanderHeader p { color: #c8e0c8 !important; }
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────────
for k, v in {
    "sloth_pose":    "wave",
    "sloth_tenue":   get_current_season(),
    "sloth_msg":     "Bonjour ! 🌿",
    "filters":       [],
    "existing_plants": [],
    "msgs_libre": [{"role":"assistant","content":"🌿 Demander à Slothia…\nPose-moi n'importe quelle question sur les plantes, les associations, les maladies, les écosystèmes !"}],
    "jardin":        [],    # Mon Jardin — liste de dicts {nom, nom_latin, emplacement, exposition, notes}
    "fiche_version": 0,     # incrémenté à chaque nouvelle fiche Compositeur → force les widgets à se réinitialiser
    "_admin_mode":   False, # Mode créateur — activé par le mot-clé secret
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


def set_sloth(pose: str, msg: str = None, tenue: str = None):
    st.session_state.sloth_pose = pose
    if msg:   st.session_state.sloth_msg   = msg
    if tenue: st.session_state.sloth_tenue = tenue


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
def _vider_fiches():
    """Vide les états fiche. Appelé dans les callbacks (avant rerun)."""
    for _k in ["fiche_composer", "fiche_composer_cache", "active_plant",
               "fiche_id", "fiche_id_cache", "msgs_id", "msgs_compare",
               "_modal_fiche", "_modal_cache", "_open_modal"]:
        st.session_state.pop(_k, None)
    for _k in list(st.session_state.keys()):
        if _k.startswith(("_wthumb_", "msgs_comp_v", "form_comp_v", "msgs_id_")):
            del st.session_state[_k]
    st.session_state.fiche_version = st.session_state.get("fiche_version", 0) + 1


def _cb_fermer_fiche():
    """on_click : ferme la fiche."""
    _vider_fiches()


def _cb_ouvrir_fiche(nom: str, latin: str, target: str = "modal", idx: int = 0):
    """
    on_click : mémorise la plante à ouvrir.
    target='modal'   → modale sidebar (tous les onglets)
    target='composer' → fiche inline dans le Composer
    """
    _vider_fiches()
    st.session_state["_pending_fiche"] = {
        "nom": nom, "latin": latin, "target": target, "idx": idx
    }


# ── Chargement de fiche (avant les tabs) ──────────────────────────────────────
if "_pending_fiche" in st.session_state:
    _pf     = st.session_state.pop("_pending_fiche")
    _pf_nom = _pf["nom"]
    _pf_lat = _pf["latin"]
    _pf_tgt = _pf["target"]

    set_sloth("thinking", f"{_pf_nom}… 📚")
    with st.spinner(f"🌿 Chargement de {_pf_nom}…"):
        _pf_fc, _pf_frm = get_or_create_fiche(_pf_nom, _pf_lat)
    _pf_fc = copy.deepcopy(_pf_fc)

    is_aqu = _pf_fc.get("categorie", "") in ["aquatique", "semi_aquatique"]
    set_sloth("talking", "Fiche prête ! 🌿", "aquatique" if is_aqu else get_current_season())

    # Tous les cas → modale
    st.session_state["_modal_fiche"] = _pf_fc
    st.session_state["_modal_cache"] = _pf_frm
    st.session_state["_open_modal"]  = True
    # Alimenter l'historique sidebar
    _pl_new = {"nom": _pf_nom, "latin": _pf_lat}
    _hist = st.session_state.get("plant_history", [])
    _hist = [h for h in _hist if h["nom"].lower() != _pf_nom.lower()]
    st.session_state["plant_history"] = [_pl_new] + _hist[:9]

with st.sidebar:
    components.html(
        render_sloth(
            tenue   = st.session_state.sloth_tenue,
            pose    = st.session_state.sloth_pose,
            message = st.session_state.sloth_msg,
            height  = 250
        ),
        height=270, scrolling=False
    )
    st.markdown("<hr style='border-color:#3a5a3a;margin:6px 0'>", unsafe_allow_html=True)

    _stats = get_db_stats()
    st.markdown(
        f"<div style='text-align:center;font-size:12px;color:#6dba6d;font-weight:600'>"
        f"🌿 {_stats['total']} plante{'s' if _stats['total'] > 1 else ''} en base</div>",
        unsafe_allow_html=True
    )
    # ── Liste des plantes consultées ──────────────────────────────
    _history = st.session_state.get("plant_history", [])
    if _history:
        st.markdown(
            "<div style='font-size:11px;color:#6dba6d;margin:10px 0 4px;"
            "text-transform:uppercase;letter-spacing:1px'>📋 Fiches consultées</div>",
            unsafe_allow_html=True
        )
        for _hi, _pl in enumerate(_history):
            st.button(
                f"🌿 {_pl['nom']}",
                key=f"sidebar_hist_{_hi}",
                use_container_width=True,
                type="primary" if _hi == 0 else "secondary",
                on_click=_cb_ouvrir_fiche,
                kwargs={"nom": _pl["nom"], "latin": _pl.get("latin", _pl["nom"]), "target": "modal"},
            )




# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<h1 style='text-align:center;margin-bottom:0'>🌿 Slothia</h1>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center;color:#9ac89a;font-size:10px;letter-spacing:2.5px;"
    "text-transform:uppercase;margin-top:2px'>"
    "Base de connaissance vivante · Identifier · Question · Jardin · Base</p>",
    unsafe_allow_html=True
)
st.markdown("<hr style='border-color:#3a5a3a;margin:10px 0 14px'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# CALLBACKS + CHARGEMENT DE FICHE
# ══════════════════════════════════════════════════════════════════════════════
#
# ORDRE CRITIQUE : _pending_fiche doit être vérifié AVANT st.tabs().
# Si st.tabs() est appelé d'abord, Streamlit enregistre le widget et peut
# afficher l'ancienne fiche avant que st.rerun() ne soit atteint.
#
# FLUX :
#   Clic bouton → on_click s'exécute (AVANT rerun) :
#     _vider_fiches() : state vide immédiatement
#     _pending_fiche  : mémorise nom/latin/target
#
#   Rerun 1 :
#     → _pending_fiche détecté ICI avant st.tabs()
#     → page de chargement dédiée (pas de tabs, pas d'ancienne fiche)
#     → time.sleep(0.4) : cycle visuel propre garanti
#     → get_or_create_fiche() avec spinner
#     → stocke nouvelle fiche
#     → st.rerun()
#
#   Rerun 2 :
#     → _pending_fiche absent → st.tabs() s'affiche normalement
#     → nouvelle fiche proprement ✓

# ── Création des tabs ────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📷 Identifier","💬 Question","🌿 Jardin","🗄️ Base"])


# ══════════════════════════════════════════════════════════════════════════════
# COMPOSANTS RÉUTILISABLES
# ══════════════════════════════════════════════════════════════════════════════

def _get_wiki_thumb(query: str, fallback: str = None) -> str | None:
    """
    Cascade photo autonome : Wikipedia FR → Wikipedia EN → Wikimedia Commons.
    Résultats mis en cache dans session_state.
    """
    cache_key = f"_wthumb_{query}|{fallback}"
    if cache_key in st.session_state:
        return st.session_state[cache_key] or None

    headers = {"Accept": "application/json", "User-Agent": "Slothia/1.0"}

    def _wiki_summary_img(lang: str, q: str) -> str:
        try:
            r = _requests.get(
                f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{q.replace(' ','_')}",
                headers=headers, timeout=6
            )
            if r.status_code == 200:
                d = r.json()
                return (d.get("thumbnail") or {}).get("source") or \
                       (d.get("originalimage") or {}).get("source") or ""
        except Exception:
            pass
        return ""

    queries = [q for q in [query, fallback] if q]
    url = ""

    for lang in ("fr", "en"):
        for q in queries:
            url = _wiki_summary_img(lang, q)
            if url:
                break
        if url:
            break

    if not url:
        nom_latin = fallback or query
        try:
            r = _requests.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query", "generator": "search",
                    "gsrnamespace": "6", "gsrsearch": nom_latin,
                    "gsrlimit": "5", "prop": "imageinfo",
                    "iiprop": "url|mime|thumburl", "iiurlwidth": "300",
                    "format": "json",
                },
                headers=headers, timeout=8
            )
            if r.status_code == 200:
                for page in r.json().get("query", {}).get("pages", {}).values():
                    info = page.get("imageinfo", [{}])[0]
                    mime = info.get("mime", "")
                    if mime.startswith("image/") and "svg" not in mime:
                        url = info.get("thumburl") or info.get("url", "")
                        if url:
                            break
        except Exception:
            pass

    st.session_state[cache_key] = url or ""
    return url or None


def render_fiche(fiche: dict, from_cache: bool = None):
    """Affiche la fiche complète d'une plante."""
    if from_cache is True:
        st.markdown('<div class="ok-box">⚡ Fiche depuis la base locale</div>', unsafe_allow_html=True)
    elif from_cache is False:
        st.markdown('<div class="warn-box">🧠 Nouvelle fiche générée (Wikipedia → Groq) et sauvegardée</div>', unsafe_allow_html=True)

    wiki_img = fiche.get("wiki", {}).get("image", "")
    if wiki_img:
        col_img, _ = st.columns([1, 3])
        with col_img:
            st.image(wiki_img, use_container_width=True)

    conf_html = ""
    if fiche.get("confiance"):
        c = {"élevée":"#6dba6d","moyenne":"#c8a84b","faible":"#c86060"}.get(fiche["confiance"],"#9ac89a")
        score_txt = f"({fiche.get('score')}%)" if fiche.get("score") else ""
        conf_html = f'<span style="color:{c};font-size:11px;font-weight:600">{fiche["confiance"]} {score_txt}</span>'

    fields = [
        ("📖", "Description",      "description"),
        ("🌍", "Origine",          "origine_naturelle"),
        ("🌿", "Écosystème",       "ecosysteme_naturel"),
        ("☀️", "Exposition",       "exposition"),
        ("🪨", "Sol",              "sol_type"),
        ("🌱", "Terreau",          "terreau_recommande"),
        ("💧", "Arrosage",         "arrosage_frequence"),
        ("❄️", "Résistance froid", "resistance_froid"),
        ("📏", "Hauteur",          "hauteur_adulte"),
        ("⚡", "Croissance",       "croissance"),
        ("✂️", "Taille",           "taille"),
        ("🌸", "Floraison",        "floraison"),
        ("🦋", "Biodiversité",     "biodiversite"),
        ("🐝", "Insectes",         "insectes_attires"),
        ("🐦", "Oiseaux",          "oiseaux_attires"),
        ("🩺", "Maladies",         "maladies_courantes"),
        ("🪴", "Plantation",       "conseil_plantation"),
        ("☢️", "Toxique",          "toxique_adulte"),
    ]

    def _field_val(v):
        if isinstance(v, list):
            return ", ".join(str(x) for x in v if x)
        return str(v) if v else ""

    rows = "".join(
        f'<div class="row"><span class="lbl">{ico} {label} :</span> {_field_val(fiche.get(field, ""))}</div>'
        for ico, label, field in fields
        if fiche.get(field)
    )

    st.markdown(f"""<div class="card">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
    <div>
      <div style="font-size:21px;font-weight:700;color:#eaf2ea">{fiche.get('nom_commun','')}</div>
      <div style="font-size:12px;color:#9ac89a;font-style:italic;margin-top:2px">{fiche.get('nom_latin','')} · {fiche.get('famille','')}</div>
      <div style="font-size:10px;color:#6dba6d;margin-top:3px;text-transform:uppercase;letter-spacing:1px">{fiche.get('categorie','').upper()} / {fiche.get('sous_categorie','')}</div>
    </div>
    <div style="margin-left:12px">{conf_html}</div>
  </div>
  {rows}
</div>""", unsafe_allow_html=True)

    wiki = fiche.get("wiki", {})
    if wiki.get("url"):
        st.markdown(
            f'<div style="font-size:11px;margin-bottom:5px">📖 <a href="{wiki["url"]}" target="_blank" style="color:#6dba6d">{wiki.get("titre","Wikipedia")}</a></div>',
            unsafe_allow_html=True
        )
    if fiche.get("toxicite_wiki"):
        st.markdown(f'<div class="alert-box">⚠️ Wikipedia : {fiche["toxicite_wiki"]}</div>', unsafe_allow_html=True)

    for label, key, css in [
        ("🤝 Associations",      "associations_benefiques",    "tag"),
        ("⚠️ Incompatibilités",  "associations_incompatibles", "tag-red"),
        ("🌿 Même écosystème",   "plantes_meme_ecosysteme",    "tag-gold"),
    ]:
        items = fiche.get(key, [])
        if items:
            tags = "".join(f'<span class="{css}">{p}</span>' for p in items)
            st.markdown(
                f'<div style="margin:6px 0"><span style="color:#c8e0c8;font-weight:600">{label} :</span> {tags}</div>',
                unsafe_allow_html=True
            )


# ── Dialog modale (s'affiche par-dessus n'importe quel onglet) ────────────────
def _show_fiche_modal():
    fiche = st.session_state.get("_modal_fiche", {})
    from_cache = st.session_state.get("_modal_cache")
    if not fiche:
        st.warning("Aucune fiche chargée.")
        return
    render_fiche(fiche, from_cache)
    st.markdown("---")
    if st.button("✕ Fermer", type="secondary"):
        st.session_state.pop("_modal_fiche", None)
        st.session_state.pop("_modal_cache", None)
        st.rerun()


@st.dialog("📋 Fiche plante", width="large")
def _show_fiche_modal():
    fiche = st.session_state.get("_modal_fiche", {})
    from_cache = st.session_state.get("_modal_cache")
    if not fiche:
        st.warning("Aucune fiche chargée.")
        return
    render_fiche(fiche, from_cache)
    st.markdown("---")
    if st.button("✕ Fermer", type="secondary"):
        st.session_state.pop("_modal_fiche", None)
        st.session_state.pop("_modal_cache", None)
        st.rerun()


def _render_msg(m: dict, idx: int = 0):
    """Affiche un message chat (user ou bot)."""
    content = m["content"]
    if m["role"] == "user":
        st.markdown(f'<div class="chat-user">{content}</div>', unsafe_allow_html=True)
    else:
        if m.get("is_alert"):
            st.markdown(f'<div class="alert-box">{content}</div>', unsafe_allow_html=True)
        else:
            html = content.replace("\n", "<br>")
            html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
            lines = html.split("<br>")
            out, in_list = [], False
            for line in lines:
                s = line.strip()
                if s.startswith("- ") or s.startswith("• "):
                    if not in_list:
                        out.append("<ul style='margin:4px 0;padding-left:18px'>")
                        in_list = True
                    out.append(f"<li style='color:#ddeedd'>{s[2:]}</li>")
                else:
                    if in_list:
                        out.append("</ul>")
                        in_list = False
                    out.append(line)
            if in_list:
                out.append("</ul>")
            st.markdown(f'<div class="chat-bot">{"<br>".join(out)}</div>', unsafe_allow_html=True)

    if m.get("from_cache"):
        st.markdown('<div style="font-size:10px;color:#4a9a4a;margin-left:4px">⚡ mémorisé</div>',
                    unsafe_allow_html=True)


def render_chat(key: str, on_send, placeholder: str = "Pose ta question…"):
    """Chat avec form + clear_on_submit=True."""
    msgs = st.session_state.get(f"msgs_{key}", [])
    for i, m in enumerate(msgs):
        _render_msg(m, i)

    with st.form(key=f"form_{key}", clear_on_submit=True):
        c1, c2 = st.columns([5, 1])
        with c1:
            q = st.text_input("Question", placeholder=placeholder,
                              label_visibility="collapsed")
        with c2:
            submitted = st.form_submit_button("→")

    if submitted and q and q.strip():
        on_send(q.strip(), list(msgs))
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — IDENTIFIER
# ══════════════════════════════════════════════════════════════════════════════
# ── Ouvrir la modale si demandé (toutes les fonctions sont définies ici) ────────
if st.session_state.get("_open_modal") and st.session_state.get("_modal_fiche"):
    st.session_state.pop("_open_modal", None)
    _show_fiche_modal()


with tab1:
    _id_col1, _id_col2 = st.columns(2)
    with _id_col1:
        uploaded = st.file_uploader("📁 Depuis la galerie", type=["jpg","jpeg","png","webp"])
    with _id_col2:
        captured = st.camera_input("📷 Prendre une photo")

    _id_source = captured or uploaded
    if _id_source:
        img = _id_source.read()
        st.image(img, width=300)
        if st.button("🔍 Identifier cette plante"):
            set_sloth("thinking", "Je cherche… 🔍")
            with st.spinner("PlantNet — identification en cours…"):
                candidats, err = identify_photo(img)
            if err:
                set_sloth("surprised", err)
                st.error(err)
            else:
                set_sloth("wave", "C'est laquelle ? 🌿")
                st.session_state.candidats_plantnet = candidats
                st.session_state.pop("fiche_id", None)
                st.session_state.pop("msgs_id", None)

    if "candidats_plantnet" in st.session_state and "fiche_id" not in st.session_state:
        candidats = st.session_state.candidats_plantnet
        st.markdown("### 🔎 Quelle plante est-ce ?")
        st.markdown("<div style='font-size:13px;color:#9ac89a;margin-bottom:10px'>PlantNet a trouvé plusieurs résultats. Clique sur la bonne plante :</div>", unsafe_allow_html=True)

        for i, c in enumerate(candidats):
            col_color = {"élevée": "#6dba6d", "moyenne": "#c8a84b", "faible": "#f09090"}.get(c["confiance"], "#9ac89a")
            warn      = c["score"] < 50
            _nom_c    = c["nom_commun"]
            _nom_l    = c["nom_latin"]
            _score    = c["score"]
            _conf     = c["confiance"]
            _famille  = c["famille"]
            warn_str  = "\u26a0\ufe0f score faible" if warn else ""

            # Carte : st.columns pour image/texte (évite base64 dans markdown)
            st.markdown("<div class='card' style='margin-bottom:6px;padding:10px 12px'>",
                        unsafe_allow_html=True)
            col_img, col_txt = st.columns([1, 3])
            with col_img:
                if c.get("photo_bytes"):
                    st.image(c["photo_bytes"], use_container_width=True)
                else:
                    st.markdown(
                        "<div style='height:90px;background:#1c3a1c;border-radius:8px;"
                        "display:flex;align-items:center;justify-content:center;font-size:30px'>\U0001f33f</div>",
                        unsafe_allow_html=True)
            with col_txt:
                st.markdown(
                    f"<div style='font-size:17px;font-weight:700;color:#eaf2ea'>{_nom_c}</div>"
                    f"<div style='font-size:12px;color:#9ac89a;font-style:italic'>{_nom_l}</div>"
                    f"<div style='margin-top:4px'><span style='color:{col_color};font-size:13px;"
                    f"font-weight:600'>{_score}% — {_conf}</span>"
                    f"<span style='color:#f09090;font-size:11px;margin-left:8px'>{warn_str}</span></div>"
                    f"<div style='font-size:11px;color:#6dba6d;margin-top:2px'>Famille : {_famille}</div>",
                    unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            if st.button(f"✅ C'est {c['nom_commun']}", key=f"pick_plantnet_{i}"):
                set_sloth("thinking", "Wikipedia puis Groq… 📚")
                with st.spinner(f"Construction de la fiche pour {c['nom_commun']}…"):
                    fiche, from_cache = get_or_create_fiche(c["nom_commun"], c["nom_latin"])
                    fiche = copy.deepcopy(fiche)
                    fiche["score"]     = c["score"]
                    fiche["confiance"] = c["confiance"]
                is_tox    = bool(fiche.get("toxicite_wiki"))
                is_aqu    = fiche.get("categorie","") in ["aquatique","semi_aquatique"]
                new_tenue = "toxique" if is_tox else "aquatique" if is_aqu else get_current_season()
                new_pose  = "alert"   if is_tox else "excited" if not from_cache else "talking"
                new_msg   = "⚠️ TOXIQUE !" if is_tox else "Nouvelle plante ! 🌿" if not from_cache else "Je connais déjà ! ⚡"
                set_sloth(new_pose, new_msg, new_tenue)
                st.session_state.fiche_id       = fiche
                st.session_state.fiche_id_cache = from_cache
                st.session_state.pop("candidats_plantnet", None)
                st.session_state.pop("msgs_id", None)
                for _k in list(st.session_state.keys()):
                    if _k.startswith("_wthumb_"):
                        del st.session_state[_k]
                st.rerun()

        st.markdown("---")
        if st.button("❌ Aucune de ces plantes — réessayer"):
            st.session_state.pop("candidats_plantnet", None)
            st.rerun()

        st.markdown("---")
        st.markdown("**🤔 Un doute ? Décris ce que tu vois ou sens :**")
        st.caption("Ex : « les feuilles sont veloutées, ça sent le citron, les tiges sont carrées… »")

        if "msgs_compare" not in st.session_state:
            candidats_txt = ", ".join(
                f"{c['nom_commun']} ({c['nom_latin']}, {c['score']}%)"
                for c in st.session_state.candidats_plantnet
            )
            st.session_state.msgs_compare = [{
                "role": "assistant",
                "content": f"PlantNet hésite entre : {candidats_txt}. Décris-moi la plante — couleur, texture des feuilles, odeur, forme des tiges, fleurs… Je vais t'aider à trancher !"
            }]

        def send_compare(q, msgs):
            candidats_ctx = "\n".join(
                f"- {c['nom_commun']} ({c['nom_latin']}) : {c['score']}%"
                for c in st.session_state.candidats_plantnet
            )
            msgs.append({"role": "user", "content": q})
            set_sloth("thinking", "J'analyse ta description… 🔍")
            system_compare = f"""Tu es botaniste expert. PlantNet a proposé ces candidats :
{candidats_ctx}

L'utilisateur va décrire ce qu'il voit et sent. Tu dois :
1. Analyser sa description et comparer aux caractéristiques de chaque candidat
2. Dire lequel correspond le mieux et POURQUOI (critères précis)
3. Poser UNE question ciblée si tu as encore besoin d'un détail pour trancher
Sois direct et concis. Ne répète pas les noms scientifiques à chaque phrase."""
            with st.spinner("🌿"):
                from ia import _groq, _clean_history
                rep = _groq(_clean_history(msgs), system_compare, temp=0.3, max_t=400)
            msgs.append({"role": "assistant", "content": rep})
            set_sloth("talking", "Voilà mon analyse ! 🌿")
            st.session_state.msgs_compare = msgs

        render_chat("compare", send_compare, "Décris les feuilles, l'odeur, la tige…")

    if "fiche_id" in st.session_state:
        fiche = st.session_state.fiche_id
        render_fiche(fiche, st.session_state.get("fiche_id_cache"))
        qa = get_qa_summary(fiche)
        if qa["total"]:
            al = f" · ⚠️ {qa['alertes']} alerte(s)" if qa["alertes"] else ""
            st.markdown(f'<div class="ok-box">📚 {qa["total"]} Q&A mémorisée(s){al}</div>', unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("**💬 Question sur cette plante ?**")
        if "msgs_id" not in st.session_state:
            st.session_state.msgs_id = []

        def send_id(q, msgs):
            msgs.append({"role": "user", "content": q})
            set_sloth("thinking", "Je cherche… 🤔")
            with st.spinner("🌿"):
                ans, cached = ask_plant(fiche, q, _clean_history(msgs))
            is_al = contains_alert(ans)
            set_sloth(
                "alert" if is_al else "talking",
                "⚠️ Attention !" if is_al else "Voilà ! 😊",
                "toxique" if is_al else st.session_state.sloth_tenue
            )
            msgs.append({"role": "assistant", "content": ans, "from_cache": cached, "is_alert": is_al})
            st.session_state.msgs_id = msgs

        render_chat("id", send_id, f"Ex : est-ce que {fiche.get('nom_commun','')} est toxique ?")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — QUESTION (chat unifié + photo)
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    msgs_libre = st.session_state.msgs_libre
    _is_admin  = st.session_state.get("_admin_mode", False)

    # ── Bandeau + panneau mode créateur ──────────────────────────────────────
    if _is_admin:
        st.markdown(
            "<div style='background:rgba(180,120,30,0.15);border:1px solid rgba(200,160,50,0.5);"
            "border-radius:10px;padding:6px 14px;font-size:12px;color:#d4a830;margin-bottom:8px'>"
            "🔧 <strong>Mode créateur actif</strong> — conversation libre, sans détection de plante."
            " Retape <code>akiran01</code> pour désactiver.</div>",
            unsafe_allow_html=True
        )
        # ── Requêtes non résolues ──────────────────────────────────────────────
        _unresolved = st.session_state.get("_unresolved", [])
        if _unresolved:
            with st.expander(f"⚠️ {len(_unresolved)} requête(s) potentiellement non résolue(s)", expanded=False):
                for _ur in reversed(_unresolved):
                    st.markdown(
                        f"<div style='background:rgba(200,100,50,0.1);border:1px solid rgba(200,100,50,0.3);"
                        f"border-radius:8px;padding:8px 12px;margin-bottom:6px'>"
                        f"<div style='font-size:12px;color:#e0a070;font-weight:600'>Question :</div>"
                        f"<div style='font-size:13px;color:#eaf2ea;margin:2px 0 6px'>{_ur['question']}</div>"
                        f"<div style='font-size:12px;color:#e0a070;font-weight:600'>Réponse donnée :</div>"
                        f"<div style='font-size:12px;color:#b0c8b0;font-style:italic'>{_ur['reponse'][:200]}…</div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                if st.button("🗑️ Effacer la liste", key="clear_unresolved"):
                    st.session_state["_unresolved"] = []
                    st.rerun()
        else:
            st.markdown(
                "<div style='font-size:12px;color:#6a9a6a;padding:4px 0'>✅ Aucune requête problématique détectée pour l'instant.</div>",
                unsafe_allow_html=True
            )

    # ── Affichage des messages ──
    for i, m in enumerate(msgs_libre):
        _render_msg(m, i)

    # ── Upload photo ou caméra ──
    _photo_key = f"photo_question_{st.session_state.get('_photo_counter', 0)}"
    _cam_key   = f"cam_question_{st.session_state.get('_photo_counter', 0)}"
    _pc1, _pc2 = st.columns(2)
    with _pc1:
        photo_chat = st.file_uploader(
            "📁 Galerie",
            type=["jpg","jpeg","png","webp"],
            key=_photo_key,
        )
    with _pc2:
        cam_chat = st.camera_input("📷 Caméra", key=_cam_key)

    _active_photo = cam_chat or photo_chat
    if _active_photo:
        st.image(_active_photo, width=220)

    # ── Formulaire de saisie ──
    with st.form(key="form_libre", clear_on_submit=True):
        c1, c2 = st.columns([5, 1])
        with c1:
            q_libre = st.text_input(
                "Message",
                placeholder="Demander à Slothia… Ex : comment associer les tomates au potager ?",
                label_visibility="collapsed"
            )
        with c2:
            submitted_libre = st.form_submit_button("→")

    if submitted_libre and (q_libre.strip() or _active_photo):
        msgs     = list(st.session_state.msgs_libre)
        img_bytes = _active_photo.read() if _active_photo else None
        _q       = q_libre.strip()

        # ── Détection mot-clé admin ────────────────────────────────────────────
        if ADMIN_KEYWORD in _q.lower():
            _was_admin = st.session_state.get("_admin_mode", False)
            st.session_state["_admin_mode"] = not _was_admin
            if not _was_admin:
                # Activation
                set_sloth("excited", "Mode créateur activé 🔧")
                msgs.append({"role": "assistant",
                             "content": "🔧 Bonjour créateur ! Content de te voir. Qu'est-ce qui t'amène aujourd'hui — un bug à investiguer, un retour sur mon comportement, ou juste une conversation libre ?",
                             "is_admin": True})
            else:
                # Désactivation
                set_sloth("wave", "Mode créateur désactivé 🌿")
                msgs.append({"role": "assistant",
                             "content": "🌿 Mode créateur désactivé. Je repasse en mode utilisateur normal.",
                             "is_admin": True})
            st.session_state.msgs_libre = msgs
            st.rerun()

        # ── Cas photo : analyse vision ─────────────────────────────────────────
        elif img_bytes:
            _user_content = _q if _q else "📷 *photo envoyée*"
            _hist_before  = _clean_history(msgs)
            msgs.append({"role": "user", "content": _user_content, "has_photo": True})
            set_sloth("thinking", "J'analyse la photo… 🔬")
            with st.spinner("🔬 Analyse en cours…"):
                rep = groq_vision_chat(img_bytes, _q, _hist_before)
            is_alert = contains_alert(rep)
            msgs.append({"role": "assistant", "content": rep, "is_alert": is_alert})
            set_sloth("alert" if is_alert else "talking",
                      "🚨 Attention !" if is_alert else "Voilà ce que j'observe 🔬")
            st.session_state["_photo_counter"] = st.session_state.get("_photo_counter", 0) + 1

        # ── Mode créateur actif : chat admin ──────────────────────────────────
        elif st.session_state.get("_admin_mode", False):
            msgs.append({"role": "user", "content": _q})
            set_sloth("thinking", "Je réfléchis pour mon créateur… 🔧")
            _session_info = {
                "nb_jardin":   len(st.session_state.get("jardin", [])),
                "nb_history":  len(st.session_state.get("plant_history", [])),
                "nb_msgs":     len(msgs),
                "filters":     st.session_state.get("filters", []),
                "repairs_done": getattr(st.session_state, "_repairs_done", 0),
                "purges_done":  getattr(st.session_state, "_purges_done", 0),
                "unresolved":  st.session_state.get("_unresolved", []),
            }
            with st.spinner("🔧"):
                rep = groq_chat_admin(_clean_history(msgs), _session_info)
            msgs.append({"role": "assistant", "content": rep, "is_admin": True})
            set_sloth("talking", "Rapport prêt 🔧")

        # ── Chat normal ────────────────────────────────────────────────────────
        else:
            msgs.append({"role": "user", "content": _q})
            set_sloth("thinking", "Je réfléchis… 🤔")
            with st.spinner("🌿"):
                rep, fiche_detectee = groq_chat(_clean_history(msgs))
            msg_bot = {"role": "assistant", "content": rep}
            if fiche_detectee:
                pl = {
                    "nom":   fiche_detectee.get("nom_commun", ""),
                    "latin": fiche_detectee.get("nom_latin", ""),
                }
                _pl_nom_low = pl["nom"].lower()
                _msg_low    = _q.lower()
                _pl_mots    = [w for w in _pl_nom_low.split() if len(w) >= 4]
                _pl_valide  = (
                    any(w in _msg_low for w in _pl_mots) or
                    any(_pl_nom_low[i:i+4] in _msg_low for i in range(max(1, len(_pl_nom_low)-3)))
                )
                if _pl_valide and pl["nom"] and pl["nom"].lower() not in {"saucisse","saucisson","viande","poulet","poisson","fromage","beurre","lait","sel","poivre","sucre","farine"}:
                    msg_bot["plant_link"] = pl
                    _hist = st.session_state.get("plant_history", [])
                    _hist = [h for h in _hist if h["nom"].lower() != _pl_nom_low]
                    st.session_state["plant_history"] = [pl] + _hist[:9]
            msgs.append(msg_bot)
            set_sloth("talking", "Fiche mémorisée ! 🌿" if fiche_detectee else "Voilà ! 😄")

            # ── Tracker les requêtes potentiellement non résolues ──────────────
            _rep_low = rep.lower()
            _is_weak = (
                "je ne sais pas" in _rep_low or
                "je n'ai pas" in _rep_low or
                "désolé" in _rep_low or
                "erreur" in _rep_low or
                len(rep) < 80
            )
            if _is_weak:
                _unresolved = st.session_state.get("_unresolved", [])
                _unresolved.append({"question": _q, "reponse": rep})
                st.session_state["_unresolved"] = _unresolved[-20:]  # garder les 20 dernières

        st.session_state.msgs_libre = msgs
        st.rerun()



# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — JARDIN
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    jardin = st.session_state.jardin

    # ── Résumé ──────────────────────────────────────────────────────
    nb_terre = sum(1 for p in jardin if p.get("emplacement") == "Pleine terre")
    nb_pot   = sum(1 for p in jardin if p.get("emplacement") == "Pot / Bac")
    if jardin:
        c_sum1, c_sum2, c_sum3 = st.columns(3)
        with c_sum1:
            st.markdown(f"<div style='text-align:center;padding:10px;background:#1e3420;border-radius:12px;border:1px solid #3a6a3a'><div style='font-size:22px'>🌱</div><div style='font-size:18px;font-weight:700;color:#eaf2ea'>{len(jardin)}</div><div style='font-size:11px;color:#9ac89a'>plantes</div></div>", unsafe_allow_html=True)
        with c_sum2:
            st.markdown(f"<div style='text-align:center;padding:10px;background:#1e3420;border-radius:12px;border:1px solid #3a6a3a'><div style='font-size:22px'>🌍</div><div style='font-size:18px;font-weight:700;color:#c8a870'>{nb_terre}</div><div style='font-size:11px;color:#9ac89a'>pleine terre</div></div>", unsafe_allow_html=True)
        with c_sum3:
            st.markdown(f"<div style='text-align:center;padding:10px;background:#1e3420;border-radius:12px;border:1px solid #3a6a3a'><div style='font-size:22px'>🪴</div><div style='font-size:18px;font-weight:700;color:#80b8e8'>{nb_pot}</div><div style='font-size:11px;color:#9ac89a'>pot / bac</div></div>", unsafe_allow_html=True)
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ── Formulaire d'ajout ─────────────────────────────────────────────────
    with st.expander("➕ Ajouter une plante à mon jardin", expanded=not jardin):
        with st.form("form_add_jardin", clear_on_submit=True):
            jc1, jc2 = st.columns(2)
            with jc1:
                nom_j   = st.text_input("Nom de la plante *", placeholder="Ex : Tomate, Rosier…")
            with jc2:
                latin_j = st.text_input("Nom latin (optionnel)", placeholder="Ex : Solanum lycopersicum")

            jc3, jc4 = st.columns(2)
            with jc3:
                empl_j  = st.selectbox("Emplacement", ["Pleine terre", "Pot / Bac"])
            with jc4:
                expo_j  = st.selectbox("Exposition", [
                    "Plein soleil", "Mi-ombre", "Ombre totale",
                    "Soleil matinal (Est)", "Soleil tardif (Ouest)", "Non précisé"
                ])

            photo_j = st.file_uploader(
                "📷 Photo (optionnel)", type=["jpg","jpeg","png","webp"],
                help="Ajoute une photo personnelle de ta plante"
            )
            notes_j = st.text_area("Notes personnelles", height=65,
                                   placeholder="Plantation prévue en mai, paillis en juillet, arrosage quotidien…")
            gen_fiche_j = st.checkbox("Générer la fiche automatiquement (Wikipedia → Groq)", value=True)
            submitted_j = st.form_submit_button("🌱 Ajouter au jardin")

        if submitted_j and nom_j.strip():
            new_plant = {
                "nom":         nom_j.strip(),
                "nom_latin":   latin_j.strip(),
                "emplacement": empl_j,
                "exposition":  expo_j,
                "notes":       notes_j.strip(),
                "photo":       photo_j.read() if photo_j else None,
            }
            if gen_fiche_j:
                set_sloth("thinking", f"Création fiche {nom_j}… 📚")
                with st.spinner(f"Génération de la fiche pour {nom_j}…"):
                    fc, frm = get_or_create_fiche(nom_j.strip(), latin_j.strip() or nom_j.strip())
                new_plant["nom_latin"] = fc.get("nom_latin", latin_j.strip())
                new_plant["fiche_loaded"] = True
                set_sloth("excited", "Plante ajoutée ! 🌿" if not frm else "Plante ajoutée ! ⚡",
                          get_current_season())
            else:
                set_sloth("talking", "Plante ajoutée ! 🌿")
            st.session_state.jardin.append(new_plant)
            st.rerun()

    # ── Affichage des plantes ──────────────────────────────────────────────
    if jardin:
        for section_empl, section_ico, badge_cls in [
            ("Pleine terre", "🌍", "badge-terre"),
            ("Pot / Bac",    "🪴", "badge-pot"),
        ]:
            section_plants = [p for p in jardin if p.get("emplacement") == section_empl]
            if not section_plants:
                continue

            st.markdown(
                f"<div class='sec-hdr'>{section_ico} {section_empl} — {len(section_plants)} plante{'s' if len(section_plants)>1 else ''}</div>",
                unsafe_allow_html=True
            )

            for idx, plant in enumerate(section_plants):
                real_idx = next(
                    (i for i, p in enumerate(st.session_state.jardin) if p is plant),
                    None
                )
                _pnm  = plant.get("nom","")
                _plt  = plant.get("nom_latin","")
                _pex  = plant.get("exposition","")
                _pnt  = plant.get("notes","")
                _pphoto = plant.get("photo")  # bytes si photo uploadée

                col_photo, col_content = st.columns([1, 3])
                with col_photo:
                    if _pphoto:
                        # Photo personnelle uploadée
                        st.image(_pphoto, use_container_width=True)
                    else:
                        # Fallback : miniature Wikipedia
                        thumb = _get_wiki_thumb(_pnm, _plt) if (_plt or _pnm) else None
                        if thumb:
                            st.image(thumb, use_container_width=True)
                        else:
                            st.markdown(
                                '<div style="width:100%;aspect-ratio:1;background:#1c3a1c;border-radius:10px;'
                                'border:1px solid #3a5a3a;display:flex;align-items:center;'
                                'justify-content:center;font-size:26px">🌿</div>',
                                unsafe_allow_html=True
                            )

                with col_content:
                    expo_html  = f'<span class="badge-expo">☀️ {_pex}</span>' if _pex and _pex != "Non précisé" else ""
                    notes_html = f'<div style="font-size:12px;color:#a0c0a0;margin-top:5px;font-style:italic">📝 {_pnt}</div>' if _pnt else ""
                    latin_html = f'<span style="font-size:11px;color:#9ac89a;font-style:italic"> {_plt}</span>' if _plt else ""

                    st.markdown(f"""<div style="padding:4px 0">
  <div style="margin-bottom:4px">
    <strong style="color:#eaf2ea;font-size:16px">{_pnm}</strong>{latin_html}
  </div>
  <div style="margin-bottom:4px">
    <span class="{badge_cls}">{section_ico} {section_empl}</span>
    {expo_html}
  </div>
  {notes_html}
</div>""", unsafe_allow_html=True)

                btn_col1, btn_col2, _ = st.columns([1.2, 1, 2])
                with btn_col1:
                    if st.button(f"📋 Fiche", key=f"jardin_fiche_{real_idx}",
                                 on_click=_cb_ouvrir_fiche,
                                 kwargs={"nom": _pnm, "latin": _plt or _pnm, "target": "modal"}):
                        pass
                with btn_col2:
                    if st.button(f"🗑️ Suppr.", key=f"jardin_del_{real_idx}"):
                        st.session_state.jardin.pop(real_idx)
                        st.rerun()

                st.markdown("<hr style='border-color:#2a4a2a;margin:6px 0'>", unsafe_allow_html=True)

    else:
        st.markdown(
            "<div style='text-align:center;color:#6a9a6a;font-size:14px;padding:30px 0'>"
            "🌿 Ton jardin est vide.<br>Ajoute ta première plante avec le formulaire ci-dessus !"
            "</div>",
            unsafe_allow_html=True
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — BASE
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    _s = get_db_stats()
    st.markdown(f"### 🗄️ Base — {_s['total']} fiche{'s' if _s['total'] > 1 else ''}")
    for cat, count in _s["par_categorie"].items():
        st.markdown(f"- **{cat}** : {count} plante{'s' if count > 1 else ''}")

    st.markdown("---")
    q = st.text_input("🔍 Rechercher", placeholder="Ex: pin, lavande, monstera…", key="srch")
    if q and len(q) >= 2:
        res = search_db(q)
        if res:
            st.success(f"{len(res)} résultat(s)")
            for r in res:
                qa  = get_qa_summary(r)
                lbl = f"🌿 {r.get('nom_commun','')} — {r.get('nom_latin','')}"
                if qa["total"]:   lbl += f" · 📚 {qa['total']} Q&A"
                if qa["alertes"]: lbl += f" · ⚠️ {qa['alertes']} alerte(s)"
                with st.expander(lbl):
                    render_fiche(r)
                    qam = r.get("qa_memory", {})
                    if qam:
                        st.markdown("**📚 Q&A mémorisées :**")
                        for cat_q, entries in qam.items():
                            for e in entries:
                                icon = "⚠️" if e.get("has_alert") else "💬"
                                with st.expander(f"{icon} {e['question'][:80]}"):
                                    css_qa = "alert-box" if e.get("has_alert") else "chat-bot"
                                    st.markdown(f'<div class="{css_qa}">{e["answer"]}</div>', unsafe_allow_html=True)
        else:
            st.info("Aucun résultat. Va dans 📷 pour identifier et ajouter une plante !")

    st.markdown("---")
    st.markdown("**➕ Ajouter manuellement :**")
    c1, c2 = st.columns(2)
    with c1: mn = st.text_input("Nom commun", key="mn")
    with c2: ml = st.text_input("Nom latin",  key="ml")
    if st.button("📥 Générer la fiche (Wikipedia → Groq)") and mn and ml:
        set_sloth("thinking", "Wikipedia → Groq… 📚")
        with st.spinner(f"Génération pour {mn}…"):
            fc, frm = get_or_create_fiche(mn, ml)
        set_sloth(
            "excited" if not frm else "talking",
            "Nouvelle fiche ! 🌿" if not frm else "Déjà en base ! ⚡"
        )
        st.success(f"✅ {mn} {'créée et sauvegardée' if not frm else 'déjà en base'} !")
        render_fiche(fc, frm)