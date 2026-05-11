
import json
import re
from pathlib import Path

DB_ROOT = Path(__file__).parent / "database"

# ── Schéma d'une fiche ────────────────────────────────────────────
FICHE_SCHEMA = {
    "nom_commun": "", "nom_latin": "", "famille": "",
    "categorie": "", "sous_categorie": "", "description": "",
    "origine_naturelle": "", "ecosysteme_naturel": "",
    "exposition": "", "sol_type": "", "sol_ph": "",
    "terreau_recommande": "", "arrosage": "", "arrosage_frequence": "",
    "resistance_froid": "", "zone_rusticite": "",
    "hauteur_adulte": "", "croissance": "", "taille": "",
    "floraison": "", "fructification": "", "biodiversite": "",
    "insectes_attires": "", "oiseaux_attires": "",
    "associations_benefiques": [], "associations_incompatibles": [],
    "plantes_meme_ecosysteme": [],
    "maladies_courantes": "", "ravageurs": "",
    "conseil_plantation": "", "conseil_entretien": "",
    "tags": [], "wiki": {}, "qa_memory": {}, "source": ""
}

# ── Détection catégories ──────────────────────────────────────────
# ── Catégories inspirées du catalogue Maison Barrault ────────────────────────
CATEGORY_KEYWORDS = {
    "plantes_vertes": [
        "monstera","pothos","epipremnum","dracaena","ficus","philodendron",
        "calathea","dieffenbachia","schefflera","croton","spathiphyllum",
        "tradescantia","peperomia","chlorophytum","aglaonema","sansevieria",
        "zamioculcas","cissus","syngonium","aralia","asparagus","alocasia",
        "strelitzia","chamaedorea","ravenea","howea","rhapis","coffea",
        "plante verte","plantes vertes","intérieur","tropical",
    ],
    "plantes_grasses": [
        "cactus","cactaceae","echeveria","sedum","sempervivum","haworthia",
        "aloe","agave","opuntia","mammillaria","cereus","euphorbe cactiforme",
        "lithops","aeonium","crassula","kalanchoe","portulacaria",
        "succulente","succulentes","plante grasse","plantes grasses",
    ],
    "plantes_vivaces": [
        "lavandula","lavande","rosa","rosier","paeonia","pivoine","heuchera",
        "hosta","salvia","sauge","echinacea","rudbeckia","achillea","astilbe",
        "geranium","géranium","pelargonium","agapanthe","agapanthus",
        "hemerocallis","iris","gaura","nepeta","phlox","verbena","coreopsis",
        "kniphofia","vivace","vivaces","plante vivace","yucca","cordyline",
        "phormium","bambou","phyllostachys","miscanthus","cortaderia",
        "forsythia","syringa","viburnum","weigela","spiraea","lilas",
        "buddleia","mahonia","ribes","cornus","arbuste","buisson",
        "buxus","taxus","ligustrum","photinia","buis","if",
        "pinus","quercus","fagus","acer","fraxinus","betula","platanus",
        "tilia","salix","populus","chêne","hêtre","érable","frêne",
        "bouleau","arbre","olea","cedrus","pommier","cerisier","poirier",
        "rhododendron","azalea","azalée","camellia","camélia","hortensia",
        "hydrangea","magnolia","pieris",
    ],
    "graminees": [
        "festuca","miscanthus","pennisetum","stipa","molinia","panicum",
        "helictotrichon","briza","graminée","graminées","herbe ornementale",
    ],
    "fougeres": [
        "nephrolepis","polystichum","dryopteris","athyrium","asplenium",
        "phyllitis","osmunda","matteucia","cyathea","dicksonia",
        "fougère","fougères","pteridophyta",
    ],
    "plantes_aquatiques": [
        "nymphaea","nelumbo","nénuphar","lotus","typha","juncus","sagittaria",
        "elodea","myriophyllum","pontederia","pistia","eichhornia",
        "iris pseudacorus","massette","lentille d'eau","aquatique","bassin",
    ],
    "plantes_aromatiques": [
        "ocimum","basilic","mentha","menthe","thymus","thym","rosmarinus",
        "rosmarinum","romarin","origanum","origan","salvia officinalis",
        "coriandrum","coriandre","petroselinum","persil","anethum","aneth",
        "foeniculum","fenouil","allium schoenoprasum","ciboulette","melissa",
        "mélisse","laurus nobilis","laurier","verveine","aromatique",
        "herbe aromatique","fines herbes","plante médicinale",
    ],
    "plantes_eco_solution": [
        "tagetes","phacelia","phacélie","borage","bourrache","helianthus",
        "tournesol","lupinus","lupin","trifolium","trèfle","anthemis",
        "camomille","tanacetum","tanaisie","solidago","eco-solution",
        "auxiliaire","pollinisateur","mellifère","biodiversité","nectarifère",
    ],
    "potageres": [
        "solanum lycopersicum","tomate","solanum melongena","aubergine",
        "cucurbita","courgette","cucumis sativus","concombre","capsicum",
        "poivron","phaseolus","haricot","lactuca","salade","laitue",
        "allium cepa","oignon","daucus","carotte","brassica","chou",
        "spinacia","épinard","beta vulgaris","betterave","raphanus","radis",
        "allium porrum","poireau","cynara","artichaut","allium sativum","ail",
        "potiron","courge","melon","pastèque","fragaria","fraise",
        "ribes","groseille","rubus","framboisier","vaccinium","myrtille",
        "potager","légume","petits fruits","fraisier",
    ],
    "plantes_annuelles": [
        "zinnia","cosmos","impatiens","petunia","lobelia","lobularia",
        "antirrhinum","nigella","papaver rhoeas","centaurea","scabiosa",
        "lathyrus","pois de senteur","tropaeolum","capucine","calendula",
        "annuelle","annuelles","fleur annuelle",
    ],
    "plantes_bisannuelles": [
        "digitalis","digitale","myosotis","bellis","viola","pensée",
        "erysimum","giroflée","alcea","rose trémière","lunaria",
        "bisannuelle","bisannuelles",
    ],
    "chrysanthemes": [
        "chrysanthemum","chrysanthème","chrysanthèmes","dendranthema",
    ],
    "arbres_arbustes": [
        "pinus","quercus","fagus","acer","fraxinus","betula","platanus",
        "tilia","salix","populus","prunus","malus","pyrus","cydonia",
        "sorbus","alnus","carpinus","corylus","juglans","castanea",
        "robinia","gleditsia","paulownia","catalpa","liquidambar",
        "liriodendron","magnolia","cercis","amelanchier","crataegus",
        "cotoneaster","pyracantha","berberis","forsythia","syringa",
        "philadelphus","deutzia","kolkwitzia","weigela","viburnum",
        "sambucus","cornus","ligustrum","buxus","taxus","thuja",
        "chamaecyparis","juniperus","picea","abies","cedrus","larix",
        "eucalyptus","araucaria","ginkgo","metasequoia",
        "oleander","nerium","olea","ficus carica","punica","arbre",
        "arbuste","haie","conifère","résineux","feuillu",
        "pin","chêne","hêtre","érable","frêne","bouleau","platane",
        "tilleul","saule","peuplier","cerisier","pommier","poirier",
        "noisetier","noyer","châtaignier","robinier","aulne","charme",
        "lilas","forsythia","viorne","sureau","cornouiller",
        "if","buis","thuya","genévrier","épicéa","sapin","cèdre",
        "mélèze","ginkgo","laurier","olivier","figuier","grenadier",
    ],
    "plantes_sauvages": [
        "urtica","dioica","ortie","convolvulus arvensis","liseron",
        "taraxacum","pissenlit","plantago","plantain","cirsium","chardon",
        "papaver rhoeas","coquelicot","centaurea cyanus","bleuet",
        "daucus carota","carotte sauvage","achillea millefolium",
        "digitalis","digitale","hypericum perforatum","millepertuis",
        "sambucus nigra","sureau noir","rosa canina","églantier",
        "corylus avellana","noisetier","prunus spinosa","prunellier",
        "crataegus monogyna","aubépine","rubus fruticosus","ronce",
        "fragaria vesca","fraise des bois","viola tricolor","pensée sauvage",
        "primula veris","coucou","bellis perennis","pâquerette",
        "lamium","ortie morte","galium aparine","gaillet",
        "myosotis arvensis","myosotis","ranunculus acris","renoncule",
        "lotus corniculatus","lotier","trifolium","trèfle",
        "epilobium","épilobe","lythrum salicaria","salicaire",
        "mentha aquatica","menthe sauvage","valeriana officinalis",
        "bryonia","bryone","clematis vitalba","clématite",
        "hedera helix sauvage","lierre","arum maculatum","arum",
        "oxalis acetosella","oxalide","stellaria","mouron",
        "geranium robertianum","herbe à robert","sauvage","adventice",
        "flore sauvage","prairie","forêt","haie naturelle","bocage",
    ],
    "rosiers": [
        "rosa gallica","rosa damascena","rosa centifolia","rosa alba",
        "rosa rugosa","rosa banksiae","rosa moschata","rosa moyesii",
        "rosa floribunda","rosa miniature","rosa climber","rosier",
        "rosiers","david austin","eden rose","new dawn","iceberg",
    ],
    "plantes_aquarium": [
        "anubias","cryptocoryne","echinodorus","vallisneria","ludwigia",
        "rotala","hygrophila","microsorum","eleocharis","cabomba",
        "ceratophyllum","taxiphyllum","bacopa","hemianthus","staurogyne",
        "pogostemon","limnophila","riccia","vesicularia","bolbitis",
        "aquarium","plante aquatique d'aquarium","aquascaping",
    ],
    "plantes_carnivores": [
        "dionaea","sarracenia","drosera","nepenthes","pinguicula",
        "utricularia","cephalotus","aldrovanda","carnivore","insectivore",
        "attrape mouche","venus","pitcher plant",
    ],
    "plantes_grimpantes": [
        "wisteria","glycine","clematis","clématite","jasminum","jasmin",
        "passiflora","passiflore","cobaea","ipomoea","ipomée","campsis",
        "humulus","hydrangea anomala","akebia","schisandra","actinidia",
        "parthenocissus","lonicera grimpant","fallopia","solanum laxum",
        "grimpante","grimpant","liane","escalade","palissade",
    ],
    "plantes_fetes": [
        "euphorbia pulcherrima","poinsettia","étoile de noël","schlumbergera",
        "cactus de noël","cyclamen","hippeastrum","amaryllis","helleborus",
        "hellébore","skimmia","ilex","houx","viscum","gui",
        "kalanchoe blossfeldiana","plante de noël","noël","fêtes",
    ],
}

