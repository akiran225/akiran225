## Slothia, Assistant Botanique IA

> Base de connaissance vivante pour les amateurs et professionnels de jardinage.




## L'histoire du projet

Slothia est né en juin 2025 d'un constat simple : en travaillant en jardinerie, j'ai remarqué que beaucoup de clients repartaient avec une plante sans vraiment savoir comment en prendre soin. Les questions étaient souvent les mêmes, quel terreau, quelle exposition, comment reconnaître une maladie, et les réponses n'étaient pas toujours accessibles au bon moment.

L'idée était de créer un assistant qui puisse répondre à ces questions de façon fiable, simple, et disponible à tout moment. Pas un outil pour les experts, mais quelque chose que n'importe qui puisse utiliser.



## Fonctionnalités

### Identifier
- Identification de plantes par photo via **PlantNet API** (galerie ou caméra)
- Génération automatique d'une fiche technique complète (Wikipedia → Trefle.io → Groq)
- Analyse de maladies, problèmes de sol et compositions par **Llama 4 Vision**

### Question
- Chat libre spécialisé en botanique (Llama 3.3 70B via Groq)
- Détection automatique des plantes mentionnées → fiche enrichie en temps réel
- Analyse photo intégrée (maladie, ravageur, composition de plantes)
- Contexte maladie automatique (symptômes → diagnostic → solutions naturelles)

### Jardin
- Registre personnel de plantes avec photo, emplacement, exposition, notes
- Tableau de bord (pleine terre / pot)

### ️ Base
- Base de données locale JSON enrichie automatiquement à chaque interaction
- Recherche plein texte
- Ajout manuel de plantes



## ️ Architecture

 
Slothia
├── app.py # Interface Streamlit
├── ia.py # Moteur IA (Wikipedia → Trefle → Groq)
├── memory.py # Gestion base de données JSON
├── associations.py # Filtres, compatibilité, diagnostic
├── sloth.py # Mascotte animée (SVG)
└── database/ # Fiches plantes JSON (auto-générées)
 

| Composant | Technologie |
|--|-|
| Interface | Streamlit (Python) |
| LLM texte | Llama 3.3 70B via Groq |
| LLM vision | Llama 4 Scout via Groq |
| Identification | PlantNet API |
| Données botaniques | Wikipedia API + Trefle.io |
| Stockage | JSON local (RAG pattern) |



## Installation

### Prérequis
- Python 3.10+
- Clés API : Groq, PlantNet, Trefle.io (optionnel)

### Lancer le projet

 bash
git clone https://github.com/akiran225/slothia.git
cd slothia
pip install streamlit requests python-dotenv
cp .env.example .env
# Remplir .env avec vos clés API
streamlit run app.py
 

### Variables d'environnement

 env
GROQ_API_KEY=votre_clé_groq
PLANTNET_API_KEY=votre_clé_plantnet
TREFLE_API_KEY=votre_clé_trefle # optionnel
 



## Comment ça fonctionne

 
Question utilisateur
 ↓
Détection de la plante dans le message
 ↓
Cache local → réponse instantanée si déjà connue
 ↓ sinon
Wikipedia FR → données vérifiées
 ↓
Trefle.io → données certifiées (pH, hauteur, résistance froid…)
 ↓
Groq (Llama 3.3 70B) → synthèse en français
 ↓
Sauvegarde JSON → la base s'enrichit à chaque interaction
 



## Roadmap

- [ ] Améliorer les performances et la précision des réponses
- [ ] Déploiement cloud
- [ ] APK Android
- [ ] Fallback multi-modèles (OpenRouter)



## ‍ Auteur

Projet développé par **akiran225**.
![Profile Views](https://komarev.com/ghpvc/?username=akiran225&color=green&style=flat)
