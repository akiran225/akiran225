import json, os, requests

GROQ_KEY  = os.getenv("GROQ_API_KEY","")
GROQ_URL  = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL= "llama-3.3-70b-versatile"

# ── Filtres jardin ────────────────────────────────────────────────
GARDEN_FILTERS = {
    "☀️ Lumière": {
        "Mi-ombre":     "zone ombragée sous couvert arboré, sol frais et humifère",
        "Plein soleil": "exposition directe plus de 6h/jour, chaleur",
        "Ombre totale": "exposition nord, ombre totale, sol frais",
    },
    "🧭 Orientation": {
        "Nord":  "exposition nord, ombre totale, sol frais",
        "Sud":   "exposition sud, chaleur intense, sécheresse",
        "Est":   "exposition est, soleil matinal, doux",
        "Ouest": "exposition ouest, soleil après-midi, chaud",
    },
    "🌍 Ambiance": {
        "Prairie":       "sol pauvre ensoleillé, calcaire ou neutre, sec",
        "Haie":          "bordure, haie vive, résistant au vent",
        "Jardin urbain": "espace réduit, pollution, microclimat urbain",
        "Potager":       "légumes, fruits, protection, association",
        "Zone humide":   "sol constamment humide, bord de mare ou berge",
        "Mare / Étang":  "zone aquatique ou semi-aquatique",
    },
    "🪨 Sol": {
        "Argileux":  "sol lourd, retient l'eau, riche",
        "Sableux":   "sol léger, drainant, pauvre, sec",
        "Calcaire":  "sol basique, pH élevé, sec en surface",
        "Limoneux":  "sol équilibré, fertile, profond",
        "Pot / Bac": "conteneur, volume limité, arrosage fréquent",
    },
    "❄️ Résistance": {
        "Rustique −15°C":     "zone froide, gel fort, altitude",
        "Semi-rustique −5°C": "gel léger à modéré, régions tempérées",
        "Frileux 0°C min":    "hors-gel, méditerranéen ou intérieur",
    }
}

DISEASE_CATS = {
    "🍂 Feuilles": [
        "Feuilles jaunissantes","Feuilles qui brunissent","Taches noires sur feuilles",
        "Feuilles qui tombent prématurément","Feuilles déformées","Taches blanches / oïdium",
    ],
    "🌱 Sol & Racines": [
        "Trop de mousse","Sol acide","Sol compacté","Pourriture des racines",
        "Plante sèche malgré l'arrosage",
    ],
    "🐛 Ravageurs": [
        "Pucerons","Cochenilles","Limaces et escargots","Chenilles",
        "Araignées rouges","Mouche blanche",
    ],
    "🌳 Arbre": [
        "Arbre qui dépérit","Branches mortes","Écorce qui se décolle",
        "Champignons sur le tronc","Gui / parasites",
    ],
    "🌸 Floraison": [
        "Plante ne fleurit pas","Fleurs qui tombent prématurément","Bourgeons qui n'ouvrent pas",
    ]
}

SOIL_SYMPTOMS = [
    "Trop de mousse","Végétation rabougrie","Sol très compact",
    "Sol très acide (rumex, prêle, joncs)","Sol basique (coquelicots, bleuets)",
    "Sol engorgé / asphyxie","Sol sableux / très sec","Manque de vers de terre"
]

ECOSYSTEMS = [
    "Chênaie atlantique","Garrigue méditerranéenne","Prairie calcicole",
    "Forêt alluviale","Lande à bruyères","Bord de mare","Haie bocagère","Pelouse sèche"
]

# ── Groq bas niveau ───────────────────────────────────────────────
def _g_json(prompt: str, system: str) -> list | dict | None:
    if not GROQ_KEY: return None
    try:
        r = requests.post(GROQ_URL, headers={
            "Authorization": f"Bearer {GROQ_KEY}","Content-Type":"application/json"
        }, json={
            "model":GROQ_MODEL,
            "messages":[{"role":"system","content":system},{"role":"user","content":prompt}],
            "max_tokens":1500,"temperature":0.3
        }, timeout=30)
        r.raise_for_status()
        t = r.json()["choices"][0]["message"]["content"]
        return json.loads(t.replace("```json","").replace("```","").strip())
    except Exception:
        return None