SUB_CATEGORIES = {
    "plantes_vertes":       ["monstera","pothos","ficus","dracaena","philodendron",
                             "calathea","spathiphyllum","cordyline","aralia",
                             "asparagus","alocasia","chamaedorea","coffea","aglaonema"],
    "plantes_grasses":      ["cactus","echeveria","aloe","agave","sedum","haworthia",
                             "kalanchoe","crassula","opuntia","mammillaria"],
    "plantes_vivaces":      ["lavande","rosier","géranium","sauge","pivoine","agapanthe",
                             "iris","hosta","heuchera","echinacea","hortensia",
                             "rhododendron","azalée","lilas","buddleia","bambou","yucca",
                             "crocus","tulipe","narcisse","jacinthe","dahlia","begonia",
                             "allium","muscari","fritillaire"],
    "graminees":            ["festuca","miscanthus","pennisetum","carex","stipa"],
    "fougeres":             ["nephrolepis","polystichum","asplenium","dryopteris"],
    "plantes_aquatiques":   ["nymphaea","lotus","typha","sagittaria","iris pseudacorus"],
    "plantes_aromatiques":  ["basilic","menthe","thym","romarin","persil",
                             "coriandre","origan","laurier","ciboulette","fenouil"],
    "plantes_eco_solution": ["tournesol","bourrache","phacélie","tagète","lupin"],
    "potageres":            ["tomate","courgette","salade","carotte","haricot",
                             "poivron","aubergine","oignon","ail","fraise"],
    "plantes_annuelles":    ["zinnia","cosmos","pétunia","impatiens","capucine"],
    "plantes_bisannuelles": ["digitale","myosotis","pensée","rose trémière","giroflée"],
    "arbres_arbustes":  ["chêne","hêtre","érable","bouleau","cerisier","pommier",
                         "olivier","figuier","lilas","forsythia","sureau","if",
                         "thuya","genévrier","épicéa","sapin","cèdre","ginkgo",
                         "magnolia","cercis","viorne","cornouiller","noisetier"],
    "plantes_sauvages": ["ortie","pissenlit","coquelicot","bleuet","millepertuis",
                         "sureau","églantier","prunellier","aubépine","ronce",
                         "fraise des bois","valériane","salicaire","lierre",
                         "clématite sauvage","arum","primevère sauvage"],
    "plantes_fetes":        ["poinsettia","cyclamen","amaryllis","hellébore","houx"],
    "rosiers":              ["rosier buisson","rosier grimpant","rosier ancien",
                             "rosier anglais","rosier rugosa","rosier miniature"],
    "plantes_aquarium":     ["anubias","cryptocoryne","echinodorus","vallisneria",
                             "ludwigia","rotala","microsorum","java moss"],
    "plantes_carnivores":   ["dionaea","sarracenia","drosera","nepenthes","pinguicula"],
    "plantes_grimpantes":   ["glycine","clématite","jasmin","passiflore","campsis",
                             "hydrangea grimpant","akebia","parthenocissus"],
}

