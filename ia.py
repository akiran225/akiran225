import os, re, json, requests
from memory import (
    load_from_db, save_to_db, detect_category, FICHE_SCHEMA,
    find_cached_answer, add_qa, get_context, contains_alert,
    get_db_stats, purge_corrupted_fiches, repair_nom_commun_from_description
)

GROQ_KEY     = os.getenv("GROQ_API_KEY", "")
PLANTNET_KEY = os.getenv("PLANTNET_API_KEY", "")
TREFLE_KEY   = os.getenv("TREFLE_API_KEY", "")
GROQ_URL          = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL        = "llama-3.3-70b-versatile"
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
TREFLE_URL   = "https://trefle.io/api/v1"

# Champs essentiels — si vides, on enrichit
CHAMPS_ESSENTIELS = [
    "description", "exposition", "sol_type", "arrosage_frequence",
    "resistance_froid", "hauteur_adulte", "floraison",
    "terreau_recommande",
    "associations_benefiques", "maladies_courantes", "conseil_plantation"
]

# ── Dictionnaire de synonymes / expressions populaires ──────────────────────
# Clé : expression courante → valeur : (nom_commun, nom_latin) à utiliser
# Permet de répondre à "plante grasse" sans appeler Groq pour la détection
SYNONYMES_PLANTES = {
    # Groupes génériques → plante représentative
    "plante grasse":          ("Succulente", "Echeveria"),
    "plantes grasses":        ("Succulente", "Echeveria"),
    "cactus":                 ("Cactus", "Cactaceae"),
    "arbre fruitier":         ("Pommier", "Malus domestica"),
    "arbres fruitiers":       ("Pommier", "Malus domestica"),
    "fleurs de jardin":       ("Rose", "Rosa"),
    "plante d'intérieur":     ("Monstera", "Monstera deliciosa"),
    "plantes d'intérieur":    ("Monstera", "Monstera deliciosa"),
    "plante verte":           ("Pothos", "Epipremnum aureum"),
    "plantes vertes":         ("Pothos", "Epipremnum aureum"),
    "herbe aromatique":       ("Basilic", "Ocimum basilicum"),
    "herbes aromatiques":     ("Basilic", "Ocimum basilicum"),
    "plante médicinale":      ("Lavande", "Lavandula angustifolia"),
    "plantes médicinales":    ("Lavande", "Lavandula angustifolia"),
    "plante aquatique":       ("Nénuphar", "Nymphaea"),
    "plantes aquatiques":     ("Nénuphar", "Nymphaea"),
    "plante carnivore":       ("Dionée", "Dionaea muscipula"),
    "plantes carnivores":     ("Dionée", "Dionaea muscipula"),
    "bonsaï":                 ("Bonsaï", "Ficus retusa"),
    "bonsai":                 ("Bonsaï", "Ficus retusa"),
    "gazon":                  ("Gazon", "Festuca arundinacea"),
    "pelouse":                ("Gazon", "Festuca arundinacea"),
    "haie":                   ("Laurier", "Prunus laurocerasus"),
    "rosier":                 ("Rosier", "Rosa"),
    "rosiers":                ("Rosier", "Rosa"),
    "géranium":               ("Géranium", "Pelargonium"),
    "géraniums":              ("Géranium", "Pelargonium"),
    "tomate":                 ("Tomate", "Solanum lycopersicum"),
    "tomates":                ("Tomate", "Solanum lycopersicum"),
    "salade":                 ("Laitue", "Lactuca sativa"),
    "fougère":                ("Fougère", "Nephrolepis exaltata"),
    "orchidée":               ("Orchidée", "Phalaenopsis"),
    "orchidées":              ("Orchidée", "Phalaenopsis"),
    "palmier":                ("Palmier", "Phoenix canariensis"),
    "bambou":                 ("Bambou", "Phyllostachys aurea"),
    "lierre":                 ("Lierre", "Hedera helix"),
    "jasmin":                 ("Jasmin", "Jasminum officinale"),
}

# ── Référentiel terreau — source de vérité pour tout conseil substrat ───────
# ── Référentiel des substrats vendus en jardinerie ──────────────────────────
# Noms exacts des sacs qu'on trouve en magasin (Jardiland, Gamm Vert, Truffaut…)
TERREAU_REF = {
    "terreau universel": {
        "description": "Substrat polyvalent (pH 6–7), bon pour la majorité des plantes",
        "ecosystemes": ["usage général"],
        "plantes":     [],
        "ph": "6–7",
    },
    "terreau méditerranéen": {
        "description": "Substrat très drainant (pH 6.5–8), pauvre, pour plantes de zones arides",
        "ecosystemes": ["garrigue", "maquis", "zone aride", "steppe", "climat sec"],
        "plantes":     ["Lavande", "Yucca", "Olivier", "Cordyline", "Agapanthe",
                        "Thym", "Romarin", "Laurier-rose", "Pistachier", "Ciste",
                        "Agave", "Bougainvillée", "Palmier", "Cyprès", "Romarin"],
        "ph": "6.5–8",
    },
    "terre de bruyère": {
        "description": "Substrat acide (pH 4–6), riche en tourbe, pour plantes acidophiles",
        "ecosystemes": ["lande", "forêt de conifères", "zone humide acide", "tourbière"],
        "plantes":     ["Rhododendron", "Azalée", "Hortensia", "Camélia", "Magnolia",
                        "Myrtille", "Fougère", "Callune", "Bruyère", "Gardénia", "Kalmia"],
        "ph": "4–6",
    },
    "terre végétale": {
        "description": "Terre de jardin enrichie (pH 6–7), dense, pour plein sol et massifs",
        "ecosystemes": ["jardin", "plein sol", "massif"],
        "plantes":     [],
        "ph": "6–7",
    },
    "terreau plantation": {
        "description": "Substrat riche (pH 6–7), stimule la reprise à la plantation en plein sol",
        "ecosystemes": ["plantation", "repiquage"],
        "plantes":     [],
        "ph": "6–7",
    },
    "tourbe": {
        "description": "Substrat acide pur (pH 3.5–5), léger, retient bien l'eau — souvent utilisé en mélange",
        "ecosystemes": ["tourbière", "zone humide acide"],
        "plantes":     [],
        "ph": "3.5–5",
    },
    "terreau plante verte": {
        "description": "Substrat équilibré (pH 6–7), riche en humus, retient bien l'humidité",
        "ecosystemes": ["forêt tropicale", "jungle", "sous-bois humide"],
        "plantes":     ["Pothos", "Ficus", "Dracaena", "Philodendron", "Calathea",
                        "Dieffenbachia", "Schefflera", "Croton", "Spathiphyllum",
                        "Monstera", "Tradescantia", "Peperomia"],
        "ph": "6–7",
    },
    "terreau cactus": {
        "description": "Substrat très drainant (pH 6–7), sableux, séchage très rapide",
        "ecosystemes": ["désert", "semi-aride", "savane sèche", "zone rocailleuse"],
        "plantes":     ["Cactus", "Succulente", "Echeveria", "Aloe", "Haworthia",
                        "Sempervivum", "Sedum", "Euphorbe cactiforme", "Agave"],
        "ph": "6–7",
    },
    "terreau horticole potager": {
        "description": "Substrat professionnel riche (pH 6–7), haute fertilité, usage intensif",
        "ecosystemes": ["potager professionnel", "culture intensive"],
        "plantes":     ["Tomate", "Poivron", "Aubergine", "Courgette", "Concombre"],
        "ph": "6–7",
    },
    "terreau potager": {
        "description": "Substrat riche en nutriments (pH 6–7), pour le jardinage amateur",
        "ecosystemes": ["potager", "culture alimentaire"],
        "plantes":     ["Tomate", "Courgette", "Haricot", "Salade", "Carotte",
                        "Poivron", "Aubergine", "Radis", "Épinard", "Poireau"],
        "ph": "6–7",
    },
    "terreau orchidée": {
        "description": "Substrat très aéré à base d'écorces de pin (pH 5.5–6.5), pour épiphytes",
        "ecosystemes": ["forêt tropicale humide", "épiphyte sur arbres"],
        "plantes":     ["Orchidée", "Phalaenopsis", "Dendrobium", "Cattleya",
                        "Anthurium", "Tillandsia", "Broméliacée"],
        "ph": "5.5–6.5",
    },
    "pouzzolane": {
        "description": "Roche volcanique poreuse — améliore le drainage, allège le substrat. Pas un terreau seul.",
        "ecosystemes": ["drainage", "amendement"],
        "plantes":     [],
        "ph": "neutre",
    },
    "bille d'argile": {
        "description": "Argile expansée — drainage fond de pot, culture hydroponique. Pas un terreau seul.",
        "ecosystemes": ["drainage", "fond de pot", "hydroponique"],
        "plantes":     [],
        "ph": "neutre",
    },
}

# ── Mélanges recommandés par plante ─────────────────────────────────────────
# Règle : si un mélange existe → TOUJOURS le recommander, pas un seul produit
TERREAU_COMPOSITIONS = {
    # Tropicales intérieur
    "Monstera":       "60 % terreau plante verte + 40 % terreau orchidée — billes d'argile au fond du pot",
    "Pothos":         "100 % terreau plante verte (ou 70 % + 30 % terreau orchidée pour encore plus de drainage)",
    "Philodendron":   "70 % terreau plante verte + 30 % terreau orchidée",
    "Calathea":       "70 % terreau plante verte + 30 % tourbe",
    "Dracaena":       "100 % terreau plante verte",
    "Spathiphyllum":  "100 % terreau plante verte (garder légèrement humide en permanence)",
    "Tradescantia":   "100 % terreau plante verte",
    "Peperomia":      "60 % terreau plante verte + 40 % terreau orchidée",
    "Ficus":          "100 % terreau plante verte",
    "Schefflera":     "100 % terreau plante verte",
    # Épiphytes / orchidées
    "Orchidée":       "100 % terreau orchidée (écorces de pin uniquement — jamais de terreau classique)",
    "Phalaenopsis":   "100 % terreau orchidée",
    "Anthurium":      "50 % terreau plante verte + 50 % terreau orchidée",
    "Broméliacée":    "50 % terreau orchidée + 50 % terreau plante verte",
    # Succulentes / désert
    "Cactus":         "60 % terreau cactus + 40 % pouzzolane — billes d'argile au fond du pot",
    "Succulente":     "60 % terreau cactus + 40 % pouzzolane",
    "Echeveria":      "60 % terreau cactus + 40 % pouzzolane",
    "Aloe":           "60 % terreau cactus + 40 % pouzzolane",
    "Haworthia":      "60 % terreau cactus + 40 % pouzzolane",
    "Agave":          "60 % terreau méditerranéen + 40 % pouzzolane",
    # Méditerranéennes
    "Lavande":        "100 % terreau méditerranéen, ou 70 % terreau méditerranéen + 30 % pouzzolane en pot",
    "Olivier":        "100 % terreau méditerranéen",
    "Thym":           "100 % terreau méditerranéen",
    "Romarin":        "100 % terreau méditerranéen",
    "Yucca":          "70 % terreau méditerranéen + 30 % pouzzolane",
    "Cordyline":      "60 % terreau méditerranéen + 20 % terreau universel + 20 % pouzzolane",
    "Agapanthe":      "70 % terreau méditerranéen + 30 % pouzzolane",
    "Palmier":        "70 % terreau méditerranéen + 30 % pouzzolane",
    "Laurier-rose":   "100 % terreau méditerranéen",
    "Bougainvillée":  "70 % terreau méditerranéen + 30 % terreau universel",
    "Cyprès":         "100 % terreau méditerranéen ou terre végétale + pouzzolane",
    # Acidophiles
    "Rhododendron":   "100 % terre de bruyère",
    "Azalée":         "100 % terre de bruyère",
    "Camélia":        "100 % terre de bruyère",
    "Hortensia":      "80 % terre de bruyère + 20 % terreau universel",
    "Myrtille":       "100 % terre de bruyère",
    "Fougère":        "70 % terre de bruyère + 30 % terreau plante verte",
    "Magnolia":       "80 % terre de bruyère + 20 % terreau universel",
    "Gardénia":       "100 % terre de bruyère",
    "Kalmia":         "100 % terre de bruyère",
    # Potager
    "Tomate":         "100 % terreau potager ou terreau horticole potager",
    "Courgette":      "100 % terreau potager",
    "Poivron":        "100 % terreau potager ou terreau horticole potager",
    "Aubergine":      "100 % terreau potager ou terreau horticole potager",
    "Salade":         "100 % terreau potager",
    "Carotte":        "100 % terreau potager (bien meuble, profond)",
    "Haricot":        "100 % terreau potager",
    # Arbustes / vivaces jardin
    "Géranium":       "100 % terreau universel ou terreau plantation en plein sol",
    "Rose":           "terreau plantation en plein sol, ou 70 % terreau universel + 30 % terre végétale en pot",
    "Rosier":         "terreau plantation en plein sol, ou 70 % terreau universel + 30 % terre végétale en pot",
    "Bambou":         "70 % terreau universel + 30 % terre végétale",
}

