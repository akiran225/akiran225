# 🌿 Slothia — Guide d'installation complet

## Structure du projet

```
slothia/
│
├── main.py           → Lance tout. Commande : streamlit run main.py
├── app.py            → Interface Streamlit (5 onglets + paresseux)
├── ia.py             → Pipeline : Wikipedia → Groq → Mémoire
├── memory.py         → Base de données JSON + Q&A par plante
├── associations.py   → Associations, filtres jardin, maladies
├── sloth.py          → Paresseux mascotte (7 tenues, 8 poses)
│
├── database/         → Fiches créées automatiquement
│   ├── arbres/
│   ├── fleurs/
│   ├── plantes_sauvages/
│   ├── ornement/
│   ├── interieur/
│   ├── buissons/
│   ├── semi_aquatique/
│   └── aquatique/
│
├── requirements.txt  → Dépendances
├── .env.example      → Modèle de configuration
└── .env              → TES clés API (à créer toi-même, ne jamais partager)
```

---

## ÉTAPE 1 — Installe Python

Vérifie que Python 3.10 ou plus est installé :
```
python --version
```

Si non installé → https://www.python.org/downloads/
Sur Windows : coche "Add Python to PATH" pendant l'installation.

---

## ÉTAPE 2 — Crée ta clé Groq (l'IA qui répond)

1. Va sur → https://console.groq.com
2. Crée un compte gratuit
3. Clique "API Keys" dans le menu gauche
4. Clique "Create API Key" et donne-lui un nom (ex: slothia)
5. Copie la clé — elle commence par `gsk_`
6. Garde-la, tu en as besoin à l'étape 4

Gratuit : 14 400 requêtes / jour.

---

## ÉTAPE 3 — Crée ta clé PlantNet (reconnaissance photo)

1. Va sur → https://my.plantnet.org
2. Crée un compte gratuit
3. Dans ton profil, trouve "API Access"
4. Copie ta clé API

Gratuit : 500 photos / jour.

---

## ÉTAPE 4 — Crée le fichier .env

Dans le dossier `slothia/`, crée un fichier nommé exactement `.env`
(pas `.env.txt` — juste `.env`) et colle ceci dedans :

```
GROQ_API_KEY=gsk_ta_vraie_clé_ici
PLANTNET_API_KEY=ta_vraie_clé_plantnet_ici
```

Remplace par tes vraies clés.
⚠️ Ne partage jamais ce fichier.

---

## ÉTAPE 5 — Installe les dépendances

Ouvre un terminal dans le dossier `slothia/` et lance :

```
pip install -r requirements.txt
```

Si erreur sur Windows : essaie `pip3 install -r requirements.txt`

---

## ÉTAPE 6 — Lance l'application

```
streamlit run main.py
```

L'application s'ouvre dans ton navigateur sur http://localhost:8501
Pour l'arrêter : Ctrl+C dans le terminal.

---

## Ce que fait le paresseux

Le paresseux dans la sidebar change automatiquement :

| Situation                     | Pose        | Tenue               |
|-------------------------------|-------------|---------------------|
| Démarrage                     | Wave        | Saison actuelle     |
| En train de chercher          | Thinking    | Inchangée           |
| Plante identifiée             | Excited     | Saison actuelle     |
| Plante aquatique              | Talking     | Aquatique (masque)  |
| Plante toxique détectée       | Alert       | Combinaison ☣️      |
| Réponse prête                 | Talking     | Inchangée           |
| Alerte dans une réponse       | Alert       | Combinaison ☣️      |

Tu peux aussi changer sa tenue manuellement depuis la sidebar.

---

## Mise en ligne gratuite (Streamlit Cloud)

1. Crée un compte GitHub → https://github.com
2. Crée un dépôt public, uploade tous les fichiers sauf `.env`
3. Va sur https://streamlit.io/cloud → "New app"
4. Connecte ton dépôt GitHub et choisis `main.py`
5. Dans "Advanced settings" → "Secrets", ajoute :
   ```
   GROQ_API_KEY = "gsk_..."
   PLANTNET_API_KEY = "..."
   ```
6. Clique Deploy — ton appli est en ligne, lien partageable

---

## Problèmes fréquents

**"Module not found"**
→ Relance `pip install -r requirements.txt`

**"GROQ_API_KEY manquante"**
→ Vérifie que le fichier `.env` est dans `slothia/` et que la clé est correcte

**"PlantNet ne répond pas"**
→ Vérifie ta connexion et ta clé PlantNet

**L'appli ne s'ouvre pas automatiquement**
→ Va manuellement sur http://localhost:8501

---

## Pour la suite

Quand tu veux ajouter la reconnaissance faune (insectes, oiseaux) :
→ Crée `faune.py` sur le modèle de `associations.py`
→ Ajoute un onglet dans `app.py`
→ Ajoute les nouvelles poses au paresseux dans `sloth.py`

Nuages, phases de lune → même principe, un module par thème.