ALERT_WORDS = {
    "toxique","dangereux","dangereuse","poison","vénéneux","vénéneuse","mortel","mortelle",
    "nocif","nocive","irritant","allergisant","se protéger","porter des gants","gants",
    "ingestion","ingérer","ingestion"
}

QA_CATS = {
    "floraison":    ["fleur","fleurit","floraison","fleurir","bouton","pétale","parfum","couleur fleur"],
    "fruits":       ["fruit","baie","graine","haricot","gousse","semence","fructification","comestible"],
    "maladies":     ["maladie","tache","jaunisse","champignon","moisissure","pourriture","traitement","soigner"],
    "ravageurs":    ["insecte","puceron","cochenille","araignée","chenille","larve","ver","parasite","ravageur","mange"],
    "arrosage":     ["arros","eau","humidité","sécheresse","fréquence","irrigation","sec","trop d'eau"],
    "taille":       ["taill","couper","élaguer","recéper","rabattre","branches","comment couper"],
    "plantation":   ["planter","plantation","quand planter","transplanter","repiquer","distance","profondeur"],
    "exposition":   ["soleil","ombre","mi-ombre","exposition","lumière","orientation","nord","sud","est","ouest"],
    "sol_terreau":  ["terreau","sol","terre","substrat","engrais","compost","ph","rempotage","pot"],
    "froid":        ["froid","gel","hiver","rusticité","température","résiste","degré","rentrer"],
    "associations": ["associer","compagnon","voisin","planter avec","compatible","incompatible","éviter","mélanger"],
    "biodiversite": ["oiseau","insecte","abeille","papillon","hérisson","attirer","pollinisateur","faune"],
    "toxicite":     ["toxique","dangereux","poison","vénéneux","danger","enfant","animal","chat","chien","ingérer","manger"],
    "divers":       []
}