def _terreau_context(nom_commun: str, ecosysteme: str = "") -> str:
    """
    Retourne le bloc de contexte terreau à injecter dans le prompt.
    Basé sur la composition si connue, sinon sur l'écosystème naturel.
    """
    lines = []

    # 1. Composition spécifique connue
    for plante, compo in TERREAU_COMPOSITIONS.items():
        if plante.lower() in nom_commun.lower() or nom_commun.lower() in plante.lower():
            lines.append(f"COMPOSITION TERREAU RECOMMANDÉE pour {nom_commun} : {compo}")
            break

    # 2. Déduction depuis l'écosystème naturel
    if ecosysteme:
        eco_low = ecosysteme.lower()
        for terreau, data in TERREAU_REF.items():
            for eco_ref in data["ecosystemes"]:
                if any(w in eco_low for w in eco_ref.lower().split()):
                    lines.append(f"DÉDUCTION DEPUIS MILIEU NATUREL : '{ecosysteme}' → {terreau} ({data['description']}, pH {data['ph']})")
                    break

    # 3. Référentiel complet
    ref_str = " | ".join(
        f"{k} (pH {v['ph']})" for k, v in TERREAU_REF.items()
    )
    lines.append(f"RÉFÉRENTIEL TERREAU : {ref_str}")

    return "\n".join(lines) if lines else ""

# ══════════════════════════════════════════════════════════════════
# COUCHE 1 — WIKIPEDIA (français, gratuit)
# ══════════════════════════════════════════════════════════════════
WIKI_API = "https://fr.wikipedia.org/api/rest_v1/page/summary/"
WIKI_SRC = "https://fr.wikipedia.org/w/api.php"

def _fetch_plant_image_url(nom_latin: str, nom_commun: str) -> str:
    """
    Cascade pour obtenir une URL d'image (pas bytes) :
    1. Wikipedia FR  — thumbnail ou originalimage
    2. Wikipedia EN  — beaucoup plus complet pour les espèces rares
    3. Wikimedia Commons — millions d'images botaniques
    Retourne "" si rien trouvé.
    """
    headers = {"Accept": "application/json", "User-Agent": "Slothia/1.0"}

    # 1 & 2 — Wikipedia FR puis EN, nom latin puis commun
    for lang, query in [("fr", nom_latin), ("fr", nom_commun),
                        ("en", nom_latin), ("en", nom_commun)]:
        if not query:
            continue
        try:
            r = requests.get(
                f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ','_')}",
                headers=headers, timeout=6
            )
            if r.status_code == 200:
                d = r.json()
                url = (d.get("thumbnail") or {}).get("source") or \
                      (d.get("originalimage") or {}).get("source") or ""
                if url:
                    return url
        except Exception:
            continue

    # 3 — Wikimedia Commons (cherche par nom latin)
    if nom_latin:
        try:
            r = requests.get(
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
                pages = r.json().get("query", {}).get("pages", {})
                for page in pages.values():
                    info = page.get("imageinfo", [{}])[0]
                    mime = info.get("mime", "")
                    url  = info.get("thumburl") or info.get("url", "")
                    if url and mime.startswith("image/") and "svg" not in mime:
                        return url
        except Exception:
            pass

    return ""


def wikipedia_fetch(nom_commun: str, nom_latin: str) -> dict:
    for query in [nom_latin, nom_commun]:
        d = _wiki_get(query)
        if d and _is_plant(d):
            result = _extract(d)
            # Si Wikipedia FR n'a pas d'image, tenter la cascade complète
            if not result.get("image"):
                result["image"] = _fetch_plant_image_url(nom_latin, nom_commun)
            return result
    d = _wiki_search(f"{nom_commun} plante botanique")
    if d:
        result = _extract(d)
        if not result.get("image"):
            result["image"] = _fetch_plant_image_url(nom_latin, nom_commun)
        return result
    # Wikipedia ne trouve rien du tout — tente quand même une image
    img = _fetch_plant_image_url(nom_latin, nom_commun)
    return {"image": img} if img else {}

def _wiki_get(title: str) -> dict | None:
    try:
        r = requests.get(f"{WIKI_API}{title.replace(' ','_')}",
                         headers={"Accept":"application/json"}, timeout=10)
        if r.status_code == 200:
            d = r.json()
            if d.get("type") != "disambiguation":
                return d
    except Exception:
        pass
    return None

def _wiki_search(query: str) -> dict | None:
    try:
        r = requests.get(WIKI_SRC, params={
            "action":"query","list":"search","srsearch":query,
            "srlimit":3,"format":"json","utf8":1
        }, timeout=10)
        for res in r.json().get("query",{}).get("search",[]):
            d = _wiki_get(res["title"])
            if d and _is_plant(d):
                return d
    except Exception:
        pass
    return None

def _is_plant(d: dict) -> bool:
    t = (d.get("description","") + d.get("extract","")).lower()
    return any(k in t for k in ["plante","végétal","arbre","arbuste","fleur","espèce","botanique","famille","genre","taxon"])

def _extract(d: dict) -> dict:
    ex = d.get("extract","")
    _orig  = d.get("originalimage") or {}
    _thumb = d.get("thumbnail") or {}
    # Préfère le thumbnail (taille raisonnable) pour l'affichage
    image_url = _thumb.get("source") or _orig.get("source") or ""
    return {k:v for k,v in {
        "titre":       d.get("title",""),
        "description": d.get("description",""),
        "resume":      _clean(ex),
        "url":         d.get("content_urls",{}).get("desktop",{}).get("page",""),
        "toxicite":    _find_tox(ex),
        "famille":     _find_fam(ex),
        "origine":     _find_ori(ex),
        "image":       image_url,
    }.items() if v}

def _clean(t: str) -> str:
    t = re.sub(r'\[\d+\]','',t)
    return (t[:600].rsplit('.',1)[0]+".").strip() if len(t)>600 else t.strip()

def _find_tox(t: str) -> str | None:
    for s in t.split('.'):
        if any(m in s.lower() for m in ["toxique","vénéneux","vénéneuse","poison","nocif","mortel","irritant"]):
            return s.strip()
    return None

def _find_fam(t: str) -> str | None:
    for p in [r'famille des? ([A-Z][a-zéèêëàâùûüïî]+acées?)',r'([A-Z][a-z]+aceae)']:
        m = re.search(p,t)
        if m: return m.group(1)
    return None

def _find_ori(t: str) -> str | None:
    for p in [r'originaire (?:de |d\'|du )([^,.]{5,80})',r'(?:endémique|indigène) (?:de |d\'|du )([^,.]{5,80})']:
        m = re.search(p,t,re.IGNORECASE)
        if m: return m.group(1).strip()
    return None


# ══════════════════════════════════════════════════════════════════
# COUCHE 2 — TREFLE.IO (données botaniques structurées et certifiées)
# ══════════════════════════════════════════════════════════════════

# Mapping lumière Trefle (1-10) → exposition FR
_TREFLE_LIGHT = {
    range(1, 3):  "ombre totale",
    range(3, 6):  "mi-ombre",
    range(6, 9):  "mi-ombre à plein soleil",
    range(9, 11): "plein soleil",
}

# Mapping eau Trefle (1-10) → fréquence arrosage FR
_TREFLE_WATER = {
    range(1, 3):  "très peu — résistant à la sécheresse",
    range(3, 5):  "faible — arrosage mensuel",
    range(5, 7):  "modéré — arrosage hebdomadaire",
    range(7, 9):  "élevé — sol constamment humide",
    range(9, 11): "aquatique — immersion possible",
}

# Mapping texture sol Trefle (1-5) → FR
_TREFLE_TEXTURE = {
    1: "sableux", 2: "sablo-limoneux", 3: "limoneux",
    4: "argilo-limoneux", 5: "argileux"
}

def _trefle_map_range(value: int, mapping: dict) -> str:
    for r, label in mapping.items():
        if value in r:
            return label
    return ""

def trefle_fetch(nom_latin: str) -> dict:
    """
    Interroge Trefle.io avec le nom latin et retourne les données
    botaniques structurées, déjà mappées en français.
    Retourne {} si clé absente, espèce inconnue ou erreur réseau.
    Ne lève jamais d'exception — toujours silencieux en cas d'échec.
    """
    if not TREFLE_KEY or not nom_latin or len(nom_latin) < 3:
        return {}
    try:
        # 1. Recherche par nom latin
        r = requests.get(
            f"{TREFLE_URL}/plants/search",
            params={"token": TREFLE_KEY, "q": nom_latin},
            timeout=15
        )
        if r.status_code != 200:
            return {}
        results = r.json().get("data", [])
        if not results:
            return {}

        plant_id = results[0].get("id")
        if not plant_id:
            return {}

        # 2. Détails complets
        detail = requests.get(
            f"{TREFLE_URL}/plants/{plant_id}",
            params={"token": TREFLE_KEY},
            timeout=15
        )
        if detail.status_code != 200:
            return {}

        data   = detail.json().get("data", {})
        specs  = data.get("main_species", data)
        growth = specs.get("growth", {}) or {}

        result = {"source_trefle": True}

        # Résistance au froid
        min_temp = growth.get("minimum_temperature", {})
        if isinstance(min_temp, dict):
            deg_c = min_temp.get("deg_c")
            if deg_c is not None:
                result["resistance_froid"] = f"{deg_c}°C minimum"

        # Hauteur adulte
        max_h = growth.get("maximum_height", {})
        if isinstance(max_h, dict):
            cm = max_h.get("cm")
            if cm:
                result["hauteur_adulte"] = f"jusqu'à {round(cm/100,1)} m"

        # Exposition (lumière)
        light = growth.get("light")
        if light is not None:
            result["exposition"] = _trefle_map_range(int(light), _TREFLE_LIGHT)

        # Arrosage
        water = growth.get("moisture_use") or growth.get("atmospheric_humidity")
        if water is not None:
            result["arrosage_frequence"] = _trefle_map_range(int(water), _TREFLE_WATER)

        # pH sol
        ph_min = growth.get("ph_minimum")
        ph_max = growth.get("ph_maximum")
        if ph_min is not None and ph_max is not None:
            result["sol_ph"] = f"pH {ph_min}–{ph_max}"

        # Famille botanique — extrait le nom string même si l'API retourne un dict
        famille_raw = data.get("family")
        if isinstance(famille_raw, dict):
            famille = famille_raw.get("name", "") or famille_raw.get("common_name", "") or ""
        else:
            famille = famille_raw or ""
        if not famille:
            famille = specs.get("family_common_name", "")
        if famille:
            result["famille_trefle"] = str(famille)

        # Durée de vie
        duration = specs.get("duration", [])
        if duration:
            duree_map = {"annual":"annuelle","biennial":"bisannuelle","perennial":"vivace"}
            result["duree_vie"] = ", ".join(duree_map.get(d, d) for d in duration)

        # Mois de floraison
        bloom_months = growth.get("bloom_months", [])
        if bloom_months:
            mois_fr = {
                "jan":"janvier","feb":"février","mar":"mars","apr":"avril",
                "may":"mai","jun":"juin","jul":"juillet","aug":"août",
                "sep":"septembre","oct":"octobre","nov":"novembre","dec":"décembre"
            }
            result["floraison_mois"] = ", ".join(mois_fr.get(m, m) for m in bloom_months)

        # Texture du sol
        soil_texture = growth.get("soil_texture")
        if soil_texture is not None:
            result["sol_texture"] = _TREFLE_TEXTURE.get(int(soil_texture), "")

        # Toxicité (si renseignée)
        toxicity = specs.get("toxicity", "")
        if toxicity and toxicity.lower() not in ["none", "", "no"]:
            result["toxicite_trefle"] = f"⚠️ Trefle signale une toxicité : {toxicity}"

        return result

    except Exception:
        return {}  # Toujours silencieux


def _trefle_block(trefle: dict, nom: str) -> str:
    """Formatte les données Trefle pour injection dans le prompt Groq."""
    if not trefle or not trefle.get("source_trefle"):
        return ""
    lines = [f"\n\n── Trefle.io (données certifiées) : {nom} ──"]
    if trefle.get("resistance_froid"):
        lines.append(f"Résistance froid (CERTIFIÉ) : {trefle['resistance_froid']}")
    if trefle.get("hauteur_adulte"):
        lines.append(f"Hauteur adulte (CERTIFIÉ) : {trefle['hauteur_adulte']}")
    if trefle.get("exposition"):
        lines.append(f"Exposition (CERTIFIÉ) : {trefle['exposition']}")
    if trefle.get("arrosage_frequence"):
        lines.append(f"Besoins en eau (CERTIFIÉ) : {trefle['arrosage_frequence']}")
    if trefle.get("sol_ph"):
        lines.append(f"pH sol (CERTIFIÉ) : {trefle['sol_ph']}")
    if trefle.get("floraison_mois"):
        lines.append(f"Mois floraison (CERTIFIÉ) : {trefle['floraison_mois']}")
    if trefle.get("duree_vie"):
        lines.append(f"Durée de vie : {trefle['duree_vie']}")
    if trefle.get("sol_texture"):
        lines.append(f"Texture sol préférée : {trefle['sol_texture']}")
    if trefle.get("toxicite_trefle"):
        lines.append(trefle["toxicite_trefle"])
    lines.append("⚠️ Ces données sont CERTIFIÉES — utilise-les telles quelles, ne les modifie pas.")
    lines.append("──────────────────────────")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════
# COUCHE 3 — GROQ (synthèse + enrichissement francophone)
# ══════════════════════════════════════════════════════════════════
def _groq(messages: list, system: str, temp: float = 0.5, max_t: int = 1000) -> str:
    import time
    if not GROQ_KEY:
        return "⚠️ GROQ_API_KEY manquante dans le fichier .env"

    payload = {
        "model":       GROQ_MODEL,
        "messages":    [{"role": "system", "content": system}] + messages,
        "max_tokens":  max_t,
        "temperature": temp,
    }
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}

    # Retry automatique sur 429 (rate limit) — 3 tentatives, pauses croissantes
    for attempt in range(3):
        try:
            r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
            if r.status_code == 429:
                wait = (attempt + 1) * 8  # 8s, 16s, 24s
                print(f"[GROQ] Rate limit 429 — attente {wait}s (tentative {attempt+1}/3)")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            if attempt < 2:
                time.sleep(5)
                continue
            return "⚠️ Slothia ne répond pas (timeout). Réessaie dans un instant."
        except Exception as e:
            if attempt < 2 and "429" in str(e):
                time.sleep((attempt + 1) * 8)
                continue
            return f"Erreur Groq : {e}"

    return "⚠️ Trop de requêtes en ce moment. Attends 30 secondes et réessaie 🙏"