def _g_text(messages: list, system: str) -> str:
    if not GROQ_KEY: return "⚠️ GROQ_API_KEY manquante"
    try:
        r = requests.post(GROQ_URL, headers={
            "Authorization": f"Bearer {GROQ_KEY}","Content-Type":"application/json"
        }, json={
            "model":GROQ_MODEL,
            "messages":[{"role":"system","content":system}]+messages,
            "max_tokens":1000,"temperature":0.5
        }, timeout=30)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Erreur : {e}"

# ── Fonctions publiques ───────────────────────────────────────────
def suggest_plants(conditions: list, existing: list = None) -> list[dict]:
    p = f"""Conditions : {', '.join(conditions)}
Plantes déjà présentes : {', '.join(existing) if existing else 'aucune'}
Propose 5 plantes parfaitement adaptées. Si plantes existantes, assure la compatibilité.
Réponds UNIQUEMENT en JSON : [{{"nom":"...","nom_latin":"...","emoji":"...","pourquoi":"raison courte","associations":"bonnes associations","incompatibilites":"à éviter","biodiversite":"rôle faune","alerte":""}}]
Note alerte seulement si toxique ou invasive."""
    r = _g_json(p,"Tu es botaniste expert. Réponds uniquement en JSON valide.")
    return r if isinstance(r,list) else []

def check_compatibility(a: str, b: str) -> dict:
    p = f"""Compatibilité entre "{a}" et "{b}" dans un jardin.
Réponds UNIQUEMENT en JSON : {{"compatible":true/false,"niveau":"excellent/bon/moyen/déconseillé","raison":"explication","conseils":"comment associer ou éviter","distance":"si applicable"}}"""
    r = _g_json(p,"Tu es botaniste expert. Réponds uniquement en JSON valide.")
    return r or {"compatible":None,"raison":"Impossible d'analyser","conseils":""}

def get_ecosystem_plants(ecosystem: str) -> list[dict]:
    p = f"""Pour l'écosystème "{ecosystem}", liste 8 plantes caractéristiques avec différentes strates.
Réponds UNIQUEMENT en JSON : [{{"nom":"...","nom_latin":"...","strate":"arbre/arbuste/herbacée/liane","role_ecosysteme":"...","emoji":"..."}}]"""
    r = _g_json(p,"Tu es écologue expert. Réponds uniquement en JSON valide.")
    return r if isinstance(r,list) else []

def diagnose_problem(symptom: str, plant: str = None, details: str = None) -> dict:
    ctx = (f"Plante : {plant}\n" if plant else "") + (f"Détails : {details}\n" if details else "")
    p = f"""{ctx}Problème : {symptom}
Réponds UNIQUEMENT en JSON :
{{"diagnostic":"...","gravite":"faible/moyenne/élevée","causes":["..."],"solutions_naturelles":["...","...","..."],"solution_chimique":"si vraiment nécessaire sinon vide","prevention":"...","urgence":false,"alerte_toxicite":""}}"""
    r = _g_json(p,"Tu es phytopathologiste expert. Solutions naturelles en premier. Réponds en JSON valide.")
    return r or {"diagnostic":"Impossible à diagnostiquer","solutions_naturelles":[],"gravite":"inconnue"}

def diagnose_soil(symptoms: list) -> dict:
    p = f"""Problèmes de sol : {', '.join(symptoms)}
Réponds UNIQUEMENT en JSON :
{{"diagnostic":"...","ph_probable":"acide/neutre/alcalin","causes":["..."],"amendements":["...","..."],"plantes_indicatrices":"...","temps_correction":"...","conseils":"..."}}"""
    r = _g_json(p,"Tu es pédologue expert. Réponds uniquement en JSON valide.")
    return r or {}

def chat_associations(messages: list, filters: list, existing: list) -> str:
    system = f"""Tu es expert en associations végétales et design de jardin écologique.
Tu connais la permaculture, les guildes de plantes et les écosystèmes naturels.
Mentionne distances, périodes, bénéfices réciproques et incompatibilités.
Contexte jardin : {', '.join(filters) if filters else 'non précisé'}
Plantes présentes : {', '.join(existing) if existing else 'aucune'}"""
    return _g_text(messages, system)