# ── Utilitaires ───────────────────────────────────────────────────
def _safe(text: str) -> str:
    return re.sub(r'[^a-z0-9_]', '_', text.lower().replace(" ", "_"))

def detect_category(nom_latin: str, nom_commun: str) -> tuple[str, str]:
    nom = f"{nom_commun} {nom_latin}".lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(k in nom for k in kws):
            sub = next((s for s in SUB_CATEGORIES.get(cat, []) if s.replace("_"," ") in nom or s in nom), nom.split()[0] if nom.split() else "divers")
            return cat, sub
    return "ornement", "divers"

def contains_alert(text: str) -> bool:
    """
    Détecte une vraie alerte de toxicité — évite les faux positifs.
    Ex : "ne pas confondre avec des plantes toxiques" → pas une alerte
    Ex : "⚠️ ATTENTION cette plante est toxique" → alerte réelle
    """
    t = text.lower()

    # Patterns qui indiquent que c'est une alerte RÉELLE (sujet = la plante elle-même)
    REAL_ALERT_PATTERNS = [
        "⚠️ attention", "⚠️",
        "cette plante est toxique", "est toxique pour",
        "est vénéneuse", "est vénéneux",
        "est dangereuse", "est dangereux",
        "est mortelle", "est mortel",
        "toxique pour les", "toxique si",
        "peut être toxique pour",
        "nocif pour", "nocive pour",
        "porter des gants", "se protéger",
        "ingestion peut", "ingérer peut",
        "en cas d'ingestion",
    ]
    if any(p in t for p in REAL_ALERT_PATTERNS):
        return True

    # Patterns qui indiquent un contexte NÉGATIF (faux positifs à ignorer)
    FALSE_POSITIVE_PATTERNS = [
        "ne pas confondre avec",
        "contrairement aux plantes",
        "d'autres plantes qui peuvent être toxiques",
        "certaines plantes toxiques",
        "plantes potentiellement toxiques",
        "pas toxique",
        "non toxique",
        "n'est pas toxique",
        "n'est pas dangereuse",
        "n'est pas dangereux",
        "sans danger",
        "comestible",
        "consommation sans",
    ]
    for fp in FALSE_POSITIVE_PATTERNS:
        if fp in t:
            return False

    # Vérification mot clé simple (dernier recours)
    SIMPLE_ALERT_WORDS = {"poison", "vénéneux", "vénéneuse", "mortel", "mortelle", "allergisant"}
    return any(w in t for w in SIMPLE_ALERT_WORDS)