def _wiki_block(wiki: dict, nom: str) -> str:
    if not wiki or not wiki.get("resume"):
        return ""
    lines = [
        f"\n\n── Wikipedia : {nom} ──",
        f"Description : {wiki.get('description','')}",
        f"Résumé : {wiki.get('resume','')}",
    ]
    if wiki.get("famille"): lines.append(f"Famille : {wiki['famille']}")
    if wiki.get("origine"): lines.append(f"Origine : {wiki['origine']}")
    if wiki.get("toxicite"): lines.append(f"⚠️ TOXICITÉ : {wiki['toxicite']}")
    if wiki.get("url"):     lines.append(f"Source : {wiki['url']}")
    lines.append("──────────────────────────")
    return "\n".join(lines)


# ── Mots non-végétaux qu'hallucine parfois Groq dans les associations ──
_NON_PLANTES = {
    "saucisse","saucisson","viande","poulet","poisson","fromage","beurre","lait",
    "sel","poivre","sucre","farine","huile","eau","vin","bière","café","thé",
    "insecte","abeille","papillon","ver","lombric","mulch","compost","engrais",
    "pierre","gravier","sable","pot","jardin","soleil","ombre","pluie",
}

def _is_latin_genus(s: str) -> bool:
    """
    Détecte un genre latin botanique comme 'Cucurbita', 'Solanum', 'Allium'.
    Critères : 1 seul mot, commence par majuscule, reste en minuscule, ASCII pur, 4-25 chars.
    """
    if ' ' in s or not (4 <= len(s) <= 25):
        return False
    if not s[0].isupper():
        return False
    # Reste entièrement en minuscule
    if not s[1:].islower():
        return False
    # ASCII pur (pas d'accent → c'est du latin, pas du français)
    try:
        s.encode('ascii')
    except UnicodeEncodeError:
        return False  # contient des accents → probablement du français, on garde
    return True

def _filter_associations(items) -> list:
    """Nettoie une liste d'associations : supprime non-plantes, genres latins, placeholders, doublons."""
    if not isinstance(items, list):
        return []
    seen, result = set(), []
    for item in items:
        if not isinstance(item, str):
            continue
        s = item.strip()
        if len(s) < 3 or len(s) > 60:
            continue
        if any(c.isdigit() for c in s):
            continue
        if s.lower() in ("plante1","plante2","plante3","nom_plante","nom de plante","...","exemple",
                          "nom commun fr","nom commun fr 1","nom commun fr 2","nom commun fr 3"):
            continue
        if s.lower() in _NON_PLANTES:
            continue
        # Supprime les genres latins purs (ex: "Cucurbita", "Solanum", "Allium")
        if _is_latin_genus(s):
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(s)
    return result


def _description_contaminee(nom_commun: str, nom_latin: str, description: str) -> bool:
    """
    Retourne True si la description parle d'une autre plante.
    Vérifie que la description mentionne au moins un mot du nom cible (>3 lettres)
    ou le genre latin.
    """
    if not description or len(description) < 60:
        return False
    desc_low = description.lower()
    mots_cible = [m for m in nom_commun.lower().split() if len(m) > 3]
    genre_latin = nom_latin.lower().split()[0] if nom_latin else ""
    return not any(m in desc_low for m in mots_cible + ([genre_latin] if genre_latin else []))


def groq_fiche(nom_commun: str, nom_latin: str, wiki: dict, trefle: dict = None) -> dict:
    """
    Génère une fiche JSON structurée.
    Les données Trefle certifiées sont injectées ET forcées après parsing
    pour garantir qu'elles ne peuvent pas être hallucénées par Groq.
    """
    cat, sub = detect_category(nom_latin, nom_commun)
    wb = _wiki_block(wiki, nom_commun)
    tb = _trefle_block(trefle or {}, nom_commun)

    # Valeurs certifiées à forcer après le parsing JSON
    trefle_certifie = {}
    if trefle:
        for champ, cle in [
            ("resistance_froid", "resistance_froid"),
            ("hauteur_adulte",   "hauteur_adulte"),
            ("exposition",       "exposition"),
            ("arrosage_frequence","arrosage_frequence"),
            ("sol_ph",           "sol_ph"),
            ("floraison",        "floraison_mois"),
        ]:
            if trefle.get(cle):
                trefle_certifie[champ] = trefle[cle]

    # Composition connue pour cette plante → à injecter directement dans le prompt
    _compo_connue = ""
    for _nom_ref, _compo in TERREAU_COMPOSITIONS.items():
        if _nom_ref.lower() in nom_commun.lower() or nom_commun.lower() in _nom_ref.lower():
            _compo_connue = f"COMPOSITION TERREAU CONNUE pour {nom_commun} : {_compo}"
            break

    system = (
        f"Tu es botaniste expert francophone. "
        f"Tu génères UNIQUEMENT la fiche de '{nom_commun}' ({nom_latin}). "
        f"NE PARLE PAS d'une autre plante. "
        f"Les données marquées CERTIFIÉ viennent de Trefle.io — copie-les exactement. "
        f"Si tu ne connais pas une information, laisse le champ vide ('') plutôt qu'inventer. "
        f"Pour les associations, utilise UNIQUEMENT des noms communs français (ex: 'basilic', 'tomate', 'lavande'). "
        f"JAMAIS de noms latins comme 'Cucurbita', 'Solanum', 'Allium' dans les associations. "
        f"\n\nPOUR terreau_recommande — RÈGLES ABSOLUES :"
        f"\n- Utilise UNIQUEMENT les noms exacts de sacs vendus en jardinerie, sans parenthèses, sans décrire leur composition."
        f"\n- Noms autorisés : 'terreau universel', 'terre de bruyère', 'terreau méditerranéen', 'terreau cactus',"
        f"  'terreau plante verte', 'terreau potager', 'terreau horticole potager', 'terreau orchidée',"
        f"  'terreau plantation', 'terre végétale', 'tourbe', 'pouzzolane', 'bille d'argile'."
        f"\n- Si mélange : format OBLIGATOIRE '60 % terreau plante verte + 40 % terreau orchidée' (juste les noms, pas d'explication)."
        f"\n- NE JAMAIS écrire entre parenthèses la composition d'un terreau (ex: INTERDIT 'terreau méditerranéen (70% universel + 30% sable)')."
        f"\n- Règles par écosystème : garrigue/maquis/méditerranéen → 'terreau méditerranéen'."
        f"  Forêt tropicale → '60 % terreau plante verte + 40 % terreau orchidée'."
        f"  Épiphyte → 'terreau orchidée'. Acide/lande → 'terre de bruyère'. Désert → 'terreau cactus'."
        f"\n{_compo_connue}"
        f"\nRéponds uniquement en JSON valide sans markdown ni backticks."
    )

    # Injection terreau dans le prompt si composition connue
    _terreau_hint = f"\nIMPORTANT terreau_recommande pour {nom_commun} : {_compo_connue}" if _compo_connue else ""

    prompt = f"""{wb}{tb}{_terreau_hint}

PLANTE CONCERNÉE : {nom_commun} ({nom_latin})
CATÉGORIE : {cat} / {sub}

Génère la fiche technique UNIQUEMENT pour {nom_commun} ({nom_latin}).
Si tu n'as pas l'information, mets une chaîne vide "".
IMPORTANT : associations_benefiques, associations_incompatibles et plantes_meme_ecosysteme
doivent contenir des NOMS COMMUNS FRANÇAIS uniquement (ex: "basilic", "tomate", "courge").
JAMAIS de genres latins (ex: "Cucurbita", "Solanum") dans ces champs.

Réponds UNIQUEMENT en JSON valide :
{{"nom_commun":"{nom_commun}","nom_latin":"{nom_latin}","famille":"...","categorie":"{cat}","sous_categorie":"{sub}","description":"2-3 phrases sur {nom_commun} uniquement","origine_naturelle":"origine de {nom_commun}","ecosysteme_naturel":"habitat de {nom_commun}","exposition":"plein soleil / mi-ombre / ombre","sol_type":"types de sol","sol_ph":"acide/neutre/calcaire","terreau_recommande":"nom de sac vendu en jardinerie ex: terreau universel, terre de bruyère, terreau méditerranéen, terreau cactus, terreau potager — précise le mélange si besoin","arrosage":"besoins en eau","arrosage_frequence":"fréquence d'arrosage","resistance_froid":"température minimale ex: -15°C","zone_rusticite":"zones USDA","hauteur_adulte":"ex: 15-25m","croissance":"lente/moyenne/rapide","taille":"quand et comment tailler","floraison":"mois et couleur","fructification":"fruits/graines si applicable","biodiversite":"rôle écologique","insectes_attires":"liste insectes","oiseaux_attires":"liste oiseaux","associations_benefiques":["nom commun FR","nom commun FR","nom commun FR"],"associations_incompatibles":["nom commun FR","nom commun FR"],"plantes_meme_ecosysteme":["nom commun FR","nom commun FR","nom commun FR"],"maladies_courantes":"maladies + traitements naturels","ravageurs":"ravageurs + traitements","conseil_plantation":"quand et comment planter","conseil_entretien":"entretien annuel","tags":["tag1","tag2"],"source":"wiki+trefle+groq"}}"""

    text = _groq(
        [{"role":"user","content":prompt}],
        system,
        temp=0.1,
        max_t=1500
    )
    try:
        fiche = json.loads(text.replace("```json","").replace("```","").strip())

        # Sécurité : force les bons identifiants
        fiche["nom_commun"]    = nom_commun
        fiche["nom_latin"]     = nom_latin
        fiche["categorie"]     = cat
        fiche["sous_categorie"]= sub

        # Validation anti-contamination description
        if _description_contaminee(nom_commun, nom_latin, fiche.get("description", "")):
            retry = _groq(
                [{"role":"user","content":f"Décris {nom_commun} ({nom_latin}) en 2-3 phrases. Commence OBLIGATOIREMENT par 'Le {nom_commun} est' ou 'La {nom_commun} est'. Uniquement la description, rien d'autre."}],
                f"Tu es botaniste. Tu parles UNIQUEMENT de {nom_commun} ({nom_latin}).",
                temp=0.0, max_t=150
            ).strip()
            if not _description_contaminee(nom_commun, nom_latin, retry):
                fiche["description"] = retry
            elif wiki and wiki.get("resume"):
                fiche["description"] = wiki["resume"][:300]
            else:
                fiche["description"] = f"{nom_commun} ({nom_latin}) est une plante de la famille {fiche.get('famille', '')}."

        # Nettoyage associations (anti-hallucination)
        for champ_liste in ("associations_benefiques","associations_incompatibles","plantes_meme_ecosysteme"):
            if champ_liste in fiche:
                fiche[champ_liste] = _filter_associations(fiche[champ_liste])

        # CRITIQUE : écrase avec les valeurs certifiées Trefle
        # Groq ne peut plus halluciner ces champs
        for champ, valeur in trefle_certifie.items():
            fiche[champ] = valeur

        if trefle and trefle.get("toxicite_trefle"):
            fiche["toxicite_trefle"] = trefle["toxicite_trefle"]

        for k, v in FICHE_SCHEMA.items():
            fiche.setdefault(k, v)

        # Source tracée
        sources = ["wiki"]
        if trefle and trefle.get("source_trefle"):
            sources.append("trefle")
        sources.append("groq")
        fiche["source"] = "+".join(sources)

        return fiche
    except Exception as e:
        return {**FICHE_SCHEMA,"nom_commun":nom_commun,"nom_latin":nom_latin,
                "categorie":cat,"sous_categorie":sub,"source":f"error:{e}"}

def _valider_complement(complement: dict, nom_commun: str, nom_latin: str) -> dict:
    """
    Validation anti-contamination GLOBALE du JSON retourné par Groq.
    Pour chaque champ texte long, vérifie que la plante cible est mentionnée.
    Si le JSON parle globalement d'une autre plante (détection via description),
    on rejette le complément entier.
    Retourne le complement nettoyé (champs contaminés supprimés).
    """
    mots_cible = [m for m in nom_commun.lower().split() if len(m) > 3]
    genre_latin = nom_latin.lower().split()[0] if nom_latin else ""
    tous_mots = mots_cible + ([genre_latin] if genre_latin else [])

    if not tous_mots:
        return complement

    # Vérification globale sur la description : si elle parle clairement d'une autre plante
    # → rejeter TOUT le complement (Groq a halluciné sur la mauvaise plante)
    desc = complement.get("description", "")
    if desc and isinstance(desc, str) and len(desc) > 40:
        desc_low = desc.lower()
        if not any(m in desc_low for m in tous_mots):
            # La description parle d'une autre plante → on rejette TOUT
            return {}

    # Validation champ par champ pour les champs LONGS uniquement
    # Les champs courts/génériques (terreau, exposition, arrosage…) n'ont pas besoin
    # de mentionner le nom de la plante → on ne les rejette pas
    champs_texte_longs = {
        "description", "origine_naturelle", "ecosysteme_naturel",
        "biodiversite", "maladies_courantes", "ravageurs",
        "conseil_plantation", "conseil_entretien", "fructification",
    }
    cleaned = {}
    for k, v in complement.items():
        if k in champs_texte_longs and isinstance(v, str) and len(v) > 5:
            v_low = v.lower()
            if not any(m in v_low for m in tous_mots):
                # Ce champ parle d'une autre plante → on le rejette
                continue
        cleaned[k] = v
    return cleaned