def detect_qa_cat(question: str) -> str:
    q = question.lower()
    for cat, kws in QA_CATS.items():
        if any(k in q for k in kws):
            return cat
    return "divers"

def _normalize(q: str) -> str:
    q = re.sub(r'[?!.,;:]', '', q.lower().strip())
    for s in ["est-ce que","c'est quoi","dis moi","explique","comment savoir"]:
        q = q.replace(s, "")
    return re.sub(r'\s+', ' ', q).strip()

def _similarity(q1: str, q2: str) -> float:
    w1, w2 = set(_normalize(q1).split()), set(_normalize(q2).split())
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / len(w1 | w2)

# ── Base de données ───────────────────────────────────────────────
def _fiche_matches(fiche: dict, nom_latin: str, nom_commun: str) -> bool:
    """
    Vérifie qu'une fiche correspond VRAIMENT à la plante cherchée.

    DOUBLE PROTECTION anti-contamination :
    1. Si les deux noms latins ont des genres différents → rejet immédiat
       (ex: fiche a "Cucumis melo" et on cherche "Solanum melongena" → rejet)
    2. Si le nom latin matche mais que les noms communs sont incompatibles → rejet
       (ex: fiche a (Cucumis melo, Aubergine) et on cherche (Cucumis melo, Melon) → rejet)
    """
    fl = fiche.get("nom_latin", "").lower().strip()
    fc = fiche.get("nom_commun", "").lower().strip()
    nl = nom_latin.lower().strip()
    nc = nom_commun.lower().strip()

    # ── PROTECTION 1 : genres latins différents → impossible même plante ────
    # Ex: fiche (Cucumis melo, Aubergine) vs requête (Solanum melongena, Aubergine)
    #     genre "cucumis" ≠ "solanum" → REJET même si nom_commun identique
    if fl and nl and " " in fl and " " in nl:
        if fl.split()[0] != nl.split()[0]:
            return False

    # ── Correspondance nom latin ─────────────────────────────────────────────
    if nl and fl and (nl == fl or nl in fl or fl in nl):
        # PROTECTION 2 : le latin matche mais les noms communs sont incompatibles
        # Ex: fiche (Cucumis melo, Aubergine) vs requête (Cucumis melo, Melon)
        #     "aubergine" et "melon" n'ont aucun mot en commun → REJET
        if nc and fc and len(nc) >= 4 and len(fc) >= 4:
            has_overlap = (nc in fc or fc in nc or bool(set(nc.split()) & set(fc.split())))
            if not has_overlap:
                return False
        return True

    # ── Correspondance nom commun seul ───────────────────────────────────────
    if nc and fc and len(nc) >= 4 and len(fc) >= 4 and (nc == fc or nc in fc or fc in nc):
        return True
    return False