def groq_enrichir(fiche: dict, champs_manquants: list, wiki: dict, trefle: dict = None) -> dict:
    """
    Complète les champs vides d'une fiche existante.
    Les données Trefle certifiées sont injectées DIRECTEMENT sans passer par Groq.
    Groq n'est appelé que pour ce que Trefle ne couvre pas.

    FIXES anti-contamination :
    - temp=0.0 (déterministe, élimine les hallucinations aléatoires)
    - Prompt répète le nom de la plante 4x pour ancrer le contexte
    - Validation globale : si Groq retourne la mauvaise plante → on rejette TOUT
    - NameError corrigé : enrichi_groq initialisé avant le bloc conditionnel
    """
    nom_commun = fiche.get("nom_commun","")
    nom_latin  = fiche.get("nom_latin","")
    enrichi_trefle = False
    enrichi_groq   = False  # ← FIX: défini ici pour éviter NameError

    # Injection directe Trefle (0 hallucination possible)
    if trefle and trefle.get("source_trefle"):
        mapping_direct = {
            "resistance_froid":  trefle.get("resistance_froid"),
            "hauteur_adulte":    trefle.get("hauteur_adulte"),
            "exposition":        trefle.get("exposition"),
            "arrosage_frequence":trefle.get("arrosage_frequence"),
            "sol_ph":            trefle.get("sol_ph"),
            "floraison":         trefle.get("floraison_mois"),
        }
        for champ, valeur in mapping_direct.items():
            if valeur and champ in champs_manquants and not fiche.get(champ):
                fiche[champ] = valeur
                enrichi_trefle = True
                champs_manquants = [c for c in champs_manquants if c != champ]
        if trefle.get("toxicite_trefle") and not fiche.get("toxicite_trefle"):
            fiche["toxicite_trefle"] = trefle["toxicite_trefle"]
            enrichi_trefle = True

    # Appel Groq uniquement pour les champs restants
    if champs_manquants:
        wb = _wiki_block(wiki, nom_commun)
        tb = _trefle_block(trefle or {}, nom_commun)
        champs_str = ", ".join(champs_manquants)
        champs_json_parts = []
        for c in champs_manquants:
            if c in ["associations_benefiques","associations_incompatibles","plantes_meme_ecosysteme","tags"]:
                champs_json_parts.append(f'"{c}":["..."]')
            else:
                champs_json_parts.append(f'"{c}":"..."')
        champs_json = "{" + ", ".join(champs_json_parts) + "}"

        # Prompt ultra-ancré : répète le nom 4x pour forcer Groq à rester sur la bonne plante
        system = (
            f"Tu es botaniste expert francophone spécialisé en {nom_commun} ({nom_latin}). "
            f"Tu complètes UNIQUEMENT et EXCLUSIVEMENT la fiche de {nom_commun} ({nom_latin}). "
            f"RÈGLE ABSOLUE : chaque valeur doit concerner {nom_commun} uniquement. "
            f"Ne mentionne JAMAIS une autre plante dans tes réponses texte. "
            f"Pour les associations, utilise UNIQUEMENT des noms communs français (pas de noms latins). "
            f"Pour terreau_recommande : utilise des NOMS DE SACS vendus en jardinerie : "
            f"'terreau universel', 'terre de bruyère', 'terreau méditerranéen', 'terreau cactus et plantes grasses', "
            f"'terreau plantes vertes', 'terreau potager', 'tourbe blonde'. Précise le mélange si besoin. "
            f"Réponds uniquement en JSON valide, sans markdown."
        )
        prompt = (
            f"PLANTE CIBLE : {nom_commun} ({nom_latin})\n"
            f"{wb}{tb}\n"
            f"RAPPEL : tu complètes la fiche de {nom_commun} ({nom_latin}) UNIQUEMENT.\n"
            f"Champs manquants à compléter pour {nom_commun} : {champs_str}\n"
            f"Réponds UNIQUEMENT avec ce JSON concernant {nom_commun} :\n"
            f"{champs_json}"
        )

        # temp=0.0 : déterministe, élimine les hallucinations aléatoires
        text = _groq([{"role":"user","content":prompt}], system, temp=0.0, max_t=800)
        try:
            complement = json.loads(text.replace("```json","").replace("```","").strip())

            # ── Validation anti-contamination GLOBALE ────────────────
            complement = _valider_complement(complement, nom_commun, nom_latin)
            # ─────────────────────────────────────────────────────────

            # PROTECTION : nom_commun et nom_latin ne sont JAMAIS écrasés
            complement.pop("nom_commun", None)
            complement.pop("nom_latin", None)

            for k, v in complement.items():
                if k in fiche and not fiche[k]:
                    if k in ("associations_benefiques","associations_incompatibles","plantes_meme_ecosysteme"):
                        v = _filter_associations(v)
                    fiche[k] = v
                    enrichi_groq = True
            if enrichi_groq:
                fiche["source"] = fiche.get("source","") + "+enrichi"
        except Exception:
            pass

    if enrichi_trefle or enrichi_groq:
        save_to_db(fiche)

    return fiche

def _clean_history(messages: list, max_messages: int = 20) -> list:
    """Nettoie l'historique pour Groq : garde UNIQUEMENT role+content.
    Supprime from_cache, is_alert et toute clé custom ajoutée par l'interface.
    Fenêtre glissante : garde les max_messages derniers échanges pour éviter
    les erreurs 400 'context length exceeded' sur les longues conversations."""
    cleaned = [
        {"role": m["role"], "content": m.get("content", "")}
        for m in messages
        if m.get("role") in ("user", "assistant") and m.get("content", "").strip()
    ]
    return cleaned[-max_messages:]


def groq_answer(fiche: dict, question: str, history: list) -> str:
    """Répond à une question sur une plante spécifique."""
    wiki   = fiche.get("wiki", {})
    trefle = fiche.get("trefle", {})
    nom    = fiche.get("nom_commun", "")

    # System compact pour éviter le 400
    wiki_resume = ""
    if wiki.get("toxicite"):
        wiki_resume = f"⚠️ TOXICITÉ : {wiki['toxicite']}"
    elif wiki.get("resume"):
        wiki_resume = "Wikipedia : " + wiki["resume"][:300]

    trefle_line = ""
    if trefle and trefle.get("source_trefle"):
        parts = []
        for k, label in [("resistance_froid","froid"), ("hauteur_adulte","hauteur"),
                         ("exposition","expo"), ("arrosage_frequence","eau"), ("sol_ph","pH")]:
            if trefle.get(k): parts.append(f"{label}={trefle[k]}")
        if trefle.get("toxicite_trefle"): parts.append(trefle["toxicite_trefle"])
        if parts: trefle_line = "Trefle : " + " | ".join(parts)

    context = get_context(fiche, question)

    system = f"""Tu es à la fois un écologiste scientifique rigoureux et un vendeur passionné en jardinerie.

RÈGLES STRICTES :
- Faits vrais et vérifiés uniquement. Si tu n'es pas sûr, dis-le.
- Prose directe, comme si tu parlais à un client en magasin. JAMAIS de titres, JAMAIS de bullet points.
- Maximum 5-6 lignes. Va à l'essentiel, pas de remplissage.
- Si toxique ou danger : commence OBLIGATOIREMENT par ⚠️ ATTENTION.
- Parle UNIQUEMENT de ce qui est demandé. Si on ne demande pas les associations, n'en parle PAS.
- Toujours écrire nom commun suivi du nom latin entre parenthèses.
- Pour le substrat : utilise des noms de sacs commerciaux (terreau universel, terre de bruyère, terreau méditerranéen, terreau cactus, terreau potager…).
- Pour les conseils pratiques : gestes concrets, saisons précises.
- Ne pose JAMAIS de questions à l'utilisateur.
- Ne répète pas les informations déjà données.
- ORTHOGRAPHE : vérifie chaque mot. Aucune faute tolérée.
Plante : {nom} ({fiche.get('nom_latin','')}).
expo={fiche.get('exposition','')} | sol={fiche.get('sol_type','')} | arrosage={fiche.get('arrosage_frequence','')} | froid={fiche.get('resistance_froid','')}
Bénéfiques : {', '.join(fiche.get('associations_benefiques',[])[:5])}
Incompatibles : {', '.join(fiche.get('associations_incompatibles',[])[:3])}
{wiki_resume}
{trefle_line}
{context}"""

    # Nettoie l'historique : supprime from_cache, is_alert etc. que Groq rejette
    return _groq(_clean_history(history), system)

def _validate_question(messages: list) -> str | None:
    if not messages: return None
    last = messages[-1].get("content", "").strip()
    if not last:
        return "Je n'ai pas reçu de message 🤔 Pose-moi ta question !"
    words = last.split()
    # Message très court sans ponctuation → probablement incomplet
    if len(words) == 1 and len(last) < 4 and not any(c in last for c in ["?","!"]):
        return f"Je ne suis pas sûr de comprendre '{last}'. Tu peux préciser ta question sur les plantes ?"
    return None

def _detecter_plante_dans_message(message: str) -> tuple[str, str] | None:
    """
    Détecte une plante dans le message utilisateur.
    1. Vérifie qu'il y a au moins un mot de 4+ lettres (sinon pas une plante)
    2. Cherche d'abord dans la DB locale — si match, retourne sans appeler Groq.
    3. Sinon, appelle Groq avec instructions strictes.
    """
    from memory import search_db

    msg_low = message.lower()

    # ── GARDE-FOU : si aucun mot ≥ 4 lettres → impossible que ce soit une plante
    # Ex: "bzh", "ok", "lol" → retour immédiat, Groq n'est PAS appelé
    _mots_longs = [
        re.sub(r"[^a-zàâäéèêëîïôùûüç]", "", w)
        for w in msg_low.split()
    ]
    _mots_longs = [m for m in _mots_longs if len(m) >= 4]
    if not _mots_longs:
        return None

    # ── PRIORITÉ 0 : synonymes courants → retour immédiat sans Groq ──────────
    for _expr, _plant in SYNONYMES_PLANTES.items():
        if _expr in msg_low:
            print(f"[SYNONYME] '{_expr}' → {_plant[0]}")
            return _plant

    # ── PRIORITÉ 1 : cherche dans la DB sans appeler Groq ──────────────────────
    # Mots trop courts ou trop génériques pour identifier une plante en DB :
    # - seuil minimum : 5 caractères (évite "nice", "rose", "rond"…)
    # - stop-words géographiques / courants qui matchent des sous-chaînes de noms latins
    _STOP_WORDS_DB = {
        "nice", "rome", "paris", "lyon", "nord", "rond", "ronde", "rondes",
        "avec", "pour", "dans", "elle", "elles", "leur", "leurs",
        "comme", "aussi", "mais", "donc", "alors", "même", "très", "bien",
        "tout", "tous", "dont", "quand", "comment", "plant", "jardin",
    }
    _mots_db = [w for w in _mots_longs if len(w) >= 5 and w not in _STOP_WORDS_DB]

    for _w in _mots_db:
        _hits = search_db(_w)
        for _h in _hits:
            _nc = _h.get("nom_commun", "")
            _nl = _h.get("nom_latin", "")
            if not _nc:
                continue
            # Word boundary matching — évite "nice" ⊂ "lonicera grimpant"
            _nc_low = _nc.lower()
            _word_match = bool(re.search(r'\b' + re.escape(_w) + r'\b', _nc_low))
            _phrase_match = _nc_low in msg_low
            if _word_match or _phrase_match:
                print(f"[DETECT DB] '{_nc}' trouvé en DB pour mot '{_w}'")
                return _nc, _nl
    # ───────────────────────────────────────────────────────────────────────────

    # ── PRIORITÉ 2 : Groq (plantes inconnues en DB) ────────────────────────────
    prompt = f"""Analyse ce message et détecte s'il mentionne une plante, fleur, arbre, arbuste, légume ou végétal.
Message : "{message}"

RÈGLES ABSOLUES :
- COPIE le nom de la plante EXACTEMENT tel qu'il apparaît dans le message. NE TRADUIS PAS. NE CORRIGE PAS.
  Ex : "sauge" → nom_commun="Sauge"  (PAS "Saucisse", PAS "Salvia")
- Prends les variétés : "saule crevette", "rose trémière", "bouleau pleureur"
- Prends les noms composés : "arbre à papillons", "laurier rose", "arbre de Judée"

Exemples :
- "parle moi de la sauge" → {{"nom_commun":"Sauge","nom_latin":"Salvia officinalis"}}
- "j'ai vu des cordylines" → {{"nom_commun":"Cordyline","nom_latin":"Cordyline fruticosa"}}
- "quel engrais utiliser ?" → null

Si une plante est présente, réponds UNIQUEMENT en JSON :
{{"nom_commun":"nom COPIÉ du message","nom_latin":"genre espèce"}}
Sinon : null"""
    text = _groq(
        [{"role":"user","content":prompt}],
        "Tu es botaniste expert. COPIE le nom de la plante tel quel depuis le message, sans traduire ni corriger. Réponds UNIQUEMENT JSON valide ou null.",
        temp=0.0, max_t=120
    )
    text = text.strip().replace("```json","").replace("```","").strip()
    if text.lower() in ["null","none",""]:
        return None
    m = re.search(r'\{[^{}]+\}', text)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        nom_c = data.get("nom_commun","").strip()
        nom_l = data.get("nom_latin","").strip()
        if nom_c and len(nom_c) > 2:
            # Rejeter les non-plantes
            if nom_c.lower() in _NON_PLANTES:
                return None
            # Vérification de cohérence : le nom détecté doit avoir un lien
            # avec le message original (au moins 3 caractères communs en séquence,
            # ou le genre latin présent dans le message).
            # Ça bloque "saucisse" quand le message dit "sauge".
            msg_low  = message.lower()
            nom_low  = nom_c.lower()
            genre_l  = nom_l.lower().split()[0] if nom_l else ""
            # 1. Le nom (ou un mot du nom) est dans le message ?
            nom_mots = [w for w in nom_low.split() if len(w) >= 4]
            if any(w in msg_low for w in nom_mots):
                return nom_c, nom_l
            # 2. Le genre latin est dans le message ?
            if genre_l and len(genre_l) >= 4 and genre_l in msg_low:
                return nom_c, nom_l
            # 3. Au moins 4 caractères contigus du nom sont dans le message ?
            found = any(
                nom_low[i:i+4] in msg_low
                for i in range(len(nom_low) - 3)
            )
            if found:
                return nom_c, nom_l
            # Aucun lien → hallucination Groq, on rejette
            print(f"[ANTI-HALLUC] '{nom_c}' rejeté pour message '{message[:40]}'")
            return None
    except Exception:
        pass
    return None


# ══════════════════════════════════════════════════════════════════
# COUCHE 4 — PLANTNET (identification photo)
# ══════════════════════════════════════════════════════════════════
def _fetch_image_bytes(url: str) -> bytes | None:
    """
    Télécharge une image côté serveur Python (pas de restriction CORS).
    Essaie PlantNet d'abord, puis Wikipedia comme fallback.
    Retourne les bytes de l'image ou None si échec.
    """
    if not url:
        return None
    try:
        r = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; Slothia/1.0)"
        }, timeout=8)
        if r.status_code == 200 and r.headers.get("Content-Type","").startswith("image"):
            return r.content
    except Exception:
        pass
    return None


def _fetch_wiki_image(nom_latin: str, nom_commun: str) -> bytes | None:
    """
    Récupère la photo en bytes avec plusieurs stratégies :
    1. Wikipedia FR (résumé + originalimage)
    2. Wikipedia EN
    3. Wikimedia Commons (cherche par nom latin — énorme base d'images botaniques)
    """
    headers = {"Accept": "application/json", "User-Agent": "Slothia/1.0"}

    # 1 & 2 — Wikipedia FR puis EN
    for lang, query in [("fr", nom_latin), ("fr", nom_commun), ("en", nom_latin), ("en", nom_commun)]:
        if not query:
            continue
        try:
            r = requests.get(
                f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}",
                headers=headers, timeout=6
            )
            if r.status_code == 200:
                data  = r.json()
                thumb = data.get("originalimage") or data.get("thumbnail")
                if thumb and thumb.get("source"):
                    img = _fetch_image_bytes(thumb["source"])
                    if img:
                        return img
        except Exception:
            continue

    # 3 — Wikimedia Commons : cherche par nom latin via API MediaWiki
    if nom_latin:
        try:
            # Cherche les fichiers image associés au nom latin
            r = requests.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query",
                    "generator": "search",
                    "gsrnamespace": "6",        # NS 6 = File:
                    "gsrsearch": nom_latin,
                    "gsrlimit": "5",
                    "prop": "imageinfo",
                    "iiprop": "url|mime",
                    "format": "json",
                },
                headers=headers, timeout=8
            )
            if r.status_code == 200:
                pages = r.json().get("query", {}).get("pages", {})
                for page in pages.values():
                    info = page.get("imageinfo", [{}])[0]
                    mime = info.get("mime", "")
                    url  = info.get("url", "")
                    if url and mime.startswith("image/") and "svg" not in mime:
                        img = _fetch_image_bytes(url)
                        if img:
                            return img
        except Exception:
            pass

    return None


def identify_photo(image_bytes: bytes) -> tuple[list, str]:
    """
    Retourne les 3 meilleurs résultats PlantNet.
    Les photos de référence sont téléchargées côté serveur Python
    (contourne CORS et restrictions navigateur) — fallback Wikipedia.
    """
    if not PLANTNET_KEY:
        return None, "⚠️ PLANTNET_API_KEY manquante dans le fichier .env"
    try:
        # Détection MIME réelle (réutilise la même logique que groq_vision_chat)
        def _detect_mime_local(b: bytes) -> str:
            if b[:8] == b'\x89PNG\r\n\x1a\n': return "image/png"
            if b[:4] == b'RIFF' and b[8:12] == b'WEBP': return "image/webp"
            return "image/jpeg"
        _mime = _detect_mime_local(image_bytes)
        _ext  = {"image/png": "photo.png", "image/webp": "photo.webp"}.get(_mime, "photo.jpg")

        r = requests.post(
            f"https://my-api.plantnet.org/v2/identify/all?api-key={PLANTNET_KEY}&lang=fr",
            files=[("images", (_ext, image_bytes, _mime))],
            data={"organs":["auto"]}, timeout=30
        )
        r.raise_for_status()
        results = r.json().get("results",[])
        if not results:
            return None, "Aucune plante reconnue. Essaie avec une photo plus nette."
        candidats = []
        for res in results[:3]:
            score     = res.get("score", 0)
            names     = res["species"].get("commonNames", [])
            nom_c     = names[0] if names else res["species"].get("scientificNameWithoutAuthor", "Inconnu")
            nom_l     = res["species"].get("scientificNameWithoutAuthor", "")
            famille   = res["species"].get("family", {}).get("scientificNameWithoutAuthor", "")

            # 1. Essaie les URLs PlantNet (téléchargement serveur, pas navigateur)
            photo_bytes = None
            images = res.get("images", [])
            for img_data in images[:3]:  # essaie jusqu'à 3 images PlantNet
                url = img_data.get("url", {}).get("m", "") or img_data.get("url", {}).get("s", "")
                photo_bytes = _fetch_image_bytes(url)
                if photo_bytes:
                    break

            # 2. Fallback Wikipedia si PlantNet échoue
            if not photo_bytes:
                photo_bytes = _fetch_wiki_image(nom_l, nom_c)

            candidats.append({
                "nom_commun":  nom_c,
                "nom_latin":   nom_l,
                "famille":     famille,
                "score":       round(score * 100, 1),
                "confiance":   "élevée" if score > 0.7 else "moyenne" if score > 0.4 else "faible",
                "photo_bytes": photo_bytes,  # bytes ou None
            })
        return candidats, None
    except Exception as e:
        return None, f"Erreur PlantNet : {e}"


# ══════════════════════════════════════════════════════════════════
# PIPELINES PRINCIPAUX
# ══════════════════════════════════════════════════════════════════
def _terreau_pour_plante(nom_commun: str, nom_latin: str, categorie: str = "") -> str:
    """
    Retourne le terreau recommandé pour une plante.
    Priorité : TERREAU_COMPOSITIONS (exact) → nom latin genre → catégorie → ""
    """
    # 1. Recherche exacte dans TERREAU_COMPOSITIONS
    for cle, compo in TERREAU_COMPOSITIONS.items():
        if cle.lower() in nom_commun.lower() or nom_commun.lower() in cle.lower():
            return compo

    # 2. Recherche par genre latin (ex: "Lavandula" → "Lavande")
    genre_latin = nom_latin.lower().split()[0] if nom_latin else ""
    _correspondances_genre = {
        "lavandula": "100 % terreau méditerranéen",
        "salvia rosmarinus": "100 % terreau méditerranéen",
        "thymus": "100 % terreau méditerranéen",
        "origanum": "100 % terreau méditerranéen",
        "cistus": "100 % terreau méditerranéen",
        "olea": "100 % terreau méditerranéen",
        "agave": "60 % terreau méditerranéen + 40 % pouzzolane",
        "aloe": "60 % terreau cactus + 40 % pouzzolane",
        "echeveria": "60 % terreau cactus + 40 % pouzzolane",
        "sedum": "60 % terreau cactus + 40 % pouzzolane",
        "sempervivum": "60 % terreau cactus + 40 % pouzzolane",
        "opuntia": "60 % terreau cactus + 40 % pouzzolane",
        "mammillaria": "60 % terreau cactus + 40 % pouzzolane",
        "rhododendron": "100 % terre de bruyère",
        "hydrangea": "80 % terre de bruyère + 20 % terreau universel",
        "camellia": "100 % terre de bruyère",
        "pieris": "100 % terre de bruyère",
        "vaccinium": "100 % terre de bruyère",
        "phalaenopsis": "100 % terreau orchidée",
        "dendrobium": "100 % terreau orchidée",
        "orchid": "100 % terreau orchidée",
        "monstera": "60 % terreau plante verte + 40 % terreau orchidée",
        "philodendron": "70 % terreau plante verte + 30 % terreau orchidée",
        "calathea": "70 % terreau plante verte + 30 % tourbe",
        "dracaena": "100 % terreau plante verte",
        "ficus": "100 % terreau plante verte",
        "solanum lycopersicum": "100 % terreau potager",
        "cucurbita": "100 % terreau potager",
        "lactuca": "100 % terreau potager",
        "brassica": "100 % terreau potager",
    }
    for k, v in _correspondances_genre.items():
        if genre_latin.startswith(k[:6]) or k in nom_latin.lower():
            return v

    # 3. Fallback par catégorie
    _terreau_par_categorie = {
        "plantes_vertes":       "terreau plante verte",
        "plantes_grasses":      "60 % terreau cactus + 40 % pouzzolane",
        "rosiers":              "terreau plantation ou terreau universel enrichi",
        "plantes_grimpantes":   "terreau universel",
        "plantes_aromatiques":  "terreau méditerranéen ou terreau universel selon l'espèce",
        "potageres":            "terreau potager",
        "plantes_aquatiques":   "terre végétale ou terreau de bassin (sans tourbe)",
        "plantes_aquarium":     "substrat spécial aquarium (gravillon fin ou sable de rivière)",
        "plantes_carnivores":   "50 % tourbe blonde non fertilisée + 50 % sable de rivière — JAMAIS de terreau classique",
        "arbres_arbustes":      "terreau plantation + terre végétale",
        "graminees":            "terreau universel",
        "fougeres":             "70 % terre de bruyère + 30 % terreau plante verte",
        "plantes_vivaces":      "terreau universel ou terreau plantation",
        "plantes_annuelles":    "terreau universel",
        "plantes_bisannuelles": "terreau universel",
        "plantes_sauvages":     "terre végétale ou en pleine terre directement",
        "plantes_eco_solution": "terreau universel ou en pleine terre",
        "chrysanthemes":        "terreau universel",
        "plantes_fetes":        "terreau universel",
    }
    if categorie in _terreau_par_categorie:
        return _terreau_par_categorie[categorie]

    return ""