def load_from_db(nom_latin: str, nom_commun: str = "") -> dict | None:
    """
    Cherche une fiche dans la base avec plusieurs stratégies.
    Chaque candidat est validé par _fiche_matches() avant d'être retourné,
    pour éviter les faux positifs (ex: "Courgette" retournée pour "Tomate").
    """
    nl_safe = _safe(nom_latin)
    nc_safe = _safe(nom_commun) if nom_commun else ""

    # 1. Correspondance exacte sur le nom du fichier (nom_latin)
    for f in DB_ROOT.rglob(f"{nl_safe}.json"):
        try:
            fiche = json.loads(f.read_text(encoding="utf-8"))
            if _fiche_matches(fiche, nom_latin, nom_commun):
                return fiche
        except Exception:
            pass

    # 2. Correspondance exacte sur le nom du fichier (nom_commun)
    if nc_safe:
        for f in DB_ROOT.rglob(f"{nc_safe}.json"):
            try:
                fiche = json.loads(f.read_text(encoding="utf-8"))
                if _fiche_matches(fiche, nom_latin, nom_commun):
                    return fiche
            except Exception:
                pass

    # 3. Correspondance partielle sur le nom de fichier
    # Ex: cherche "Solanum lycopersicum" → trouve "solanum_lycopersicum.json"
    # On utilise le premier mot du nom latin (genre) ET on valide le contenu
    nom_lower   = nom_latin.lower().split()[0] if nom_latin else ""
    nom_c_lower = nom_commun.lower().split()[0] if nom_commun else ""
    for f in DB_ROOT.rglob("*.json"):
        fname = f.stem.lower()
        if (nom_lower and len(nom_lower) >= 4 and nom_lower in fname) or \
           (nom_c_lower and len(nom_c_lower) >= 4 and nom_c_lower in fname):
            try:
                fiche = json.loads(f.read_text(encoding="utf-8"))
                if _fiche_matches(fiche, nom_latin, nom_commun):
                    return fiche
            except Exception:
                pass

    # 4. Scan complet du contenu JSON (dernier recours)
    for f in DB_ROOT.rglob("*.json"):
        try:
            fiche = json.loads(f.read_text(encoding="utf-8"))
            if _fiche_matches(fiche, nom_latin, nom_commun):
                return fiche
        except Exception:
            pass

    return None