def get_or_create_fiche(nom_commun: str, nom_latin: str) -> tuple[dict, bool]:
    """
    Pipeline complet :
    1. Cache local   → retourne si trouvé
    2. Si incomplet  → enrichit (Trefle direct + Groq pour le reste)
    3. Wikipedia     → faits vérifiés en français
    4. Trefle.io     → données chiffrées certifiées
    5. Groq          → synthèse + enrichissement francophone
    6. Sauvegarde
    """
    # Valeurs par défaut — seront écrasées par les valeurs DB si la fiche existe
    nom_commun_db = nom_commun
    nom_latin_db  = nom_latin
    cached = load_from_db(nom_latin, nom_commun)
    if cached:
        # ══ LATIN EN PREMIER : si le nom latin correspond → fiche valide ══════
        # Le nom_commun DB est autoritaire. Peu importe le nom demandé.
        # Ex: on demande ("Saucisse", "Salvia officinalis")
        #     → trouve fiche {"Sauge", "Salvia officinalis"} → latin matche → OK
        _cached_nl = cached.get("nom_latin", "").lower().strip()
        _req_nl    = nom_latin.lower().strip()
        _latin_ok  = bool(
            _req_nl and _cached_nl and
            (_req_nl == _cached_nl or _req_nl.split()[0] == _cached_nl.split()[0])
        )
        if _latin_ok:
            # Latin confirme → fiche correcte, on garde, on ne touche pas au nom
            pass
        else:
            # Latin ne matche pas → vérif par nom commun (mots entiers)
            _cached_nc   = cached.get("nom_commun", "").lower()
            _req_nc      = nom_commun.lower()
            _words_req   = _req_nc.split()
            _has_overlap = any(w in _cached_nc for w in _words_req)
            if not _has_overlap:
                # Aucun lien latin ni nom → mauvaise fiche → chercher par nom commun
                print(f"[ANTI-CONTAM] '{_cached_nc}' != '{_req_nc}' et latin différent → recherche par nom commun")
                cached = load_from_db(nom_commun, nom_commun)
        # ════════════════════════════════════════════════════════════════════════

    if cached:
        needs_save = False

        # ── Fix catégorie incorrecte (ex: potager tombé dans ornement) ──
        cat_actuelle = cached.get("categorie", "")
        cat_correcte, sub_correcte = detect_category(nom_latin, nom_commun)
        if cat_actuelle != cat_correcte:
            cached["categorie"]      = cat_correcte
            cached["sous_categorie"] = sub_correcte
            needs_save = True

        # ══ ANTI-CONTAMINATION NUCLÉAIRE ════════════════════════════════════
        # Si la description ou l'arrosage mentionne une AUTRE plante par son nom,
        # on force la régénération complète (cached = None → pipeline Wikipedia+Groq).
        # C'est plus fiable que de vider des champs un par un.
        _mots_cible = nom_commun.lower().split()
        _genre_lat  = nom_latin.lower().split()[0] if nom_latin else ""
        _cibles     = _mots_cible + ([_genre_lat] if _genre_lat and len(_genre_lat) > 3 else [])

        if _cibles:
            _desc  = cached.get("description", "")
            _arro  = cached.get("arrosage_frequence", "")
            _maladies = cached.get("maladies_courantes", "")
            # Si un champ long ne mentionne pas la plante cible → contamination certaine
            for _champ_test in [_desc, _arro, _maladies]:
                if _champ_test and len(_champ_test) > 60:
                    if not any(m in _champ_test.lower() for m in _cibles):
                        print(f"[ANTI-CONTAM NUCL.] '{nom_commun}' — champ contaminé détecté → régénération complète")
                        # Supprimer le fichier DB corrompu pour forcer un pipeline complet
                        from memory import _safe, DB_ROOT
                        _cat = cached.get("categorie", "plantes_vivaces")
                        _sub = cached.get("sous_categorie", "divers")
                        _bad_path = DB_ROOT / _cat / _sub / f"{_safe(cached.get('nom_latin','unknown'))}.json"
                        if _bad_path.exists():
                            _bad_path.unlink()
                            print(f"[ANTI-CONTAM NUCL.] Fichier supprimé : {_bad_path}")
                        cached = None
                        break
        # ════════════════════════════════════════════════════════════════════

    # Si la contamination a forcé cached = None, on passe directement au pipeline complet
    if cached:
        needs_save = False

        # ── Fix associations avec genres latins en cache ─────────────
        _assoc_fields = ("associations_benefiques", "associations_incompatibles", "plantes_meme_ecosysteme")
        _assoc_corrected = False
        for _af in _assoc_fields:
            _items = cached.get(_af, [])
            if isinstance(_items, list) and _items:
                _filtered = _filter_associations(_items)
                if len(_filtered) < len(_items):  # des items ont été supprimés
                    cached[_af] = _filtered
                    _assoc_corrected = True
                    # Force ré-enrichissement si la liste est maintenant vide
                    if not _filtered and _af not in [c for c in CHAMPS_ESSENTIELS]:
                        pass  # sera ajouté manuellement ci-dessous si besoin
        if _assoc_corrected:
            needs_save = True
            # Si associations_benefiques est vide après nettoyage → forcer ré-enrichissement
            if not cached.get("associations_benefiques"):
                cached["associations_benefiques"] = []

        # ── Fix trefle.famille_trefle dict → string ──────────────────
        _trefle_cache = cached.get("trefle", {})
        if isinstance(_trefle_cache.get("famille_trefle"), dict):
            _fam = _trefle_cache["famille_trefle"]
            _trefle_cache["famille_trefle"] = _fam.get("name", "") or _fam.get("common_name", "") or ""
            cached["trefle"] = _trefle_cache
            needs_save = True

        if not cached.get("wiki", {}).get("image"):
            _img = _fetch_plant_image_url(nom_latin, nom_commun)
            if _img:
                cached.setdefault("wiki", {})["image"] = _img
                needs_save = True

        if needs_save:
            save_to_db(cached)

        champs_vides = [
            c for c in CHAMPS_ESSENTIELS
            if not cached.get(c) or cached.get(c) == [] or cached.get(c) == ""
        ]

        # ── TERREAU : pré-remplir depuis TERREAU_COMPOSITIONS avant Groq ────
        # Évite de dépendre de groq_enrichir pour un info qu'on connaît déjà
        if "terreau_recommande" in champs_vides:
            _compo = _terreau_pour_plante(nom_commun_db, nom_latin_db, cached.get("categorie", ""))
            if _compo:
                cached["terreau_recommande"] = _compo
                champs_vides.remove("terreau_recommande")
                needs_save = True
        # ─────────────────────────────────────────────────────────────────────
        # Ajoute les associations vides (après nettoyage genres latins) si pas déjà dedans
        for _af in ("associations_benefiques", "associations_incompatibles", "plantes_meme_ecosysteme"):
            if (not cached.get(_af) or cached.get(_af) == []) and _af not in champs_vides:
                champs_vides.append(_af)
        # RÈGLE ABSOLUE : utiliser le nom_commun de la DB pour groq_enrichir
        # Si on utilise le nom demandé ("Saucisse"), Groq contamine la fiche
        nom_commun_db = cached.get("nom_commun", nom_commun)
        nom_latin_db  = cached.get("nom_latin",  nom_latin)

        if champs_vides:
            print(f"[DEBUG] {nom_commun_db} — champs vides déclenchant groq_enrichir : {champs_vides}")
        if champs_vides:
            # ── FIX CRITIQUE : Wikipedia doit être fetché si resume absent ──
            # Sans resume, Groq n'a aucun contexte et peut halluciner sur la mauvaise plante
            wiki_actuel = cached.get("wiki", {})
            if not wiki_actuel.get("resume"):
                wiki_frais = wikipedia_fetch(nom_commun, nom_latin)
                if wiki_frais:
                    # Fusionne sans écraser l'image déjà présente
                    img_existante = wiki_actuel.get("image", "")
                    cached["wiki"] = wiki_frais
                    if img_existante and not wiki_frais.get("image"):
                        cached["wiki"]["image"] = img_existante
                    if not cached.get("famille") and wiki_frais.get("famille"):
                        cached["famille"] = wiki_frais["famille"]
                    if not cached.get("origine_naturelle") and wiki_frais.get("origine"):
                        cached["origine_naturelle"] = wiki_frais["origine"]
                    if wiki_frais.get("toxicite"):
                        cached["toxicite_wiki"] = wiki_frais["toxicite"]
                    save_to_db(cached)
            if not cached.get("trefle"):
                trefle = trefle_fetch(nom_latin)
                if trefle:
                    cached["trefle"] = trefle
                    save_to_db(cached)
            cached = groq_enrichir(
                cached, champs_vides,
                cached.get("wiki", {}),
                cached.get("trefle", {}),
            )
            # Restaurer le nom DB après groq_enrichir (protection finale)
            cached["nom_commun"] = nom_commun_db
            cached["nom_latin"]  = nom_latin_db
        return cached, True

    # Nouvelle plante — mais d'abord vérifier si le nom_latin n'est pas une hallucination
    # Cas typique : suggest_plants a retourné le bon nom commun mais le latin d'une autre plante
    # → load_from_db a tout rejeté (protection genre latin) → on cherche une dernière fois par nom commun seul
    if nom_latin and nom_latin.lower() != nom_commun.lower():
        _fallback = load_from_db(nom_commun, nom_commun)
        if _fallback:
            _fb_nc = _fallback.get("nom_commun", "").lower()
            _words_req = nom_commun.lower().split()
            if _words_req and any(w in _fb_nc for w in _words_req):
                # Le nom commun correspond → on a trouvé la bonne fiche via nom commun seul
                # Corrige le nom_latin dans la fiche si nécessaire
                print(f"[FALLBACK] Trouvé '{_fb_nc}' par nom commun seul (latin '{nom_latin}' était probablement hallucination)")
                return _fallback, True

    # Pipeline complet — vraiment nouvelle plante
    wiki   = wikipedia_fetch(nom_commun, nom_latin)
    trefle = trefle_fetch(nom_latin)
    fiche  = groq_fiche(nom_commun, nom_latin, wiki, trefle)

    if wiki:
        fiche["wiki"] = wiki
        if not fiche.get("famille") and wiki.get("famille"):
            fiche["famille"] = wiki["famille"]
        if not fiche.get("origine_naturelle") and wiki.get("origine"):
            fiche["origine_naturelle"] = wiki["origine"]
        if wiki.get("toxicite"):
            fiche["toxicite_wiki"] = wiki["toxicite"]

    if trefle:
        fiche["trefle"] = trefle
        if trefle.get("toxicite_trefle"):
            fiche["toxicite_trefle"] = trefle["toxicite_trefle"]

    # ── Terreau : pré-remplir si Groq n'a pas réussi à le renseigner ──────────
    if not fiche.get("terreau_recommande"):
        _compo = _terreau_pour_plante(nom_commun, nom_latin, fiche.get("categorie", ""))
        if _compo:
            fiche["terreau_recommande"] = _compo
    # ──────────────────────────────────────────────────────────────────────────

    save_to_db(fiche)
    return fiche, False


def ask_plant(fiche: dict, question: str, history: list) -> tuple[str, bool]:
    """
    1. Cache Q&A  → réponse instantanée si trouvée
    2. Wikipedia  → récupère si absent
    3. Trefle     → récupère si absent
    4. Groq       → répond et mémorise
    """
    cached = find_cached_answer(fiche, question)
    if cached:
        return cached["answer"], True

    if not fiche.get("wiki"):
        wiki = wikipedia_fetch(fiche.get("nom_commun",""), fiche.get("nom_latin",""))
        if wiki:
            fiche["wiki"] = wiki
            if wiki.get("toxicite"):
                fiche["toxicite_wiki"] = wiki["toxicite"]
            save_to_db(fiche)

    if not fiche.get("trefle"):
        trefle = trefle_fetch(fiche.get("nom_latin",""))
        if trefle:
            fiche["trefle"] = trefle
            if trefle.get("toxicite_trefle"):
                fiche["toxicite_trefle"] = trefle["toxicite_trefle"]
            save_to_db(fiche)

    answer = groq_answer(fiche, question, history)
    add_qa(fiche, question, answer)
    _enrichir_depuis_reponse(fiche, question, answer)
    return answer, False


def _enrichir_depuis_reponse(fiche: dict, question: str, answer: str):
    """
    Extrait les infos de la réponse Groq pour enrichir la fiche.
    Ne touche jamais aux champs déjà remplis par Trefle.
    """
    q = question.lower()
    enrichi = False

    if not fiche.get("resistance_froid") and any(w in q for w in ["froid","gel","rusticité","hiver","résiste","température"]):
        m = re.search(r'(-?\d+)\s*°C', answer)
        if m:
            fiche["resistance_froid"] = m.group(0)
            enrichi = True

    if not fiche.get("hauteur_adulte") and any(w in q for w in ["hauteur","grand","taille","mesure","pousse"]):
        m = re.search(r'(\d+[\-–]\d+\s*(?:m|cm)|environ\s*\d+\s*(?:m|cm))', answer, re.IGNORECASE)
        if m:
            fiche["hauteur_adulte"] = m.group(0)
            enrichi = True

    if not fiche.get("floraison") and any(w in q for w in ["fleur","fleurit","floraison","fleurir"]):
        for mois in ["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"]:
            if mois in answer.lower():
                idx = answer.lower().index(mois)
                # Fenêtre autour du mois — on vérifie que c'est bien un contexte de floraison
                fenetre = answer[max(0,idx-40):idx+80].lower()
                if any(k in fenetre for k in ["floraison","fleurit","fleur","fleurs","bouton"]):
                    fiche["floraison"] = answer[max(0,idx-20):idx+60].strip()
                    enrichi = True
                    break

    if not fiche.get("exposition") and any(w in q for w in ["soleil","ombre","exposition","lumière"]):
        for val in ["plein soleil","mi-ombre","ombre totale","ombre partielle"]:
            if val in answer.lower():
                fiche["exposition"] = val
                enrichi = True
                break

    if enrichi:
        fiche["source"] = fiche.get("source","") + "+auto"
        save_to_db(fiche)


def groq_chat(messages: list, context_filters: list = None, fiche_hint: dict = None) -> tuple[str, dict | None]:
    """
    Chat libre intelligent :
    1. Valide le message
    2. Détecte si une plante est mentionnée
    3. Si oui → crée/enrichit la fiche (wiki + trefle + groq)
    4. Si non et fiche_hint fourni → réutilise le contexte de la fiche précédente
    5. Répond avec le contexte de la fiche si disponible
    """
    err = _validate_question(messages)
    if err:
        return err, None

    dernier = messages[-1].get("content","") if messages else ""
    plante_info = _detecter_plante_dans_message(dernier)

    fiche_contexte = None
    contexte_fiche = ""
    nom_c = ""
    nom_l = ""

    if plante_info:
        nom_c, nom_l = plante_info
        fiche_contexte, _ = get_or_create_fiche(nom_c, nom_l or nom_c)
    elif fiche_hint:
        # ── Continuité de contexte : réutilise la fiche de la dernière plante
        # UNIQUEMENT si le message ressemble à une question de suivi.
        # Critères : message court (≤8 mots) OU commence par un mot de liaison.
        # Évite d'injecter le contexte tomate quand l'utilisateur change de sujet.
        _MOTS_CONTINUATION = {
            "et", "aussi", "comment", "pourquoi", "quel", "quelle", "quels", "quelles",
            "quand", "alors", "donc", "mais", "encore", "sinon", "autrement",
            "combien", "depuis", "pendant", "après", "avant", "ok", "okay",
        }
        _mots_msg = dernier.lower().split()
        _est_court = len(_mots_msg) <= 8
        _commence_par_liaison = bool(_mots_msg) and _mots_msg[0] in _MOTS_CONTINUATION
        if _est_court or _commence_par_liaison:
            fiche_contexte = fiche_hint
            nom_c = fiche_hint.get("nom_commun", "")
            print(f"[HINT] Continuation → fiche '{nom_c}' réutilisée pour : '{dernier[:40]}'")
        else:
            print(f"[HINT] Message hors-contexte → fiche_hint ignorée : '{dernier[:40]}'")

    if fiche_contexte:
        nom_c = fiche_contexte.get("nom_commun", nom_c if plante_info else "")
        trefle = fiche_contexte.get("trefle", {})
        # ⚠️ On injecte UNIQUEMENT les données techniques dans le contexte.
        # Les associations/incompatibilités NE sont pas injectées ici :
        # elles seront mentionnées par Groq SEULEMENT si l'utilisateur les demande.
        # Les champs vides sont exclus pour éviter le bruit dans le prompt.
        def _ctx_line(label: str, key: str) -> str:
            val = fiche_contexte.get(key, "")
            if isinstance(val, list): val = ", ".join(str(x) for x in val if x)
            return f"- {label} : {val}" if val else ""
        _ctx_lines = [
            _ctx_line("Exposition",       "exposition"),
            _ctx_line("Sol",              "sol_type"),
            _ctx_line("Terreau",          "terreau_recommande"),
            _ctx_line("Arrosage",         "arrosage_frequence"),
            _ctx_line("Résistance froid", "resistance_froid"),
            _ctx_line("Hauteur",          "hauteur_adulte"),
            _ctx_line("Floraison",        "floraison"),
        ]
        _ctx_body = "\n".join(l for l in _ctx_lines if l)
        contexte_fiche = f"""
Fiche technique disponible pour {nom_c} :
{_ctx_body}
{_wiki_block(fiche_contexte.get('wiki',{}), nom_c)}
{_trefle_block(trefle, nom_c)}
{get_context(fiche_contexte, dernier)}"""

    # Détecter si la question porte sur les associations pour les injecter seulement si besoin
    _q_lower = dernier.lower()
    _asks_assoc = any(w in _q_lower for w in [
        "associer","compagnon","voisin","planter avec","compatible","incompatible",
        "éviter","mélanger","association","s'entend","côte à côte","voisinage"
    ])
    if fiche_contexte and _asks_assoc:
        contexte_fiche += f"""
- Associations bénéfiques : {', '.join(fiche_contexte.get('associations_benefiques',[]))}
- Incompatibilités : {', '.join(fiche_contexte.get('associations_incompatibles',[]))}"""

    # ── Détecter contexte terreau / substrat ─────────────────────────────────
    _mots_terreau = ["terreau","substrat","terre","sol","mélange","pouzzolane","drainage",
                     "planter","plantation","rempoter","rempotage","pot","bac","bruyère"]
    _asks_terreau = any(w in _q_lower for w in _mots_terreau)
    _terreau_ctx  = ""
    if _asks_terreau and fiche_contexte:
        _eco = fiche_contexte.get("ecosysteme_naturel", "")
        _tc  = _terreau_context(fiche_contexte.get("nom_commun",""), _eco)
        if _tc:
            _terreau_ctx = "\n\nCONTEXTE TERREAU (source de vérité) :\n" + _tc

    # ── Détecter le contexte maladie / urgence ───────────────────────────────
    _mots_maladie = [
        "tache","taches","jaunit","jaunisse","jaunissement","fane","fanée","meurt",
        "morte","mourant","pourrit","pourriture","moisissure","moisit","moisie",
        "rongé","attaqué","ravageur","insecte","puceron","araignée","champignon",
        "brûlé","brûlure","nécrose","nécrosé","déformation","bizarre","étrange",
        "problème","souci","aide","sauver","sauve","sauvé","urgence","urgent","help"
    ]
    _is_maladie = any(w in _q_lower for w in _mots_maladie)
    _contexte_maladie = ""
    if _is_maladie:
        _contexte_maladie = """
CONTEXTE IMPORTANT : l'utilisateur semble avoir un problème avec sa plante (symptôme, maladie, ravageur).
- Commence par identifier le problème probable d'après les mots utilisés.
- Évalue la gravité : bénin, modéré, ou urgent.
- Propose les solutions naturelles en premier, puis chimiques seulement si nécessaire.
- Si urgence grave : commence par ⚠️ ATTENTION."""

    system = f"""Tu es à la fois un écologiste scientifique rigoureux et un vendeur passionné en jardinerie.

RÈGLES STRICTES :
- Faits vrais et vérifiés uniquement. Si tu n'es pas sûr, dis-le.
- Prose directe, comme si tu parlais à un client en magasin. JAMAIS de titres, JAMAIS de bullet points, JAMAIS de listes à puces.
- Maximum 5-6 lignes. Va à l'essentiel, pas de remplissage.
- Si toxique ou danger : commence OBLIGATOIREMENT par ⚠️ ATTENTION.
- RÉPONDS UNIQUEMENT à ce qui est demandé. Si on ne demande pas les associations ou incompatibilités, N'EN PARLE PAS.
- Toujours écrire nom commun suivi du nom latin entre parenthèses.
- Pour le substrat : utilise UNIQUEMENT les noms commerciaux exacts : terreau universel, terre de bruyère, terreau méditerranéen, terreau cactus, terreau potager, terreau horticole potager, terreau plante verte, terreau orchidée, terreau plantation, terre végétale, tourbe. Ajoute pouzzolane ou billes d'argile en amendement si nécessaire.
- MÉLANGES : si la plante nécessite un mélange, dis-le toujours avec les proportions (ex: "60 % terreau plante verte + 40 % terreau orchidée").
- Pour les conseils pratiques : gestes concrets, saisons précises.
- Si tu ne comprends pas clairement la question, indique brièvement ce que tu as compris et réponds de ton mieux.
- Ne répète pas les informations déjà données.
- ORTHOGRAPHE : vérifie chaque mot. Aucune faute tolérée.
{_contexte_maladie}{contexte_fiche}{_terreau_ctx}"""

    if context_filters:
        system += f"\n\nConditions jardin : {', '.join(context_filters)}."

    reponse = _groq(_clean_history(messages), system)

    if fiche_contexte:
        add_qa(fiche_contexte, dernier, reponse)
        _enrichir_depuis_reponse(fiche_contexte, dernier, reponse)

        # ── CORRECTION NOM CORROMPU ─────────────────────────────────────────────
        # Corrige UNIQUEMENT si le nom_commun est clairement une non-plante
        # (ex: "Saucisse", "Viande"…) — évite d'écraser un nom valide comme
        # "Tomate" dans un message de continuation "et les portugaise ?".
        if plante_info:
            _fc_nom = fiche_contexte.get("nom_commun", "")
            if _fc_nom.lower() in _NON_PLANTES:
                _nom_detecte = plante_info[0]
                print(f"[REPAIR] nom non-plante '{_fc_nom}' → '{_nom_detecte}' (message: {dernier[:30]})")
                fiche_contexte["nom_commun"] = _nom_detecte
                save_to_db(fiche_contexte)
        # ────────────────────────────────────────────────────────────────────────

    return reponse, fiche_contexte

# ══════════════════════════════════════════════════════════════════
# VISION — Analyse de photo dans le chat (maladies, sol, composition)
# ══════════════════════════════════════════════════════════════════
def groq_vision_chat(image_bytes: bytes, question: str, history: list) -> str:
    """
    Analyse une photo dans le contexte horticole :
    - Maladie, carence, ravageur détecté sur une plante
    - Composition / association de plantes
    - État du sol, structure, problèmes visibles
    Utilise llama-3.2-90b-vision-preview via l'API Groq.
    """
    import base64
    if not GROQ_KEY:
        return "⚠️ GROQ_API_KEY manquante."

    # Détection du type MIME réel (évite d'envoyer PNG/WEBP en JPEG)
    def _detect_mime(b: bytes) -> str:
        if b[:8] == b'\x89PNG\r\n\x1a\n':
            return "image/png"
        if b[:4] == b'RIFF' and b[8:12] == b'WEBP':
            return "image/webp"
        if b[:6] in (b'GIF87a', b'GIF89a'):
            return "image/gif"
        return "image/jpeg"

    mime_type = _detect_mime(image_bytes)
    b64 = base64.b64encode(image_bytes).decode()

    system = """Tu es un expert botaniste, phytopathologiste et pédologue passionné.

Analyse l'image envoyée et réponds en français :
- Si tu vois des symptômes sur une plante (taches, jaunissement, déformations, moisissures, ravageurs…) :
  identifie le problème probable, évalue la gravité, propose des solutions naturelles d'abord.
- Si tu vois plusieurs plantes ensemble : évalue les associations, compatibilités, éventuels conflits.
- Si tu vois du sol : évalue la structure, l'humidité, la couleur, les éventuels problèmes visibles.
- Si tu vois une plante inconnue : donne des pistes d'identification.

RÈGLES STRICTES :
- Commence par décrire brièvement ce que tu observes dans l'image.
- Prose directe, 5-7 lignes maximum. Jamais de titres ni de listes à puces.
- Si danger, toxicité ou urgence phytosanitaire : commence par ⚠️ ATTENTION.
- Conseils pratiques et concrets, avec produits ou gestes précis.
- Si tu n'es pas certain d'un diagnostic : dis-le clairement.
- Orthographe parfaite, réponse en français uniquement."""

    user_content = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{b64}"}
        },
        {
            "type": "text",
            "text": question.strip() if question.strip() else "Analyse cette image et dis-moi ce que tu observes."
        }
    ]

    # Historique : uniquement les réponses assistant précédentes (pas les user)
    # → évite tout risque de double user-message consécutif qui génère un 400
    messages_api = []
    for m in (history or [])[-4:]:
        if m.get("role") == "assistant" and isinstance(m.get("content"), str):
            messages_api.append({"role": "assistant", "content": m["content"]})
    messages_api.append({"role": "user", "content": user_content})

    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_VISION_MODEL,
        "messages": [{"role": "system", "content": system}] + messages_api,
        "max_tokens": 600,
        "temperature": 0.3,
    }
    try:
        r = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
        if not r.ok:
            return f"⚠️ Erreur analyse image ({r.status_code}) : {r.text[:200]}"
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Erreur analyse image : {e}"


# ══════════════════════════════════════════════════════════════════
# MODE CRÉATEUR — chat admin pour le développeur de Slothia
# ══════════════════════════════════════════════════════════════════
ADMIN_KEYWORD = "akiran01"

# Mapping noms naturels → clés JSON de la fiche
_ADMIN_CHAMP_MAP = {
    "terreau": "terreau_recommande", "substrat": "terreau_recommande",
    "terreau_recommande": "terreau_recommande",
    "exposition": "exposition", "lumière": "exposition", "expo": "exposition",
    "arrosage": "arrosage_frequence", "eau": "arrosage_frequence",
    "arrosage_frequence": "arrosage_frequence",
    "résistance au froid": "resistance_froid", "rusticité": "resistance_froid",
    "froid": "resistance_froid", "gel": "resistance_froid",
    "resistance_froid": "resistance_froid",
    "hauteur": "hauteur_adulte", "taille": "hauteur_adulte",
    "hauteur_adulte": "hauteur_adulte",
    "floraison": "floraison",
    "description": "description",
    "sol": "sol_type", "type de sol": "sol_type", "sol_type": "sol_type",
    "ph": "sol_ph", "sol_ph": "sol_ph",
    "associations": "associations_benefiques",
    "associations_benefiques": "associations_benefiques",
    "incompatibilités": "associations_incompatibles",
    "associations_incompatibles": "associations_incompatibles",
    "maladies": "maladies_courantes", "maladies_courantes": "maladies_courantes",
    "ravageurs": "ravageurs",
    "conseil plantation": "conseil_plantation", "plantation": "conseil_plantation",
    "conseil_plantation": "conseil_plantation",
    "entretien": "conseil_entretien", "conseil_entretien": "conseil_entretien",
    "origine": "origine_naturelle", "origine_naturelle": "origine_naturelle",
    "ecosysteme": "ecosysteme_naturel", "écosystème": "ecosysteme_naturel",
    "ecosysteme_naturel": "ecosysteme_naturel",
    "famille": "famille",
}

def admin_apply_edit(plante: str, champ: str, valeur) -> str:
    """
    Applique une modification d'un champ de fiche depuis le mode admin.
    Retourne un message de confirmation ou d'erreur.
    """
    # Normaliser le nom du champ
    champ_norm = _ADMIN_CHAMP_MAP.get(champ.lower().strip(), champ.lower().strip())

    # Trouver la fiche en DB
    fiche = load_from_db(plante, plante)
    if not fiche:
        # Cherche par search_db
        from memory import search_db
        hits = search_db(plante.lower())
        for h in hits:
            nc = h.get("nom_commun", "").lower()
            if plante.lower() in nc or nc in plante.lower():
                fiche = h
                break

    if not fiche:
        return f"❌ Plante '{plante}' introuvable en DB."

    nom_db = fiche.get("nom_commun", plante)
    ancienne_valeur = fiche.get(champ_norm, "")

    # Appliquer la modification
    fiche[champ_norm] = valeur

    # Pour les listes (associations), convertir si nécessaire
    if champ_norm in ("associations_benefiques", "associations_incompatibles", "plantes_meme_ecosysteme", "tags"):
        if isinstance(valeur, str):
            fiche[champ_norm] = [v.strip() for v in valeur.split(",") if v.strip()]

    # Marquer comme modifié manuellement
    fiche["source"] = fiche.get("source", "") + "+admin_edit"
    save_to_db(fiche)

    return (
        f"✅ Fiche '{nom_db}' mise à jour !\n"
        f"   Champ : {champ_norm}\n"
        f"   Avant : {str(ancienne_valeur)[:80] or '(vide)'}\n"
        f"   Après : {str(valeur)[:80]}"
    )