def save_to_db(fiche: dict) -> Path:
    cat = fiche.get("categorie", "ornement")
    sub = fiche.get("sous_categorie", "divers")
    folder = DB_ROOT / cat / sub
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{_safe(fiche.get('nom_latin', 'unknown'))}.json"
    path.write_text(json.dumps(fiche, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

def search_db(query: str) -> list[dict]:
    q = query.lower()
    results = []
    for f in DB_ROOT.rglob("*.json"):
        try:
            fiche = json.loads(f.read_text(encoding="utf-8"))
            nc   = fiche.get("nom_commun","").lower()
            nl   = fiche.get("nom_latin","").lower()
            desc = fiche.get("description","").lower()
            # Cherche dans nom_commun, nom_latin ET description
            # Ça protège contre un nom_commun corrompu (ex: "Saucisse" pour "Sauge")
            if q in nc or q in nl or q in desc:
                results.append(fiche)
        except Exception:
            continue
    return results


def repair_nom_commun_from_description() -> int:
    """
    Parcourt la DB et corrige les fiches dont le nom_commun ne correspond pas
    à la description. Ex: nom_commun="Saucisse" mais description parle de "sauge"
    → extrait "Sauge" de la description et corrige.
    """
    repaired = 0
    for f in DB_ROOT.rglob("*.json"):
        try:
            fiche = json.loads(f.read_text(encoding="utf-8"))
            nc   = fiche.get("nom_commun", "")
            desc = fiche.get("description", "")
            if not nc or not desc or len(desc) < 20:
                continue
            # Si le nom_commun n'apparaît pas dans la description → corrompu
            if nc.lower() not in desc.lower():
                # Chercher le vrai nom dans la première phrase de la description
                # Ex: "La sauge est une plante..." → "Sauge"
                import re as _re
                m = _re.match(r"(?:Le|La|Les|L'|L’)\s+([A-Za-zà-ÿ\s\-]+?)\s+est", desc, _re.IGNORECASE)
                if m:
                    vrai_nom = m.group(1).strip().capitalize()
                    if vrai_nom and vrai_nom.lower() != nc.lower() and len(vrai_nom) > 2:
                        print(f"[REPAIR] {nc!r} → {vrai_nom!r} (latin: {fiche.get('nom_latin','')})")
                        fiche["nom_commun"] = vrai_nom
                        f.write_text(json.dumps(fiche, ensure_ascii=False, indent=2), encoding="utf-8")
                        repaired += 1
        except Exception as e:
            print(f"[REPAIR ERROR] {f}: {e}")
    return repaired

def get_db_stats() -> dict:
    stats = {"total": 0, "par_categorie": {}}
    for d in DB_ROOT.iterdir():
        if not d.is_dir():
            continue
        count = sum(1 for _ in d.rglob("*.json"))
        if count:
            stats["par_categorie"][d.name] = count
            stats["total"] += count
    return stats

# ── Mémoire Q&A ───────────────────────────────────────────────────
def find_cached_answer(fiche: dict, question: str, threshold: float = 0.35) -> dict | None:
    qa = fiche.get("qa_memory", {})
    best_score, best = 0.0, None
    cat = detect_qa_cat(question)
    for check_cat in ([cat] + [c for c in qa if c != cat]):
        for entry in qa.get(check_cat, []):
            score = _similarity(question, entry.get("question",""))
            if score > best_score:
                best_score, best = score, entry
    return best if best_score >= threshold else None

def add_qa(fiche: dict, question: str, answer: str) -> dict:
    """RÈGLE : seules les réponses Groq sont mémorisées ici."""
    qa  = fiche.setdefault("qa_memory", {})
    cat = detect_qa_cat(question)
    entries = qa.setdefault(cat, [])
    for entry in entries:
        if _similarity(question, entry["question"]) > 0.7:
            entry["answer"]    = answer
            entry["has_alert"] = contains_alert(answer)
            save_to_db(fiche)
            return fiche
    entries.append({
        "question":  question,
        "answer":    answer,
        "category":  cat,
        "has_alert": contains_alert(answer)
    })
    save_to_db(fiche)
    return fiche

def get_context(fiche: dict, question: str) -> str:
    qa  = fiche.get("qa_memory", {})
    cat = detect_qa_cat(question)
    parts = [
        f"Q:{e['question'][:50]} R:{e['answer'][:80]}"
        for e in qa.get(cat, [])[:2]
    ]
    return ("Mémoire:" + " | ".join(parts)) if parts else ""

def get_qa_summary(fiche: dict) -> dict:
    qa     = fiche.get("qa_memory", {})
    total  = sum(len(v) for v in qa.values())
    alerts = sum(1 for v in qa.values() for e in v if e.get("has_alert"))
    return {"total": total, "par_categorie": {k: len(v) for k,v in qa.items()}, "alertes": alerts}


# ── Nettoyage DB : supprime les fiches corrompues ─────────────────────────────
def _description_contaminee_check(nom_commun: str, nom_latin: str, description: str) -> bool:
    """
    Retourne True si la description semble parler d'une autre plante.
    Utilise des word boundaries pour éviter les faux positifs :
      "rose" NE matche PAS "roses", "arroser", "roseau"
      "pin"  NE matche PAS "pinson", "lapin"
    """
    if not description or len(description) < 60:
        return False
    desc_low   = description.lower()
    mots_cible = [m for m in nom_commun.lower().split() if len(m) > 3]
    genre_latin = nom_latin.lower().split()[0] if nom_latin else ""
    cibles = mots_cible + ([genre_latin] if genre_latin and len(genre_latin) > 3 else [])
    if not cibles:
        return False
    return not any(re.search(r"\b" + re.escape(m) + r"\b", desc_low) for m in cibles)


def purge_corrupted_fiches() -> int:
    """
    Parcourt toute la DB et supprime (ou vide les champs) des fiches corrompues.
    Une fiche est corrompue si :
    - Son nom_latin ne correspond pas à son nom_commun (genres différents entre fiches sœurs)
    - Sa description parle d'une autre plante (détection via nom_commun/latin)

    Retourne le nombre de fiches réparées.
    """
    repaired = 0
    CHAMPS_A_VIDER = [
        "description", "origine_naturelle", "ecosysteme_naturel",
        "biodiversite", "maladies_courantes", "ravageurs",
        "conseil_plantation", "conseil_entretien",
        "floraison", "fructification", "arrosage", "arrosage_frequence",
        "sol_type", "terreau_recommande", "taille", "croissance",
    ]

    # Construire un index nom_commun → (nom_latin attendu, path) depuis les fiches saines
    # Une fiche est "saine" si son nom_latin est cohérent avec son nom_commun (aucune incohérence)
    # Heuristique simple : si description parle de la plante → saine
    fiches_saines: dict[str, str] = {}  # nom_commun.lower() → nom_latin.lower()
    for f in DB_ROOT.rglob("*.json"):
        try:
            fiche = json.loads(f.read_text(encoding="utf-8"))
            nc = fiche.get("nom_commun", "").lower().strip()
            nl = fiche.get("nom_latin", "").lower().strip()
            desc = fiche.get("description", "")
            if nc and nl and desc and not _description_contaminee_check(fiche.get("nom_commun",""), nl, desc):
                fiches_saines[nc] = nl
        except Exception:
            pass

    for f in DB_ROOT.rglob("*.json"):
        try:
            fiche = json.loads(f.read_text(encoding="utf-8"))
            nc = fiche.get("nom_commun", "")
            nl = fiche.get("nom_latin", "")
            desc = fiche.get("description", "")
            dirty = False

            # Vérification 1 : description parle d'une autre plante
            if _description_contaminee_check(nc, nl, desc):
                for champ in CHAMPS_A_VIDER:
                    if fiche.get(champ) and isinstance(fiche[champ], str):
                        fiche[champ] = ""
                dirty = True

            # Vérification 2 : nom_latin incohérent avec le nom_commun connu
            # Ex: fiche {Aubergine, Cucumis melo} → on sait qu'Aubergine = Solanum melongena
            nc_low = nc.lower().strip()
            nl_low = nl.lower().strip()
            if nl_low and nc_low in fiches_saines:
                expected_nl = fiches_saines[nc_low]
                # Genres latins différents → ce nom_latin est une hallucination
                if " " in nl_low and " " in expected_nl:
                    if nl_low.split()[0] != expected_nl.split()[0]:
                        # Corriger le nom_latin avec la valeur connue
                        fiche["nom_latin"] = expected_nl.title().replace("_", " ")
                        # Vider aussi les champs texte car probablement contaminés
                        for champ in CHAMPS_A_VIDER:
                            if fiche.get(champ) and isinstance(fiche[champ], str):
                                fiche[champ] = ""
                        dirty = True

            if dirty:
                f.write_text(json.dumps(fiche, ensure_ascii=False, indent=2), encoding="utf-8")
                repaired += 1
                print(f"[DB CLEANUP] Fiche réparée : {nc} ({nl}) → {f.name}")

        except Exception as e:
            print(f"[DB CLEANUP] Erreur sur {f}: {e}")

    return repaired