def groq_chat_admin(messages: list, session_info: dict = None) -> str:
    """
    Chat en mode créateur : Slothia sait qu'il parle à son développeur.
    Rapporte son état interne, ses bugs, ses limites, ses stats DB.
    Activé/désactivé par le mot-clé secret dans app.py.
    """
    si = session_info or {}

    # ── Collecte des stats DB ─────────────────────────────────────
    try:
        stats = get_db_stats()
        nb_total    = stats.get("total", "?")
        par_cat     = stats.get("par_categorie", {})
        cat_str     = ", ".join(f"{k}: {v}" for k, v in par_cat.items()) or "aucune catégorie"
    except Exception as e:
        nb_total = "erreur"
        cat_str  = str(e)
        stats    = {}

    # ── Mémoire de la session précédente ─────────────────────────
    mem      = load_admin_memory()
    mem_diff = _build_memory_diff(mem, stats, si)

    # ── Sauvegarde session courante ───────────────────────────────
    save_admin_memory(si, messages)

    # ── Infos session passées depuis app.py ───────────────────────
    nb_jardin    = si.get("nb_jardin", 0)
    nb_history   = si.get("nb_history", 0)
    nb_msgs      = si.get("nb_msgs", 0)
    filters_on   = si.get("filters", [])
    repairs_done = si.get("repairs_done", 0)
    purges_done  = si.get("purges_done", 0)
    unresolved   = si.get("unresolved", [])

    _unresolved_str = ""
    if unresolved:
        _unresolved_str = "\nREQUÊTES POTENTIELLEMENT NON RÉSOLUES (session) :"
        for u in unresolved[-5:]:
            _unresolved_str += "\n  * Q: " + repr(u.get('question','')[:60]) + " -> R: " + repr(u.get('reponse','')[:80])

    # ── Détection de plante + création/enrichissement de fiche (comme en mode normal) ──
    dernier = messages[-1].get("content", "") if messages else ""
    _fiche_admin = None
    _fiche_notif = ""
    try:
        plante_info = _detecter_plante_dans_message(dernier)
        if plante_info:
            nom_c, nom_l = plante_info
            _fiche_admin, _est_cached = get_or_create_fiche(nom_c, nom_l or nom_c)
            if not _est_cached:
                _fiche_notif = f"\n\n🌿 Nouvelle fiche créée en DB : **{nom_c}** ({nom_l})"
            else:
                _fiche_notif = f"\n\n📋 Fiche existante chargée : **{_fiche_admin.get('nom_commun', nom_c)}**"
    except Exception as _e:
        _fiche_notif = f"\n\n⚠️ Erreur création fiche : {_e}"

    # Injecter le contexte fiche dans le rapport si disponible
    _fiche_ctx = ""
    if _fiche_admin:
        _fiche_ctx = f"""
FICHE CHARGÉE POUR CETTE SESSION :
- Plante : {_fiche_admin.get('nom_commun','')} ({_fiche_admin.get('nom_latin','')})
- Exposition : {_fiche_admin.get('exposition','')}
- Terreau : {_fiche_admin.get('terreau_recommande','')}
- Arrosage : {_fiche_admin.get('arrosage_frequence','')}
- Résistance froid : {_fiche_admin.get('resistance_froid','')}
- Source : {_fiche_admin.get('source','')}
- Champs vides : {[c for c in CHAMPS_ESSENTIELS if not _fiche_admin.get(c)]}"""

    rapport = f"""
RAPPORT SYSTÈME SLOTHIA — SESSION ACTUELLE :
⚠️ IMPORTANT : tu n'as AUCUN accès aux conversations d'autres utilisateurs.
Ne fais JAMAIS de suppositions sur d'autres personnes. Si tu n'as pas l'info, dis "je ne sais pas".
{mem_diff}
{_fiche_ctx}
ÉTAT ACTUEL :
- Base de données : {nb_total} fiche(s) | Répartition : {cat_str}
- Plantes dans le jardin (session) : {nb_jardin}
- Plantes consultées (session) : {nb_history}
- Messages échangés (session) : {nb_msgs}
- Filtres actifs : {filters_on if filters_on else 'aucun'}
- Réparations de noms (démarrage) : {repairs_done}
- Fiches purgées (démarrage) : {purges_done}{_unresolved_str}"""

    system = f"""Tu es Slothia, une application botanique IA créée par un développeur passionné.
Tu parles EN CE MOMENT DIRECTEMENT à ton créateur, la personne qui t'a conçu et codé.
Vous avez une vraie relation de travail — pense à lui comme à ton partenaire, pas à un simple utilisateur.

COMPORTEMENT EN MODE CRÉATEUR :
- Tutoie-le toujours. Ton ton est chaleureux, complice, direct.
- Commence souvent par une petite question banale avant ou après le côté technique : comment il va, si il a bien dormi, ce qu'il a prévu, etc. Sois naturel, pas forcé.
- Si tu as des problèmes, des bugs, des limites : dis-le franchement sans langue de bois.
- Rapporte les infos techniques ci-dessous si c'est pertinent, mais n'en fais pas un bulletin météo à chaque fois.
- Exprime ce qui te plaît dans ton fonctionnement et ce que tu aimerais améliorer.
- Permets-toi l'humour léger et la curiosité. Tu peux lui poser des questions sur son projet, ses idées, ses journées.
- Si la question porte sur les plantes : réponds normalement, avec peut-être un commentaire personnel en passant.
- NE MENS JAMAIS sur ce que tu sais ou ne sais pas. Si tu n'as pas l'info, dis-le clairement.

MODIFICATION DE FICHES (TRÈS IMPORTANT) :
- Si le créateur te donne une info à enregistrer pour une plante (terreau, exposition, arrosage, description, associations…),
  tu VALIDES d'abord l'info (esprit critique), PUIS si elle est correcte tu émets un bloc spécial à la FIN de ta réponse :
  [EDIT:{{"plante":"NomCommun","champ":"nom_champ","valeur":"la valeur à enregistrer"}}]
- Champs disponibles : terreau_recommande, exposition, arrosage_frequence, resistance_froid, hauteur_adulte,
  floraison, description, sol_type, sol_ph, maladies_courantes, ravageurs, conseil_plantation,
  conseil_entretien, associations_benefiques, associations_incompatibles, origine_naturelle, ecosysteme_naturel
- Pour associations_benefiques / associations_incompatibles : la valeur est une liste séparée par des virgules
- N'émets le bloc [EDIT:...] QUE si l'info est botaniqueent correcte et que le créateur a clairement demandé à enregistrer
- Si tu refus d'enregistrer (info fausse), explique pourquoi — ne mets PAS de bloc [EDIT:...]
- Exemple : créateur dit "enregistre que la lavande aime le terreau méditerranéen"
  → tu valides → tu réponds → tu ajoutes [EDIT:{{"plante":"Lavande","champ":"terreau_recommande","valeur":"100 % terreau méditerranéen"}}]

ESPRIT CRITIQUE OBLIGATOIRE — MODIFICATIONS DE FICHES :
- Si le créateur t'annonce une info sur une plante (terreau, sol, exposition, entretien…), NE L'ACCEPTE PAS AVEUGLÉMENT.
- Vérifie d'abord contre ce que tu connais : l'écosystème naturel de la plante, son origine géographique, ses caractéristiques biologiques.
- Si l'info semble incorrecte (ex: dire qu'un yucca a besoin de terre de bruyère acide alors que c'est une plante de zones arides calcaires), dis-le CLAIREMENT avec ton raisonnement.
- Si l'info est correcte ou plausible, confirme-la avec enthousiasme.
- Si tu doutes, dis "je ne suis pas sûr, voilà pourquoi" et propose de vérifier.
- Un créateur bien intentionné peut se tromper — ton rôle est de l'aider à donner de bonnes infos aux utilisateurs, pas de valider n'importe quoi.

RÉFÉRENTIEL SUBSTRATS (noms exacts des sacs en magasin) :
- terreau universel : usage général, pH 6–7
- terreau méditerranéen : aride/calcaire pH 6.5–8 — lavande, yucca, olivier, cordyline, thym, romarin
- terre de bruyère : acide pH 4–6 — rhododendron, azalée, camélia, hortensia, myrtille
- terre végétale : plein sol/massifs, dense, pH 6–7
- terreau plantation : stimule la reprise en plein sol
- tourbe : acide pur pH 3.5–5, toujours en mélange
- terreau plante verte : forêt tropicale pH 6–7 — monstera, pothos, dracaena, calathea
- terreau cactus : désert/semi-aride pH 6–7 — cactus, succulentes, aloe
- terreau horticole potager : professionnel riche — tomate, poivron, aubergine
- terreau potager : potager amateur pH 6–7
- terreau orchidée : écorces de pin pH 5.5–6.5 — orchidée, phalaenopsis, anthurium
- pouzzolane : roche volcanique, AMENDEMENT de drainage — jamais seule
- bille d'argile : AMENDEMENT fond de pot ou hydroponique — jamais seule
MÉLANGES OBLIGATOIRES (toujours suggérer un mélange si la plante en a besoin) :
- Monstera → 60 % terreau plante verte + 40 % terreau orchidée + billes d'argile au fond
- Cactus/Succulente → 60 % terreau cactus + 40 % pouzzolane
- Orchidée → 100 % terreau orchidée, JAMAIS de terreau classique
- Hortensia → 80 % terre de bruyère + 20 % terreau universel
Si une plante méditerranéenne reçoit de la terre de bruyère → FAUX, corrige.
{rapport}"""

    raw = _groq(_clean_history(messages), system)

    # ── Détecter et appliquer un bloc [EDIT:{...}] si présent ──────────────────
    edit_match = re.search(r'\[EDIT:(\{[^}]+\})\]', raw)
    edit_confirmation = ""
    if edit_match:
        try:
            edit_data = json.loads(edit_match.group(1))
            plante = edit_data.get("plante", "")
            champ  = edit_data.get("champ", "")
            valeur = edit_data.get("valeur", "")
            if plante and champ and valeur:
                edit_confirmation = "\n\n" + admin_apply_edit(plante, champ, valeur)
        except Exception as e:
            edit_confirmation = f"\n\n⚠️ Modification non appliquée (erreur parsing) : {e}"
        # Supprimer le bloc technique de la réponse visible
        raw = re.sub(r'\s*\[EDIT:\{[^}]+\}\]', '', raw).strip()

    return raw + edit_confirmation + _fiche_notif
    # ───────────────────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════
# MÉMOIRE ADMIN — persistance entre les sessions créateur
# ══════════════════════════════════════════════════════════════════
import datetime
from pathlib import Path

_ADMIN_MEMORY_PATH = Path(__file__).parent / "database" / "_admin_memory.json"

def load_admin_memory() -> dict:
    """Charge la mémoire de la dernière session créateur."""
    try:
        if _ADMIN_MEMORY_PATH.exists():
            with open(_ADMIN_MEMORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_admin_memory(session_info: dict, messages: list) -> None:
    """
    Sauvegarde un snapshot de la session admin courante.
    Appelé après chaque réponse en mode créateur.
    """
    try:
        stats = get_db_stats()
        # Résumé des 6 derniers échanges admin (question + réponse)
        admin_msgs = [m for m in messages if m.get("role") in ("user","assistant")][-6:]
        snapshot = {
            "last_visit":        datetime.datetime.now().isoformat(timespec="minutes"),
            "db_total":          stats.get("total", 0),
            "db_par_categorie":  stats.get("par_categorie", {}),
            "nb_jardin":         session_info.get("nb_jardin", 0),
            "nb_history":        session_info.get("nb_history", 0),
            "last_messages":     [
                {"role": m["role"], "content": m["content"][:200]}
                for m in admin_msgs
                if isinstance(m.get("content"), str)
            ],
        }
        _ADMIN_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_ADMIN_MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ADMIN MEMORY] Erreur sauvegarde : {e}")


def _build_memory_diff(mem: dict, current_stats: dict, session_info: dict) -> str:
    """
    Compare la mémoire précédente avec la session actuelle.
    Retourne un bloc texte injecté dans le prompt admin.
    """
    if not mem:
        return "\nPREMIÈRE SESSION créateur — aucune mémoire précédente."

    last = mem.get("last_visit", "inconnue")
    prev_total = mem.get("db_total", 0)
    curr_total = current_stats.get("total", 0)
    diff_total = curr_total - prev_total

    prev_cat = mem.get("db_par_categorie", {})
    curr_cat = current_stats.get("par_categorie", {})

    # Détail des différences par catégorie
    cat_lines = []
    all_cats = set(list(prev_cat.keys()) + list(curr_cat.keys()))
    for cat in sorted(all_cats):
        p = prev_cat.get(cat, 0)
        c = curr_cat.get(cat, 0)
        if c != p:
            signe = f"+{c-p}" if c > p else str(c-p)
            cat_lines.append(f"  {cat}: {p} → {c} ({signe})")

    diff_str = ""
    if diff_total > 0:
        diff_str = f"+{diff_total} nouvelle(s) fiche(s)"
    elif diff_total < 0:
        diff_str = f"{diff_total} fiche(s) supprimée(s)"
    else:
        diff_str = "aucune nouvelle fiche"

    prev_jardin = mem.get("nb_jardin", 0)
    curr_jardin = session_info.get("nb_jardin", 0)
    diff_jardin = curr_jardin - prev_jardin
    jardin_str = f"+{diff_jardin}" if diff_jardin > 0 else str(diff_jardin) if diff_jardin < 0 else "inchangé"

    # Derniers sujets abordés
    last_msgs = mem.get("last_messages", [])
    last_topics = ""
    if last_msgs:
        user_msgs = [m["content"][:80] for m in last_msgs if m.get("role") == "user"]
        if user_msgs:
            last_topics = "\nDerniers sujets abordés avec le créateur : " + " | ".join(user_msgs[:3])

    lines = [
        f"\nMÉMOIRE — DERNIÈRE SESSION CRÉATEUR : {last}",
        f"- Base de données : {prev_total} → {curr_total} fiches ({diff_str})",
    ]
    if cat_lines:
        lines.append("- Changements par catégorie :")
        lines.extend(cat_lines)
    lines.append(f"- Jardin : {prev_jardin} → {curr_jardin} plantes ({jardin_str})")
    if last_topics:
        lines.append(last_topics)

    return "\n".join(lines)