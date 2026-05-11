"""
populate_db.py — Peuplement automatique de la base Slothia
Catalogue : Maison Barrault (vivaces, aromatiques, potagères, graminées, fougères)

Utilisation :
    python populate_db.py

Le script crée les fiches une par une via le pipeline complet
Wikipedia + Trefle + LLM. Lance-le et laisse tourner (30-60 min).

En cas d'interruption, relance-le : les fiches déjà créées sont
ignorées (cache local), seules les manquantes sont créées.
"""

import sys, time, os
sys.path.insert(0, ".")
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from ia import get_or_create_fiche
from memory import save_to_db

# ─────────────────────────────────────────────────────────────────────────────
# FORMAT : (nom_commun, nom_latin, categorie_forcee)
# La catégorie forcée écrase detect_category pour les cas ambigus
# ─────────────────────────────────────────────────────────────────────────────

PLANTES = [

    # ══════════════════════════════════════════════════════════════════
    # PLANTES VERTES (intérieur)
    # ══════════════════════════════════════════════════════════════════
    ("Acalypha",          "Acalypha hispida",           "plantes_vertes"),
    ("Adiantum",          "Adiantum raddianum",         "plantes_vertes"),
    ("Alocasia",          "Alocasia amazonica",         "plantes_vertes"),
    ("Asparagus",         "Asparagus plumosus",         "plantes_vertes"),
    ("Asplenium",         "Asplenium antiquum",         "plantes_vertes"),
    ("Calathea",          "Calathea orbifolia",         "plantes_vertes"),
    ("Chamaedorea",       "Chamaedorea elegans",        "plantes_vertes"),
    ("Chlorophytum",      "Chlorophytum comosum",       "plantes_vertes"),
    ("Codiaeum",          "Codiaeum variegatum",        "plantes_vertes"),
    ("Coffea",            "Coffea arabica",             "plantes_vertes"),
    ("Cordyline",         "Cordyline fruticosa",        "plantes_vertes"),
    ("Dieffenbachia",     "Dieffenbachia seguine",      "plantes_vertes"),
    ("Dracaena",          "Dracaena marginata",         "plantes_vertes"),
    ("Ficus benjamina",   "Ficus benjamina",            "plantes_vertes"),
    ("Ficus elastica",    "Ficus elastica",             "plantes_vertes"),
    ("Fittonia",          "Fittonia albivenis",         "plantes_vertes"),
    ("Gasteria",          "Gasteria bicolor",           "plantes_vertes"),
    ("Hedera",            "Hedera helix",               "plantes_vertes"),
    ("Monstera",          "Monstera deliciosa",         "plantes_vertes"),
    ("Peperomia",         "Peperomia caperata",         "plantes_vertes"),
    ("Philodendron",      "Philodendron hederaceum",    "plantes_vertes"),
    ("Pilea",             "Pilea peperomioides",        "plantes_vertes"),
    ("Pothos",            "Epipremnum aureum",          "plantes_vertes"),
    ("Sansevieria",       "Sansevieria trifasciata",    "plantes_vertes"),
    ("Schefflera",        "Schefflera arboricola",      "plantes_vertes"),
    ("Spathiphyllum",     "Spathiphyllum wallisii",     "plantes_vertes"),
    ("Strelitzia",        "Strelitzia reginae",         "plantes_vertes"),
    ("Syngonium",         "Syngonium podophyllum",      "plantes_vertes"),
    ("Tradescantia",      "Tradescantia zebrina",       "plantes_vertes"),
    ("Yucca",             "Yucca elephantipes",         "plantes_vertes"),
    ("Zamioculcas",       "Zamioculcas zamiifolia",     "plantes_vertes"),

    # ══════════════════════════════════════════════════════════════════
    # PLANTES GRASSES
    # ══════════════════════════════════════════════════════════════════
    ("Crassula",          "Crassula ovata",             "plantes_grasses"),
    ("Delosperma",        "Delosperma cooperi",         "plantes_grasses"),
    ("Echeveria",         "Echeveria elegans",          "plantes_grasses"),
    ("Haworthia",         "Haworthia attenuata",        "plantes_grasses"),
    ("Kalanchoe",         "Kalanchoe blossfeldiana",    "plantes_grasses"),
    ("Opuntia",           "Opuntia microdasys",         "plantes_grasses"),
    ("Sedum album",       "Sedum album",                "plantes_grasses"),
    ("Sedum spectabile",  "Sedum spectabile",           "plantes_grasses"),
    ("Sempervivum",       "Sempervivum tectorum",       "plantes_grasses"),

    # ══════════════════════════════════════════════════════════════════
    # GRAMINÉES
    # ══════════════════════════════════════════════════════════════════
    ("Bouteloua",         "Bouteloua gracilis",         "graminees"),
    ("Briza",             "Briza media",                "graminees"),
    ("Calamagrostis",     "Calamagrostis acutiflora",   "graminees"),
    ("Carex brune",       "Carex buchananii",           "graminees"),
    ("Carex morrowii",    "Carex morrowii",             "graminees"),
    ("Cortaderia",        "Cortaderia selloana",        "graminees"),
    ("Deschampsia",       "Deschampsia cespitosa",      "graminees"),
    ("Elymus",            "Elymus arenarius",           "graminees"),
    ("Eragrostis",        "Eragrostis spectabilis",     "graminees"),
    ("Festuca",           "Festuca glauca",             "graminees"),
    ("Hakonechloa",       "Hakonechloa macra",          "graminees"),
    ("Helictotrichon",    "Helictotrichon sempervirens","graminees"),
    ("Miscanthus",        "Miscanthus sinensis",        "graminees"),
    ("Molinia",           "Molinia caerulea",           "graminees"),
    ("Panicum",           "Panicum virgatum",           "graminees"),
    ("Pennisetum",        "Pennisetum alopecuroides",   "graminees"),
    ("Phalaris",          "Phalaris arundinacea",       "graminees"),
    ("Phragmites",        "Phragmites australis",       "graminees"),
    ("Stipa",             "Stipa tenuissima",           "graminees"),

    # ══════════════════════════════════════════════════════════════════
    # FOUGÈRES
    # ══════════════════════════════════════════════════════════════════
    ("Asplenium scolopendrium","Asplenium scolopendrium","fougeres"),
    ("Athyrium",          "Athyrium niponicum",         "fougeres"),
    ("Dryopteris",        "Dryopteris filix-mas",       "fougeres"),
    ("Fougère mâle",      "Dryopteris wallichiana",     "fougeres"),
    ("Matteuccia",        "Matteuccia struthiopteris",  "fougeres"),
    ("Osmunda",           "Osmunda regalis",            "fougeres"),
    ("Polystichum",       "Polystichum aculeatum",      "fougeres"),
    ("Pteris",            "Pteris cretica",             "fougeres"),

    # ══════════════════════════════════════════════════════════════════
    # PLANTES AQUATIQUES
    # ══════════════════════════════════════════════════════════════════
    ("Alisma",            "Alisma plantago-aquatica",   "plantes_aquatiques"),
    ("Butomus",           "Butomus umbellatus",         "plantes_aquatiques"),
    ("Caltha palustris",  "Caltha palustris",           "plantes_aquatiques"),
    ("Equisetum",         "Equisetum hyemale",          "plantes_aquatiques"),
    ("Hippuris",          "Hippuris vulgaris",          "plantes_aquatiques"),
    ("Iris pseudacorus",  "Iris pseudacorus",           "plantes_aquatiques"),
    ("Juncus",            "Juncus inflexus",            "plantes_aquatiques"),
    ("Nymphaea",          "Nymphaea alba",              "plantes_aquatiques"),
    ("Pontederia",        "Pontederia cordata",         "plantes_aquatiques"),
    ("Sagittaria",        "Sagittaria japonica",        "plantes_aquatiques"),
    ("Typha",             "Typha angustifolia",         "plantes_aquatiques"),

    # ══════════════════════════════════════════════════════════════════
    # PLANTES AROMATIQUES
    # ══════════════════════════════════════════════════════════════════
    ("Aneth",             "Anethum graveolens",         "plantes_aromatiques"),
    ("Basilic",           "Ocimum basilicum",           "plantes_aromatiques"),
    ("Basilic pourpre",   "Ocimum basilicum purpureum", "plantes_aromatiques"),
    ("Basilic Thai",      "Ocimum basilicum thyrsiflorum","plantes_aromatiques"),
    ("Bourrache",         "Borago officinalis",         "plantes_aromatiques"),
    ("Camomille romaine", "Chamaemelum nobile",         "plantes_aromatiques"),
    ("Ciboulette",        "Allium schoenoprasum",       "plantes_aromatiques"),
    ("Coriandre",         "Coriandrum sativum",         "plantes_aromatiques"),
    ("Estragon",          "Artemisia dracunculus",      "plantes_aromatiques"),
    ("Fenouil",           "Foeniculum vulgare",         "plantes_aromatiques"),
    ("Gaillet odorant",   "Galium odoratum",            "plantes_aromatiques"),
    ("Lavande officinale","Lavandula angustifolia",     "plantes_aromatiques"),
    ("Lavande stoechas",  "Lavandula stoechas",         "plantes_aromatiques"),
    ("Laurier",           "Laurus nobilis",             "plantes_aromatiques"),
    ("Mélisse",           "Melissa officinalis",        "plantes_aromatiques"),
    ("Menthe aquatique",  "Mentha aquatica",            "plantes_aromatiques"),
    ("Menthe bergamote",  "Mentha citrata",             "plantes_aromatiques"),
    ("Menthe chocolat",   "Mentha piperita chocolat",   "plantes_aromatiques"),
    ("Menthe poivrée",    "Mentha piperita",            "plantes_aromatiques"),
    ("Menthe pomélo",     "Mentha suaveolens",          "plantes_aromatiques"),
    ("Origan",            "Origanum vulgare",           "plantes_aromatiques"),
    ("Persil",            "Petroselinum crispum",       "plantes_aromatiques"),
    ("Romarin",           "Salvia rosmarinus",          "plantes_aromatiques"),
    ("Sauge officinale",  "Salvia officinalis",         "plantes_aromatiques"),
    ("Thym",              "Thymus vulgaris",            "plantes_aromatiques"),
    ("Thym citron",       "Thymus citriodorus",         "plantes_aromatiques"),
    ("Thym serpolet",     "Thymus serpyllum",           "plantes_aromatiques"),

    # ══════════════════════════════════════════════════════════════════
    # PLANTES ÉCO-SOLUTION (mellifères, auxiliaires, biodiversité)
    # ══════════════════════════════════════════════════════════════════
    ("Bourrache officinale","Borago officinalis",       "plantes_eco_solution"),
    ("Gypsophile",        "Gypsophila paniculata",      "plantes_eco_solution"),
    ("Helianthus",        "Helianthus annuus",          "plantes_eco_solution"),
    ("Lupin",             "Lupinus polyphyllus",        "plantes_eco_solution"),
    ("Phacélie",          "Phacelia tanacetifolia",     "plantes_eco_solution"),
    ("Souci",             "Calendula officinalis",      "plantes_eco_solution"),
    ("Tagète",            "Tagetes patula",             "plantes_eco_solution"),
    ("Tanaisie",          "Tanacetum vulgare",          "plantes_eco_solution"),
    ("Verveine de Buenos Aires","Verbena bonariensis",  "plantes_eco_solution"),

    # ══════════════════════════════════════════════════════════════════
    # POTAGÈRES
    # ══════════════════════════════════════════════════════════════════
    ("Artichaut",         "Cynara cardunculus scolymus","potageres"),
    ("Aubergine",         "Solanum melongena",          "potageres"),
    ("Basilic grand vert","Ocimum basilicum",           "plantes_aromatiques"),
    ("Betterave",         "Beta vulgaris",              "potageres"),
    ("Carotte",           "Daucus carota",              "potageres"),
    ("Chou",              "Brassica oleracea",          "potageres"),
    ("Concombre",         "Cucumis sativus",            "potageres"),
    ("Courgette",         "Cucurbita pepo",             "potageres"),
    ("Courge",            "Cucurbita maxima",           "potageres"),
    ("Épinard",           "Spinacia oleracea",          "potageres"),
    ("Fraise",            "Fragaria × ananassa",        "potageres"),
    ("Framboisier",       "Rubus idaeus",               "potageres"),
    ("Groseillier",       "Ribes rubrum",               "potageres"),
    ("Haricot",           "Phaseolus vulgaris",         "potageres"),
    ("Laitue",            "Lactuca sativa",             "potageres"),
    ("Melon",             "Cucumis melo",               "potageres"),
    ("Myrtillier",        "Vaccinium corymbosum",       "potageres"),
    ("Oignon",            "Allium cepa",                "potageres"),
    ("Patate douce",      "Ipomoea batatas",            "potageres"),
    ("Piment",            "Capsicum annuum",            "potageres"),
    ("Poireau",           "Allium porrum",              "potageres"),
    ("Poivron",           "Capsicum annuum",            "potageres"),
    ("Pourpier",          "Portulaca oleracea",         "potageres"),
    ("Radis",             "Raphanus sativus",           "potageres"),
    ("Tomate",            "Solanum lycopersicum",       "potageres"),

    # ══════════════════════════════════════════════════════════════════
    # PLANTES ANNUELLES
    # ══════════════════════════════════════════════════════════════════
    ("Antirrhinum",       "Antirrhinum majus",          "plantes_annuelles"),
    ("Bégonia semperflorens","Begonia semperflorens",   "plantes_annuelles"),
    ("Calibrachoa",       "Calibrachoa",                "plantes_annuelles"),
    ("Capucine",          "Tropaeolum majus",           "plantes_annuelles"),
    ("Cosmos",            "Cosmos bipinnatus",          "plantes_annuelles"),
    ("Gazania",           "Gazania rigens",             "plantes_annuelles"),
    ("Impatiens",         "Impatiens walleriana",       "plantes_annuelles"),
    ("Lobelia",           "Lobelia erinus",             "plantes_annuelles"),
    ("Lobularia",         "Lobularia maritima",         "plantes_annuelles"),
    ("Nigelle",           "Nigella damascena",          "plantes_annuelles"),
    ("Pétunia",           "Petunia × hybrida",          "plantes_annuelles"),
    ("Pois de senteur",   "Lathyrus odoratus",          "plantes_annuelles"),
    ("Zinnia",            "Zinnia elegans",             "plantes_annuelles"),

    # ══════════════════════════════════════════════════════════════════
    # PLANTES BISANNUELLES
    # ══════════════════════════════════════════════════════════════════
    ("Digitale",          "Digitalis purpurea",         "plantes_bisannuelles"),
    ("Giroflée",          "Erysimum cheiri",            "plantes_bisannuelles"),
    ("Lunaire",           "Lunaria annua",              "plantes_bisannuelles"),
    ("Myosotis",          "Myosotis sylvatica",         "plantes_bisannuelles"),
    ("Pensée",            "Viola × wittrockiana",       "plantes_bisannuelles"),
    ("Rose trémière",     "Alcea rosea",                "plantes_bisannuelles"),

    # ══════════════════════════════════════════════════════════════════
    # PLANTES ANNUELLES (complément)
    # ══════════════════════════════════════════════════════════════════
    ("Brachycome",        "Brachyscome iberidifolia",    "plantes_annuelles"),
    ("Celosia",           "Celosia argentea",            "plantes_annuelles"),
    ("Cleome",            "Cleome hassleriana",          "plantes_annuelles"),
    ("Coleus",            "Coleus scutellarioides",      "plantes_annuelles"),
    ("Cosmos atrosanguineus","Cosmos atrosanguineus",    "plantes_annuelles"),
    ("Dahlia",            "Dahlia pinnata",              "plantes_annuelles"),
    ("Dorotheanthus",     "Dorotheanthus bellidiformis", "plantes_annuelles"),
    ("Felicia",           "Felicia amelloides",          "plantes_annuelles"),
    ("Heliotropium",      "Heliotropium arborescens",    "plantes_annuelles"),
    ("Isotoma",           "Isotoma axillaris",           "plantes_annuelles"),
    ("Matthiola",         "Matthiola incana",            "plantes_annuelles"),
    ("Mecardonia",        "Mecardonia acuminata",        "plantes_annuelles"),
    ("Nemesia",           "Nemesia strumosa",            "plantes_annuelles"),
    ("Nicotiana",         "Nicotiana alata",             "plantes_annuelles"),
    ("Osteospermum",      "Osteospermum ecklonis",       "plantes_annuelles"),
    ("Scaevola",          "Scaevola aemula",             "plantes_annuelles"),
    ("Thunbergia",        "Thunbergia alata",            "plantes_annuelles"),

    # ══════════════════════════════════════════════════════════════════
    # PLANTES BISANNUELLES (complément)
    # ══════════════════════════════════════════════════════════════════
    ("Bellis",            "Bellis perennis",             "plantes_bisannuelles"),
    ("Papaver nudicaule", "Papaver nudicaule",           "plantes_bisannuelles"),

    # ══════════════════════════════════════════════════════════════════
    # CHRYSANTHÈMES
    # ══════════════════════════════════════════════════════════════════
    ("Chrysanthème",      "Chrysanthemum × morifolium",  "chrysanthemes"),

    # ══════════════════════════════════════════════════════════════════
    # PLANTES DES FÊTES
    # ══════════════════════════════════════════════════════════════════
    ("Amaryllis",         "Hippeastrum hybridum",       "plantes_fetes"),
    ("Cyclamen",          "Cyclamen persicum",          "plantes_fetes"),
    ("Hellébore",         "Helleborus niger",           "plantes_fetes"),
    ("Houx",              "Ilex aquifolium",            "plantes_fetes"),
    ("Kalanchoe fêtes",   "Kalanchoe blossfeldiana",    "plantes_fetes"),
    ("Poinsettia",        "Euphorbia pulcherrima",      "plantes_fetes"),
    ("Skimmia",           "Skimmia japonica",           "plantes_fetes"),

    # ══════════════════════════════════════════════════════════════════
    # PLANTES VIVACES (le cœur du catalogue Maison Barrault)
    # ══════════════════════════════════════════════════════════════════
    ("Acanthus",          "Acanthus mollis",            "plantes_vivaces"),
    ("Achillea",          "Achillea millefolium",       "plantes_vivaces"),
    ("Achillea filipendulina","Achillea filipendulina", "plantes_vivaces"),
    ("Aconitum",          "Aconitum napellus",          "plantes_vivaces"),
    ("Acorus",            "Acorus calamus",             "plantes_vivaces"),
    ("Agapanthus",        "Agapanthus africanus",       "plantes_vivaces"),
    ("Agastache",         "Agastache foeniculum",       "plantes_vivaces"),
    ("Agastache aurantiaca","Agastache aurantiaca",     "plantes_vivaces"),
    ("Ajuga",             "Ajuga reptans",              "plantes_vivaces"),
    ("Alchemilla",        "Alchemilla mollis",          "plantes_vivaces"),
    ("Allium millenium",  "Allium millenium",           "plantes_vivaces"),
    ("Aloe vera",         "Aloe vera",                  "plantes_vivaces"),
    ("Alstroemeria",      "Alstroemeria aurea",         "plantes_vivaces"),
    ("Anchusa",           "Anchusa azurea",             "plantes_vivaces"),
    ("Anemone hybrida",   "Anemone × hybrida",         "plantes_vivaces"),
    ("Anemone blanda",    "Anemone blanda",             "plantes_vivaces"),
    ("Anemone hupehensis","Anemone hupehensis",         "plantes_vivaces"),
    ("Anthemis",          "Anthemis tinctoria",         "plantes_vivaces"),
    ("Aquilegia",         "Aquilegia vulgaris",         "plantes_vivaces"),
    ("Arabis",            "Arabis caucasica",           "plantes_vivaces"),
    ("Arenaria",          "Arenaria montana",           "plantes_vivaces"),
    ("Armeria",           "Armeria maritima",           "plantes_vivaces"),
    ("Arnica",            "Arnica montana",             "plantes_vivaces"),
    ("Artemisia",         "Artemisia arborescens",      "plantes_vivaces"),
    ("Asclepias",         "Asclepias tuberosa",         "plantes_vivaces"),
    ("Asphodelus",        "Asphodelus albus",           "plantes_vivaces"),
    ("Aster alpinus",     "Aster alpinus",              "plantes_vivaces"),
    ("Aster dumosus",     "Aster dumosus",              "plantes_vivaces"),
    ("Aster frikartii",   "Aster × frikartii",         "plantes_vivaces"),
    ("Aster novi-belgi",  "Aster novi-belgii",         "plantes_vivaces"),
    ("Astilbe",           "Astilbe × arendsii",        "plantes_vivaces"),
    ("Astrantia",         "Astrantia major",            "plantes_vivaces"),
    ("Athyrium niponicum","Athyrium niponicum",         "plantes_vivaces"),
    ("Aubrieta",          "Aubrieta deltoidea",         "plantes_vivaces"),
    ("Aurinia",           "Aurinia saxatilis",          "plantes_vivaces"),
    ("Baptisia",          "Baptisia australis",         "plantes_vivaces"),
    ("Bergenia",          "Bergenia cordifolia",        "plantes_vivaces"),
    ("Bletilla",          "Bletilla striata",           "plantes_vivaces"),
    ("Brunnera",          "Brunnera macrophylla",       "plantes_vivaces"),
    ("Calamintha",        "Calamintha nepeta",          "plantes_vivaces"),
    ("Campanula carpatica","Campanula carpatica",       "plantes_vivaces"),
    ("Campanula glomerata","Campanula glomerata",       "plantes_vivaces"),
    ("Campanula lactiflora","Campanula lactiflora",     "plantes_vivaces"),
    ("Campanula persicifolia","Campanula persicifolia", "plantes_vivaces"),
    ("Campanula poscharskyana","Campanula poscharskyana","plantes_vivaces"),
    ("Canna",             "Canna indica",               "plantes_vivaces"),
    ("Carex elata",       "Carex elata",                "plantes_vivaces"),
    ("Centaurea",         "Centaurea montana",          "plantes_vivaces"),
    ("Ceratostigma",      "Ceratostigma plumbaginoides","plantes_vivaces"),
    ("Chelone",           "Chelone obliqua",            "plantes_vivaces"),
    ("Convolvulus",       "Convolvulus sabatius",       "plantes_vivaces"),
    ("Coreopsis",         "Coreopsis grandiflora",      "plantes_vivaces"),
    ("Crocosmia",         "Crocosmia × crocosmiiflora","plantes_vivaces"),
    ("Crocus",            "Crocus sativus",             "plantes_vivaces"),
    ("Delphinium",        "Delphinium elatum",          "plantes_vivaces"),
    ("Dianthus",          "Dianthus plumarius",         "plantes_vivaces"),
    ("Dianthus barbatus", "Dianthus barbatus",          "plantes_vivaces"),
    ("Dicentra",          "Dicentra spectabilis",       "plantes_vivaces"),
    ("Dodecatheon",       "Dodecatheon meadia",         "plantes_vivaces"),
    ("Doronicum",         "Doronicum orientale",        "plantes_vivaces"),
    ("Echinacea",         "Echinacea purpurea",         "plantes_vivaces"),
    ("Echinops",          "Echinops ritro",             "plantes_vivaces"),
    ("Epimedium",         "Epimedium × versicolor",    "plantes_vivaces"),
    ("Erica",             "Erica darleyensis",          "plantes_vivaces"),
    ("Erigeron",          "Erigeron speciosus",         "plantes_vivaces"),
    ("Erodium",           "Erodium guttatum",           "plantes_vivaces"),
    ("Eryngium",          "Eryngium planum",            "plantes_vivaces"),
    ("Erysimum",          "Erysimum cheiri",            "plantes_vivaces"),
    ("Euphorbia",         "Euphorbia characias",        "plantes_vivaces"),
    ("Euphorbia palustris","Euphorbia palustris",       "plantes_vivaces"),
    ("Euphorbia polychroma","Euphorbia polychroma",     "plantes_vivaces"),
    ("Ficaria",           "Ficaria verna",              "plantes_vivaces"),
    ("Filipendula",       "Filipendula vulgaris",       "plantes_vivaces"),
    ("Fragaria",          "Fragaria vesca",             "plantes_vivaces"),
    ("Gaillardia",        "Gaillardia × grandiflora",  "plantes_vivaces"),
    ("Gaura",             "Gaura lindheimeri",          "plantes_vivaces"),
    ("Geranium",          "Geranium sanguineum",        "plantes_vivaces"),
    ("Geranium cantabrigiense","Geranium cantabrigiense","plantes_vivaces"),
    ("Geranium cinereum", "Geranium cinereum",          "plantes_vivaces"),
    ("Geranium endressii","Geranium endressii",         "plantes_vivaces"),
    ("Geranium ibericum", "Geranium ibericum",          "plantes_vivaces"),
    ("Geranium macrorrhizum","Geranium macrorrhizum",  "plantes_vivaces"),
    ("Geranium phaeum",   "Geranium phaeum",            "plantes_vivaces"),
    ("Geranium pratense", "Geranium pratense",          "plantes_vivaces"),
    ("Geranium renardii", "Geranium renardii",          "plantes_vivaces"),
    ("Geranium wallichianum","Geranium wallichianum",   "plantes_vivaces"),
    ("Geranium zonale",   "Pelargonium zonale",         "plantes_vivaces"),
    ("Geum",              "Geum chiloense",             "plantes_vivaces"),
    ("Gillenia",          "Gillenia trifoliata",        "plantes_vivaces"),
    ("Glochoma",          "Glechoma hederacea",         "plantes_vivaces"),
    ("Gypsophila",        "Gypsophila paniculata",      "plantes_vivaces"),
    ("Hakonechloa macra", "Hakonechloa macra",          "plantes_vivaces"),
    ("Helenium",          "Helenium autumnale",         "plantes_vivaces"),
    ("Helianthemum",      "Helianthemum nummularium",  "plantes_vivaces"),
    ("Hemerocallis",      "Hemerocallis fulva",         "plantes_vivaces"),
    ("Heuchera",          "Heuchera micrantha",         "plantes_vivaces"),
    ("Heucherella",       "Heucherella",                "plantes_vivaces"),
    ("Hibiscus moscheutos","Hibiscus moscheutos",       "plantes_vivaces"),
    ("Hieracium",         "Hieracium aurantiacum",      "plantes_vivaces"),
    ("Hosta",             "Hosta sieboldiana",          "plantes_vivaces"),
    ("Houttuynia",        "Houttuynia cordata",         "plantes_vivaces"),
    ("Hydrangea macrophylla","Hydrangea macrophylla",   "plantes_vivaces"),
    ("Hydrangea paniculata","Hydrangea paniculata",     "plantes_vivaces"),
    ("Hypericum",         "Hypericum calycinum",        "plantes_vivaces"),
    ("Iris germanica",    "Iris germanica",             "plantes_vivaces"),
    ("Iris sibirica",     "Iris sibirica",              "plantes_vivaces"),
    ("Kniphofia",         "Kniphofia uvaria",           "plantes_vivaces"),
    ("Lamiastrum",        "Lamiastrum galeobdolon",     "plantes_vivaces"),
    ("Lamium",            "Lamium maculatum",           "plantes_vivaces"),
    ("Leucanthemum",      "Leucanthemum vulgare",       "plantes_vivaces"),
    ("Lewisia",           "Lewisia cotyledon",          "plantes_vivaces"),
    ("Liatris",           "Liatris spicata",            "plantes_vivaces"),
    ("Ligularia",         "Ligularia dentata",          "plantes_vivaces"),
    ("Limonium",          "Limonium platyphyllum",      "plantes_vivaces"),
    ("Linaria",           "Linaria vulgaris",           "plantes_vivaces"),
    ("Linum",             "Linum perenne",              "plantes_vivaces"),
    ("Liriope",           "Liriope spicata",            "plantes_vivaces"),
    ("Lithodora",         "Lithodora diffusa",          "plantes_vivaces"),
    ("Lobelia cardinalis","Lobelia cardinalis",         "plantes_vivaces"),
    ("Lobelia speciosa",  "Lobelia speciosa",           "plantes_vivaces"),
    ("Lunaria rediviva",  "Lunaria rediviva",           "plantes_vivaces"),
    ("Lupinus",           "Lupinus polyphyllus",        "plantes_vivaces"),
    ("Lychnis",           "Lychnis coronaria",          "plantes_vivaces"),
    ("Lysimachia",        "Lysimachia punctata",        "plantes_vivaces"),
    ("Lysimachia nummularia","Lysimachia nummularia",   "plantes_vivaces"),
    ("Lythrum",           "Lythrum salicaria",          "plantes_vivaces"),
    ("Macleaya",          "Macleaya microcarpa",        "plantes_vivaces"),
    ("Malva",             "Malva moschata",             "plantes_vivaces"),
    ("Mazus",             "Mazus reptans",              "plantes_vivaces"),
    ("Monarda",           "Monarda didyma",             "plantes_vivaces"),
    ("Musa",              "Musa tropicana",             "plantes_vivaces"),
    ("Myrtillier sauvage","Vaccinium myrtillus",        "plantes_vivaces"),
    ("Nepeta",            "Nepeta faassenii",           "plantes_vivaces"),
    ("Nerembergia",       "Nierembergia repens",        "plantes_vivaces"),
    ("Oenothera",         "Oenothera speciosa",         "plantes_vivaces"),
    ("Ophiopogon",        "Ophiopogon japonicus",       "plantes_vivaces"),
    ("Origanum",          "Origanum vulgare",           "plantes_vivaces"),
    ("Oxalis",            "Oxalis tetraphylla",         "plantes_vivaces"),
    ("Pachysandra",       "Pachysandra terminalis",     "plantes_vivaces"),
    ("Paeonia lactiflora","Paeonia lactiflora",         "plantes_vivaces"),
    ("Papaver orientale", "Papaver orientale",          "plantes_vivaces"),
    ("Pentas",            "Pentas lanceolata",          "plantes_vivaces"),
    ("Penstemon",         "Penstemon barbatus",         "plantes_vivaces"),
    ("Perovskia",         "Perovskia atriplicifolia",   "plantes_vivaces"),
    ("Persicaria",        "Persicaria microcephala",    "plantes_vivaces"),
    ("Phlomis",           "Phlomis fruticosa",          "plantes_vivaces"),
    ("Phlox paniculata",  "Phlox paniculata",           "plantes_vivaces"),
    ("Phlox subulata",    "Phlox subulata",             "plantes_vivaces"),
    ("Phormium",          "Phormium tenax",             "plantes_vivaces"),
    ("Physostegia",       "Physostegia virginiana",     "plantes_vivaces"),
    ("Polemonium",        "Polemonium caeruleum",       "plantes_vivaces"),
    ("Potentilla",        "Potentilla neumanniana",     "plantes_vivaces"),
    ("Primula",           "Primula vulgaris",           "plantes_vivaces"),
    ("Primula denticulata","Primula denticulata",       "plantes_vivaces"),
    ("Prunella",          "Prunella grandiflora",       "plantes_vivaces"),
    ("Pulmonaire",        "Pulmonaria saccharata",      "plantes_vivaces"),
    ("Rhodanthemum",      "Rhodanthemum hosmariense",   "plantes_vivaces"),
    ("Ricin",             "Ricinus communis",           "plantes_vivaces"),
    ("Rosa",              "Rosa",                       "plantes_vivaces"),
    ("Rosmarinus",        "Salvia rosmarinus",          "plantes_vivaces"),
    ("Rudbeckia",         "Rudbeckia fulgida",          "plantes_vivaces"),
    ("Rudbeckia hirta",   "Rudbeckia hirta",            "plantes_vivaces"),
    ("Saccharum",         "Saccharum officinarum",      "plantes_vivaces"),
    ("Sagina",            "Sagina subulata",            "plantes_vivaces"),
    ("Salvia nemorosa",   "Salvia nemorosa",            "plantes_vivaces"),
    ("Salvia greggii",    "Salvia greggii",             "plantes_vivaces"),
    ("Salvia microphylla","Salvia microphylla",         "plantes_vivaces"),
    ("Salvia guaranitica","Salvia guaranitica",         "plantes_vivaces"),
    ("Salvia chamaedryoides","Salvia chamaedryoides",   "plantes_vivaces"),
    ("Santolina",         "Santolina chamaecyparissus", "plantes_vivaces"),
    ("Saxifraga",         "Saxifraga × arendsii",      "plantes_vivaces"),
    ("Saxifraga aizoon",  "Saxifraga paniculata",       "plantes_vivaces"),
    ("Scabiosa",          "Scabiosa caucasica",         "plantes_vivaces"),
    ("Sedum kamtschaticum","Sedum kamtschaticum",       "plantes_vivaces"),
    ("Sidalcea",          "Sidalcea malviflora",        "plantes_vivaces"),
    ("Sisyrinchium",      "Sisyrinchium striatum",      "plantes_vivaces"),
    ("Solidago",          "Solidago hybride",           "plantes_vivaces"),
    ("Sparganium",        "Sparganium erectum",         "plantes_vivaces"),
    ("Stachys byzantina", "Stachys byzantina",          "plantes_vivaces"),
    ("Stachys macrantha", "Stachys macrantha",          "plantes_vivaces"),
    ("Stokesia",          "Stokesia laevis",            "plantes_vivaces"),
    ("Tanacetum",         "Tanacetum coccineum",        "plantes_vivaces"),
    ("Tellima",           "Tellima grandiflora",        "plantes_vivaces"),
    ("Teucrium",          "Teucrium chamaedrys",        "plantes_vivaces"),
    ("Thalia",            "Thalia dealbata",            "plantes_vivaces"),
    ("Thalictrum",        "Thalictrum aquilegifolium",  "plantes_vivaces"),
    ("Tiarella",          "Tiarella cordifolia",        "plantes_vivaces"),
    ("Tradescantia vivace","Tradescantia andersoniana", "plantes_vivaces"),
    ("Tricyrtis",         "Tricyrtis hirta",            "plantes_vivaces"),
    ("Trollius",          "Trollius europaeus",         "plantes_vivaces"),
    ("Tubaghia",          "Tulbaghia violacea",         "plantes_vivaces"),
    ("Verbascum",         "Verbascum phoeniceum",       "plantes_vivaces"),
    ("Verbena",           "Verbena hastata",            "plantes_vivaces"),
    ("Verbena rigida",    "Verbena rigida",             "plantes_vivaces"),
    ("Veronica",          "Veronica spicata",           "plantes_vivaces"),
    ("Veronicastrum",     "Veronicastrum virginicum",   "plantes_vivaces"),
    ("Vinca major",       "Vinca major",                "plantes_vivaces"),
    ("Vinca minor",       "Vinca minor",                "plantes_vivaces"),
    ("Viola",             "Viola odorata",              "plantes_vivaces"),
    ("Viola sororia",     "Viola sororia",              "plantes_vivaces"),
    ("Waldsteinia",       "Waldsteinia ternata",        "plantes_vivaces"),
    ("Zauschneria",       "Zauschneria californica",    "plantes_vivaces"),
    ("Zinnia vivace",     "Zinnia peruviana",           "plantes_vivaces"),

    # ══════════════════════════════════════════════════════════════════
    # VIVACES & ARBUSTES MANQUANTS
    # ══════════════════════════════════════════════════════════════════
    ("Acanthocalycium",   "Echinopsis",                 "plantes_grasses"),
    ("Aucuba",            "Aucuba japonica",            "plantes_vivaces"),
    ("Cistus",            "Cistus purpureus",           "plantes_vivaces"),
    ("Clinopodium",       "Clinopodium alpinum",        "plantes_vivaces"),
    ("Clématite",         "Clematis vitalba",           "plantes_vivaces"),
    ("Convallaria",       "Convallaria majalis",        "plantes_vivaces"),
    ("Convolvulus cneorum","Convolvulus cneorum",       "plantes_vivaces"),
    ("Coronilla",         "Coronilla valentina",        "plantes_vivaces"),
    ("Corydalis vivace",  "Corydalis lutea",            "plantes_vivaces"),
    ("Cotula",            "Cotula hispida",             "plantes_vivaces"),
    ("Dystaenia",         "Dystaenia takesimana",       "plantes_vivaces"),
    ("Frankenia",         "Frankenia laevis",           "plantes_vivaces"),
    ("Hesperantha",       "Hesperantha coccinea",       "plantes_vivaces"),
    ("Hyssopus",          "Hyssopus officinalis",       "plantes_aromatiques"),
    ("Iberis",            "Iberis sempervirens",        "plantes_vivaces"),
    ("Imperata",          "Imperata cylindrica",        "graminees"),
    ("Iris ensata",       "Iris ensata",                "plantes_vivaces"),
    ("Iris laevigata",    "Iris laevigata",             "plantes_aquatiques"),
    ("Iris pumila",       "Iris pumila",                "plantes_vivaces"),
    ("Jasione",           "Jasione laevis",             "plantes_vivaces"),
    ("Kalimeris",         "Kalimeris incisa",           "plantes_vivaces"),
    ("Lathyrus latifolius","Lathyrus latifolius",       "plantes_vivaces"),
    ("Lavatera",          "Lavatera maritima",          "plantes_vivaces"),
    ("Leonotis",          "Leonotis leonurus",          "plantes_vivaces"),
    ("Melica",            "Melica ciliata",             "graminees"),
    ("Mimulus",           "Mimulus guttatus",           "plantes_vivaces"),
    ("Muehlenbeckia",     "Muehlenbeckia complexa",     "plantes_vivaces"),
    ("Musella",           "Musella lasiocarpa",         "plantes_vivaces"),
    ("Myosotis vivace",   "Myosotis scorpioides",       "plantes_vivaces"),
    ("Nerine",            "Nerine bowdenii",            "plantes_vivaces"),
    ("Oxalis floribunda", "Oxalis floribunda",          "plantes_vivaces"),
    ("Paracaryum",        "Paracaryum coelestinum",     "plantes_vivaces"),
    ("Parthenocissus",    "Parthenocissus striata",     "plantes_vivaces"),
    ("Physalis franchettii","Physalis alkekengi",       "plantes_vivaces"),
    ("Platycodon",        "Platycodon grandiflorus",    "plantes_vivaces"),
    ("Plumbago",          "Plumbago capensis",          "plantes_vivaces"),
    ("Polygonatum",       "Polygonatum odoratum",       "plantes_vivaces"),
    ("Ranunculus",        "Ranunculus acris",           "plantes_vivaces"),
    ("Rheum",             "Rheum palmatum",             "plantes_vivaces"),
    ("Saponaria",         "Saponaria officinalis",      "plantes_vivaces"),
    ("Satureja",          "Satureja montana",           "plantes_aromatiques"),
    ("Schizostylis",      "Hesperantha coccinea",       "plantes_vivaces"),
    ("Scirpus",           "Isolepis cernua",            "plantes_aquatiques"),
    ("Sesleria",          "Sesleria autumnalis",        "graminees"),
    ("Silene",            "Silene dioica",              "plantes_vivaces"),
    ("Solanum rantonetti","Solanum rantonnetii",        "plantes_vivaces"),
    ("Soleirolia",        "Soleirolia soleirolii",      "plantes_vivaces"),
    ("Streptocarpus",     "Streptocarpus hybridus",     "plantes_vertes"),
    ("Tetragonolobus",    "Tetragonolobus maritimus",   "plantes_vivaces"),
    ("Tigridia",          "Tigridia pavonia",           "plantes_vivaces"),
    ("Uncinia",           "Uncinia rubra",              "graminees"),
    ("Valeriana",         "Valeriana officinalis",      "plantes_vivaces"),
    ("Yucca filamentosa", "Yucca filamentosa",          "plantes_vivaces"),
    ("Zantedeschia",      "Zantedeschia aethiopica",    "plantes_vivaces"),

    # ══════════════════════════════════════════════════════════════════
    # PLANTES GRASSES (complément)
    # ══════════════════════════════════════════════════════════════════
    ("Cotyledon",         "Cotyledon orbiculata",       "plantes_grasses"),
    ("Orostachys",        "Orostachys spinosa",         "plantes_grasses"),

    # ══════════════════════════════════════════════════════════════════
    # PLANTES VERTES (complément)
    # ══════════════════════════════════════════════════════════════════
    ("Scindapsus",        "Scindapsus pictus",          "plantes_vertes"),

    # ══════════════════════════════════════════════════════════════════
    # POTAGÈRES (complément)
    # ══════════════════════════════════════════════════════════════════
    ("Maïs",              "Zea mays",                   "potageres"),
    ("Mâche",             "Valerianella locusta",       "potageres"),
    ("Navet",             "Brassica rapa",              "potageres"),
    ("Poire de terre",    "Smallanthus sonchifolius",   "potageres"),
    ("Poirée",            "Beta vulgaris cicla",        "potageres"),
    ("Potimarron",        "Cucurbita maxima",           "potageres"),
    ("Pourpier potager",  "Portulaca oleracea sativa",  "potageres"),

    # ══════════════════════════════════════════════════════════════════
    # ARBRES & ARBUSTES
    # ══════════════════════════════════════════════════════════════════

    # Arbres fruitiers
    ("Pommier",           "Malus domestica",            "arbres_arbustes"),
    ("Poirier",           "Pyrus communis",             "arbres_arbustes"),
    ("Cerisier",          "Prunus avium",               "arbres_arbustes"),
    ("Prunier",           "Prunus domestica",           "arbres_arbustes"),
    ("Pêcher",            "Prunus persica",             "arbres_arbustes"),
    ("Abricotier",        "Prunus armeniaca",           "arbres_arbustes"),
    ("Figuier",           "Ficus carica",               "arbres_arbustes"),
    ("Olivier",           "Olea europaea",              "arbres_arbustes"),
    ("Grenadier",         "Punica granatum",            "arbres_arbustes"),
    ("Cognassier",        "Cydonia oblonga",            "arbres_arbustes"),
    ("Noisetier",         "Corylus avellana",           "arbres_arbustes"),
    ("Noyer",             "Juglans regia",              "arbres_arbustes"),
    ("Châtaignier",       "Castanea sativa",            "arbres_arbustes"),
    ("Amandier",          "Prunus dulcis",              "arbres_arbustes"),

    # Arbres d'ornement
    ("Érable du Japon",   "Acer palmatum",              "arbres_arbustes"),
    ("Érable champêtre",  "Acer campestre",             "arbres_arbustes"),
    ("Bouleau",           "Betula pendula",             "arbres_arbustes"),
    ("Cerisier du Japon", "Prunus serrulata",           "arbres_arbustes"),
    ("Ginkgo",            "Ginkgo biloba",              "arbres_arbustes"),
    ("Magnolia",          "Magnolia grandiflora",       "arbres_arbustes"),
    ("Magnolia soulangeana","Magnolia soulangeana",     "arbres_arbustes"),
    ("Cercis",            "Cercis siliquastrum",        "arbres_arbustes"),
    ("Amélanchier",       "Amelanchier lamarckii",      "arbres_arbustes"),
    ("Liquidambar",       "Liquidambar styraciflua",    "arbres_arbustes"),
    ("Catalpa",           "Catalpa bignonioides",       "arbres_arbustes"),
    ("Paulownia",         "Paulownia tomentosa",        "arbres_arbustes"),
    ("Robinier",          "Robinia pseudoacacia",       "arbres_arbustes"),
    ("Tilleul",           "Tilia cordata",              "arbres_arbustes"),
    ("Charme",            "Carpinus betulus",           "arbres_arbustes"),
    ("Aulne",             "Alnus glutinosa",            "arbres_arbustes"),
    ("Saule pleureur",    "Salix babylonica",           "arbres_arbustes"),
    ("Saule marsault",    "Salix caprea",               "arbres_arbustes"),
    ("Chêne pédonculé",   "Quercus robur",              "arbres_arbustes"),
    ("Hêtre",             "Fagus sylvatica",            "arbres_arbustes"),
    ("Sorbier",           "Sorbus aucuparia",           "arbres_arbustes"),
    ("Aubépine",          "Crataegus monogyna",         "arbres_arbustes"),
    ("Prunellier",        "Prunus spinosa",             "arbres_arbustes"),

    # Conifères
    ("If",                "Taxus baccata",              "arbres_arbustes"),
    ("Thuya",             "Thuja occidentalis",         "arbres_arbustes"),
    ("Genévrier",         "Juniperus communis",         "arbres_arbustes"),
    ("Genévrier horizontal","Juniperus horizontalis",   "arbres_arbustes"),
    ("Pin sylvestre",     "Pinus sylvestris",           "arbres_arbustes"),
    ("Pin noir",          "Pinus nigra",                "arbres_arbustes"),
    ("Épicéa",            "Picea abies",                "arbres_arbustes"),
    ("Sapin de Nordmann", "Abies nordmanniana",         "arbres_arbustes"),
    ("Cèdre",             "Cedrus atlantica",           "arbres_arbustes"),
    ("Mélèze",            "Larix decidua",              "arbres_arbustes"),
    ("Chamaecyparis",     "Chamaecyparis lawsoniana",   "arbres_arbustes"),

    # Grands arbustes de haie / jardin
    ("Lilas",             "Syringa vulgaris",           "arbres_arbustes"),
    ("Forsythia",         "Forsythia × intermedia",     "arbres_arbustes"),
    ("Viorne boule de neige","Viburnum opulus",         "arbres_arbustes"),
    ("Viorne tin",        "Viburnum tinus",             "arbres_arbustes"),
    ("Sureau noir",       "Sambucus nigra",             "arbres_arbustes"),
    ("Cornouiller",       "Cornus alba",                "arbres_arbustes"),
    ("Cornouiller sanguin","Cornus sanguinea",          "arbres_arbustes"),
    ("Troène",            "Ligustrum ovalifolium",      "arbres_arbustes"),
    ("Buis",              "Buxus sempervirens",         "arbres_arbustes"),
    ("Photinia",          "Photinia × fraseri",         "arbres_arbustes"),
    ("Pyracantha",        "Pyracantha coccinea",        "arbres_arbustes"),
    ("Cotoneaster",       "Cotoneaster horizontalis",   "arbres_arbustes"),
    ("Berberis",          "Berberis thunbergii",        "arbres_arbustes"),
    ("Philadelphus",      "Philadelphus coronarius",    "arbres_arbustes"),
    ("Deutzia",           "Deutzia scabra",             "arbres_arbustes"),
    ("Kolkwitzia",        "Kolkwitzia amabilis",        "arbres_arbustes"),
    ("Bambou",            "Phyllostachys aurea",        "arbres_arbustes"),
    ("Bambou fargesia",   "Fargesia murielae",          "arbres_arbustes"),
    ("Mahonia",           "Mahonia aquifolium",         "arbres_arbustes"),
    ("Eleagnus",          "Elaeagnus × ebbingei",       "arbres_arbustes"),
    ("Escallonia",        "Escallonia rubra",           "arbres_arbustes"),
    ("Pittosporum",       "Pittosporum tobira",         "arbres_arbustes"),

    # ══════════════════════════════════════════════════════════════════
    # PLANTES SAUVAGES
    # ══════════════════════════════════════════════════════════════════

    # Comestibles / médicinales
    ("Ortie",             "Urtica dioica",              "plantes_sauvages"),
    ("Pissenlit",         "Taraxacum officinale",       "plantes_sauvages"),
    ("Plantain",          "Plantago major",             "plantes_sauvages"),
    ("Consoude",          "Symphytum officinale",       "plantes_sauvages"),
    ("Millepertuis",      "Hypericum perforatum",       "plantes_sauvages"),
    ("Valériane sauvage", "Valeriana officinalis",      "plantes_sauvages"),
    ("Grande camomille",  "Tanacetum parthenium",       "plantes_sauvages"),
    ("Achillée millefeuille","Achillea millefolium",    "plantes_sauvages"),
    ("Mauve sylvestre",   "Malva sylvestris",           "plantes_sauvages"),
    ("Sureau noir sauvage","Sambucus nigra",            "plantes_sauvages"),
    ("Fraise des bois",   "Fragaria vesca",             "plantes_sauvages"),
    ("Ronce",             "Rubus fruticosus",           "plantes_sauvages"),
    ("Mûrier sauvage",    "Morus nigra",                "plantes_sauvages"),

    # Fleurs sauvages des champs
    ("Coquelicot",        "Papaver rhoeas",             "plantes_sauvages"),
    ("Bleuet",            "Centaurea cyanus",           "plantes_sauvages"),
    ("Carotte sauvage",   "Daucus carota",              "plantes_sauvages"),
    ("Chardon",           "Cirsium vulgare",            "plantes_sauvages"),
    ("Chicorée sauvage",  "Cichorium intybus",          "plantes_sauvages"),
    ("Coucou",            "Primula veris",              "plantes_sauvages"),
    ("Pensée sauvage",    "Viola tricolor",             "plantes_sauvages"),
    ("Renoncule",         "Ranunculus acris",           "plantes_sauvages"),
    ("Lotier",            "Lotus corniculatus",         "plantes_sauvages"),
    ("Trèfle blanc",      "Trifolium repens",           "plantes_sauvages"),
    ("Trèfle des prés",   "Trifolium pratense",         "plantes_sauvages"),
    ("Oxalide",           "Oxalis acetosella",          "plantes_sauvages"),
    ("Lierre terrestre",  "Glechoma hederacea",         "plantes_sauvages"),
    ("Herbe à Robert",    "Geranium robertianum",       "plantes_sauvages"),
    ("Silène enflé",      "Silene vulgaris",            "plantes_sauvages"),
    ("Scabieuse des prés","Knautia arvensis",           "plantes_sauvages"),
    ("Gaillet",           "Galium verum",               "plantes_sauvages"),
    ("Lychnis fleur de coucou","Silene flos-cuculi",    "plantes_sauvages"),
    ("Grande ortie",      "Urtica dioica",              "plantes_sauvages"),
    ("Epilobe",           "Epilobium angustifolium",    "plantes_sauvages"),
    ("Salicaire",         "Lythrum salicaria",          "plantes_sauvages"),

    # Haies / lisières
    ("Églantier",         "Rosa canina",                "plantes_sauvages"),
    ("Prunellier sauvage","Prunus spinosa",             "plantes_sauvages"),
    ("Aubépine sauvage",  "Crataegus laevigata",        "plantes_sauvages"),
    ("Lierre",            "Hedera helix",               "plantes_sauvages"),
    ("Clématite sauvage", "Clematis vitalba",           "plantes_sauvages"),
    ("Chèvrefeuille",     "Lonicera periclymenum",      "plantes_sauvages"),
    ("Bryone",            "Bryonia dioica",             "plantes_sauvages"),
    ("Arum",              "Arum maculatum",             "plantes_sauvages"),

    # Sous-bois / forêt
    ("Muguet",            "Convallaria majalis",        "plantes_sauvages"),
    ("Jacinthe des bois", "Hyacinthoides non-scripta",  "plantes_sauvages"),
    ("Anémone des bois",  "Anemone nemorosa",           "plantes_sauvages"),
    ("Ficaire",           "Ficaria verna",              "plantes_sauvages"),
    ("Ail des ours",      "Allium ursinum",             "plantes_sauvages"),
    ("Fougère aigle",     "Pteridium aquilinum",        "plantes_sauvages"),
    ("Mousse",            "Mnium hornum",               "plantes_sauvages"),
    ("Myrtille sauvage",  "Vaccinium myrtillus",        "plantes_sauvages"),
    ("Digitale sauvage",  "Digitalis purpurea",         "plantes_sauvages"),
    ("Sceau de Salomon",  "Polygonatum multiflorum",    "plantes_sauvages"),
    ("Oxalis des bois",   "Oxalis acetosella",          "plantes_sauvages"),

    # Plantains (très importantes, médicinales et mellifères)
    ("Plantain lancéolé", "Plantago lanceolata",        "plantes_sauvages"),
    ("Plantain moyen",    "Plantago media",             "plantes_sauvages"),
    ("Plantain maritime", "Plantago maritima",          "plantes_sauvages"),

    # Orties et proches (essentielles pour la biodiversité)
    ("Petite ortie",      "Urtica urens",               "plantes_sauvages"),
    ("Ortie blanche",     "Lamium album",               "plantes_sauvages"),
    ("Ortie jaune",       "Lamium galeobdolon",         "plantes_sauvages"),
    ("Ortie rouge",       "Lamium purpureum",           "plantes_sauvages"),

    # Médicinales & comestibles majeures manquantes
    ("Bardane",           "Arctium lappa",              "plantes_sauvages"),
    ("Chardon Marie",     "Silybum marianum",           "plantes_sauvages"),
    ("Grande chélidoine", "Chelidonium majus",          "plantes_sauvages"),
    ("Aigremoine",        "Agrimonia eupatoria",        "plantes_sauvages"),
    ("Benoîte",           "Geum urbanum",               "plantes_sauvages"),
    ("Brunelle",          "Prunella vulgaris",          "plantes_sauvages"),
    ("Fumeterre",         "Fumaria officinalis",        "plantes_sauvages"),
    ("Tussilage",         "Tussilago farfara",          "plantes_sauvages"),
    ("Onagre",            "Oenothera biennis",          "plantes_sauvages"),
    ("Reine des prés",    "Filipendula ulmaria",        "plantes_sauvages"),
    ("Solidage",          "Solidago virgaurea",         "plantes_sauvages"),
    ("Vipérine",          "Echium vulgare",             "plantes_sauvages"),
    ("Petite centaurée",  "Centaurium erythraea",       "plantes_sauvages"),
    ("Euphraise",         "Euphrasia officinalis",      "plantes_sauvages"),
    ("Armoise",           "Artemisia vulgaris",         "plantes_sauvages"),
    ("Absinthe",          "Artemisia absinthium",       "plantes_sauvages"),
    ("Succise des prés",  "Succisa pratensis",          "plantes_sauvages"),
    ("Pulmonaire officinale",        "Pulmonaria officinalis",     "plantes_sauvages"),
    ("Centaurée jacée",   "Centaurea jacea",            "plantes_sauvages"),

    # Plantes des champs et prairies manquantes
    ("Marguerite",        "Leucanthemum vulgare",       "plantes_sauvages"),
    ("Stellaire",         "Stellaria media",            "plantes_sauvages"),
    ("Mouron rouge",      "Anagallis arvensis",         "plantes_sauvages"),
    ("Bourse à pasteur",  "Capsella bursa-pastoris",    "plantes_sauvages"),
    ("Liseron des haies", "Calystegia sepium",          "plantes_sauvages"),
    ("Rumex",             "Rumex obtusifolius",         "plantes_sauvages"),
    ("Sauge des prés",    "Salvia pratensis",           "plantes_sauvages"),
    ("Prêle des champs",  "Equisetum arvense",          "plantes_sauvages"),
    ("Véronique petit chêne","Veronica chamaedrys",     "plantes_sauvages"),
    ("Nielle des blés",   "Agrostemma githago",         "plantes_sauvages"),
    ("Ravenelle",         "Raphanus raphanistrum",      "plantes_sauvages"),
    ("Potentille rampante","Potentilla reptans",        "plantes_sauvages"),
    ("Potentille tormentille","Potentilla erecta",      "plantes_sauvages"),
    ("Laiteron",          "Sonchus oleraceus",          "plantes_sauvages"),
    ("Chénopode blanc",   "Chenopodium album",          "plantes_sauvages"),
    ("Persicaire",        "Persicaria maculosa",        "plantes_sauvages"),

    # Zones humides et bords d'eau
    ("Lysimaque des bois","Lysimachia nemorum",         "plantes_sauvages"),
    ("Lycope d'Europe",   "Lycopus europaeus",          "plantes_sauvages"),
    ("Menthe des champs", "Mentha arvensis",            "plantes_sauvages"),
    ("Cardamine des prés","Cardamine pratensis",        "plantes_sauvages"),
    ("Caltha des marais", "Caltha palustris",           "plantes_sauvages"),
    ("Jonc épars",        "Juncus effusus",             "plantes_sauvages"),

    # Forêt et sous-bois manquants
    ("Violette des bois", "Viola reichenbachiana",      "plantes_sauvages"),
    ("Primevère elatior", "Primula elatior",            "plantes_sauvages"),
    ("Mercuriale",        "Mercurialis perennis",       "plantes_sauvages"),
    ("Buis sauvage",      "Buxus sempervirens",         "plantes_sauvages"),
    ("Noisette",          "Corylus avellana",           "plantes_sauvages"),
    ("Groseille sauvage", "Ribes uva-crispa",           "plantes_sauvages"),
    ("Cornouille",        "Cornus mas",                 "plantes_sauvages"),
    ("Bourdaine",         "Frangula alnus",             "plantes_sauvages"),
    ("Troène sauvage",    "Ligustrum vulgare",          "plantes_sauvages"),
    ("Chèvrefeuille des bois","Lonicera periclymenum",  "plantes_sauvages"),
    ("Sorbier des oiseleurs","Sorbus aucuparia",        "plantes_sauvages"),

    # Adventices & plantes colonisatrices importantes
    ("Chiendent",         "Elymus repens",              "plantes_sauvages"),
    ("Chiendent pied de poule","Cynodon dactylon",      "plantes_sauvages"),
    ("Renouée du Japon",  "Reynoutria japonica",        "plantes_sauvages"),
    ("Liseron des champs","Convolvulus arvensis",       "plantes_sauvages"),
    ("Mouron des oiseaux","Stellaria media",            "plantes_sauvages"),
    ("Séneçon commun",    "Senecio vulgaris",           "plantes_sauvages"),
    ("Véronique des champs","Veronica arvensis",        "plantes_sauvages"),
    ("Pâturin",           "Poa annua",                  "plantes_sauvages"),
    ("Ray-grass",         "Lolium perenne",             "plantes_sauvages"),

    # ══════════════════════════════════════════════════════════════════
    ("Rosier buisson",          "Rosa floribunda",             "rosiers"),
    ("Rosier hybride de thé",   "Rosa × hybrida",              "rosiers"),
    ("Rosier ancien",           "Rosa gallica",                "rosiers"),
    ("Rosier de Damas",         "Rosa damascena",              "rosiers"),
    ("Rosier centfeuilles",     "Rosa centifolia",             "rosiers"),
    ("Rosier alba",             "Rosa alba",                   "rosiers"),
    ("Rosier rugosa",           "Rosa rugosa",                 "rosiers"),
    ("Rosier banksiae",         "Rosa banksiae",               "rosiers"),
    ("Rosier anglais",          "Rosa David Austin",           "rosiers"),
    ("Rosier miniature",        "Rosa minima",                 "rosiers"),
    ("Rosier grimpant",         "Rosa 'New Dawn'",             "rosiers"),
    ("Rosier couvre-sol",       "Rosa 'Bonica'",               "rosiers"),
    ("Rosier Iceberg",          "Rosa 'Iceberg'",              "rosiers"),
    ("Rosier Pierre de Ronsard","Rosa 'Eden'",                 "rosiers"),
    ("Rosier The Fairy",        "Rosa 'The Fairy'",            "rosiers"),
    ("Rosier moschata",         "Rosa moschata",               "rosiers"),
    ("Rosier moyesii",          "Rosa moyesii",                "rosiers"),
    ("Rosier nitida",           "Rosa nitida",                 "rosiers"),
    ("Rosier pimpinellifolia",  "Rosa pimpinellifolia",        "rosiers"),
    ("Rosier sericea",          "Rosa sericea",                "rosiers"),

    # ══════════════════════════════════════════════════════════════════
    # PLANTES D'AQUARIUM
    # ══════════════════════════════════════════════════════════════════
    ("Anubias barteri",         "Anubias barteri",             "plantes_aquarium"),
    ("Anubias nana",            "Anubias barteri nana",        "plantes_aquarium"),
    ("Cryptocoryne wendtii",    "Cryptocoryne wendtii",        "plantes_aquarium"),
    ("Cryptocoryne beckettii",  "Cryptocoryne beckettii",      "plantes_aquarium"),
    ("Cryptocoryne parva",      "Cryptocoryne parva",          "plantes_aquarium"),
    ("Echinodorus bleheri",     "Echinodorus bleheri",         "plantes_aquarium"),
    ("Vallisneria spiralis",    "Vallisneria spiralis",        "plantes_aquarium"),
    ("Vallisneria americana",   "Vallisneria americana",       "plantes_aquarium"),
    ("Ludwigia repens",         "Ludwigia repens",             "plantes_aquarium"),
    ("Ludwigia palustris",      "Ludwigia palustris",          "plantes_aquarium"),
    ("Rotala rotundifolia",     "Rotala rotundifolia",         "plantes_aquarium"),
    ("Hygrophila polysperma",   "Hygrophila polysperma",       "plantes_aquarium"),
    ("Microsorum pteropus",     "Microsorum pteropus",         "plantes_aquarium"),
    ("Eleocharis acicularis",   "Eleocharis acicularis",       "plantes_aquarium"),
    ("Cabomba caroliniana",     "Cabomba caroliniana",         "plantes_aquarium"),
    ("Ceratophyllum demersum",  "Ceratophyllum demersum",      "plantes_aquarium"),
    ("Java moss",               "Taxiphyllum barbieri",        "plantes_aquarium"),
    ("Bacopa caroliniana",      "Bacopa caroliniana",          "plantes_aquarium"),
    ("Hemianthus callitrichoides","Hemianthus callitrichoides","plantes_aquarium"),
    ("Staurogyne repens",       "Staurogyne repens",           "plantes_aquarium"),
    ("Pogostemon helferi",      "Pogostemon helferi",          "plantes_aquarium"),
    ("Limnophila sessiliflora", "Limnophila sessiliflora",     "plantes_aquarium"),
    ("Riccia fluitans",         "Riccia fluitans",             "plantes_aquarium"),
    ("Vesicularia dubyana",     "Vesicularia dubyana",         "plantes_aquarium"),
    ("Bolbitis heudelotii",     "Bolbitis heudelotii",         "plantes_aquarium"),

    # ══════════════════════════════════════════════════════════════════
    # PLANTES CARNIVORES
    # ══════════════════════════════════════════════════════════════════
    ("Dionaea",                 "Dionaea muscipula",           "plantes_carnivores"),
    ("Sarracenia",              "Sarracenia purpurea",         "plantes_carnivores"),
    ("Drosera rotundifolia",    "Drosera rotundifolia",        "plantes_carnivores"),
    ("Drosera capensis",        "Drosera capensis",            "plantes_carnivores"),
    ("Nepenthes",               "Nepenthes alata",             "plantes_carnivores"),
    ("Pinguicula",              "Pinguicula grandiflora",      "plantes_carnivores"),
    ("Utricularia",             "Utricularia vulgaris",        "plantes_carnivores"),
    ("Cephalotus",              "Cephalotus follicularis",     "plantes_carnivores"),

    # ══════════════════════════════════════════════════════════════════
    # PLANTES GRIMPANTES
    # ══════════════════════════════════════════════════════════════════
    ("Glycine",                 "Wisteria sinensis",           "plantes_grimpantes"),
    ("Glycine japonaise",       "Wisteria floribunda",         "plantes_grimpantes"),
    ("Clématite montana",       "Clematis montana",            "plantes_grimpantes"),
    ("Clématite armandii",      "Clematis armandii",           "plantes_grimpantes"),
    ("Clématite hybride",       "Clematis × hybrida",          "plantes_grimpantes"),
    ("Jasmin officinal",        "Jasminum officinale",         "plantes_grimpantes"),
    ("Jasmin d'hiver",          "Jasminum nudiflorum",         "plantes_grimpantes"),
    ("Passiflore",              "Passiflora caerulea",         "plantes_grimpantes"),
    ("Cobaea",                  "Cobaea scandens",             "plantes_grimpantes"),
    ("Ipomée",                  "Ipomoea tricolor",            "plantes_grimpantes"),
    ("Eccremocarpus",           "Eccremocarpus scaber",        "plantes_grimpantes"),
    ("Campsis",                 "Campsis radicans",            "plantes_grimpantes"),
    ("Humulus",                 "Humulus lupulus",             "plantes_grimpantes"),
    ("Hydrangea grimpant",      "Hydrangea anomala petiolaris","plantes_grimpantes"),
    ("Akebia",                  "Akebia quinata",              "plantes_grimpantes"),
    ("Schisandra",              "Schisandra chinensis",        "plantes_grimpantes"),
    ("Actinidia kolomikta",     "Actinidia kolomikta",         "plantes_grimpantes"),
    ("Parthenocissus quinquefolia","Parthenocissus quinquefolia","plantes_grimpantes"),
    ("Lonicera grimpant",       "Lonicera japonica",           "plantes_grimpantes"),
    ("Fallopia",                "Fallopia baldschuanica",      "plantes_grimpantes"),
    ("Solanum jasminoïdes",     "Solanum laxum",               "plantes_grimpantes"),

    # ══════════════════════════════════════════════════════════════════
    # BULBES À FLEURS
    # ══════════════════════════════════════════════════════════════════
    ("Tulipe",                  "Tulipa gesneriana",           "plantes_vivaces"),
    ("Narcisse",                "Narcissus pseudonarcissus",   "plantes_vivaces"),
    ("Jacinthe",                "Hyacinthus orientalis",       "plantes_vivaces"),
    ("Muscari",                 "Muscari armeniacum",          "plantes_vivaces"),
    ("Fritillaire impériale",   "Fritillaria imperialis",      "plantes_vivaces"),
    ("Fritillaire pintade",     "Fritillaria meleagris",       "plantes_vivaces"),
    ("Glaïeul",                 "Gladiolus communis",          "plantes_vivaces"),
    ("Freesia",                 "Freesia refracta",            "plantes_vivaces"),
    ("Ornithogalum",            "Ornithogalum umbellatum",     "plantes_vivaces"),
    ("Camassia",                "Camassia leichtlinii",        "plantes_vivaces"),
    ("Eucomis",                 "Eucomis comosa",              "plantes_vivaces"),
    ("Nectaroscordum",          "Nectaroscordum siculum",      "plantes_vivaces"),
    ("Galanthus",               "Galanthus nivalis",           "plantes_vivaces"),
    ("Allium giganteum",        "Allium giganteum",            "plantes_vivaces"),
    ("Scilla",                  "Scilla siberica",             "plantes_vivaces"),
    ("Chionodoxa",              "Chionodoxa luciliae",         "plantes_vivaces"),
    ("Leucojum",                "Leucojum vernum",             "plantes_vivaces"),

    # ══════════════════════════════════════════════════════════════════
    # ORCHIDÉES
    # ══════════════════════════════════════════════════════════════════
    ("Phalaenopsis",            "Phalaenopsis amabilis",       "plantes_vertes"),
    ("Cymbidium",               "Cymbidium hybridum",          "plantes_vertes"),
    ("Dendrobium",              "Dendrobium nobile",           "plantes_vertes"),
    ("Cattleya",                "Cattleya labiata",            "plantes_vertes"),
    ("Oncidium",                "Oncidium flexuosum",          "plantes_vertes"),
    ("Zygopetalum",             "Zygopetalum mackaii",         "plantes_vertes"),
    ("Paphiopedilum",           "Paphiopedilum insigne",       "plantes_vertes"),

    # ══════════════════════════════════════════════════════════════════
    # PLANTES VIVACES MANQUANTES
    # ══════════════════════════════════════════════════════════════════
    ("Actaea",                  "Actaea simplex",              "plantes_vivaces"),
    ("Amsonia",                 "Amsonia tabernaemontana",     "plantes_vivaces"),
    ("Brugmansia",              "Brugmansia arborea",          "plantes_vivaces"),
    ("Caryopteris",             "Caryopteris × clandonensis",  "plantes_vivaces"),
    ("Cerinthe",                "Cerinthe major",              "plantes_vivaces"),
    ("Cuphea",                  "Cuphea hyssopifolia",         "plantes_vivaces"),
    ("Dierama",                 "Dierama pulcherrimum",        "plantes_vivaces"),
    ("Echium",                  "Echium vulgare",              "plantes_vivaces"),
    ("Globularia",              "Globularia punctata",         "plantes_vivaces"),
    ("Hedychium",               "Hedychium gardnerianum",      "plantes_vivaces"),
    ("Heliopsis",               "Heliopsis helianthoides",     "plantes_vivaces"),
    ("Hesperis",                "Hesperis matronalis",         "plantes_vivaces"),
    ("Inula",                   "Inula magnifica",             "plantes_vivaces"),
    ("Kirengeshoma",            "Kirengeshoma palmata",        "plantes_vivaces"),
    ("Lantana",                 "Lantana camara",              "plantes_vivaces"),
    ("Libertia",                "Libertia grandiflora",        "plantes_vivaces"),
    ("Lobelia tupa",            "Lobelia tupa",                "plantes_vivaces"),
    ("Lycoris",                 "Lycoris radiata",             "plantes_vivaces"),
    ("Meconopsis",              "Meconopsis betonicifolia",    "plantes_vivaces"),
    ("Omphalodes",              "Omphalodes verna",            "plantes_vivaces"),
    ("Phygelius",               "Phygelius capensis",          "plantes_vivaces"),
    ("Podophyllum",             "Podophyllum peltatum",        "plantes_vivaces"),
    ("Polygala",                "Polygala chamaebuxus",        "plantes_vivaces"),
    ("Pulsatilla",              "Pulsatilla vulgaris",         "plantes_vivaces"),
    ("Rhodiola",                "Rhodiola rosea",              "plantes_vivaces"),
    ("Rodgersia",               "Rodgersia podophylla",        "plantes_vivaces"),
    ("Sanguisorba",             "Sanguisorba officinalis",     "plantes_vivaces"),
    ("Selinum",                 "Selinum wallichianum",        "plantes_vivaces"),
    ("Smilacina",               "Maianthemum racemosum",       "plantes_vivaces"),
    ("Strobilanthes",           "Strobilanthes atropurpureus", "plantes_vivaces"),
    ("Veratrum",                "Veratrum nigrum",             "plantes_vivaces"),

    # ══════════════════════════════════════════════════════════════════
    # ARBRES & ARBUSTES MANQUANTS
    # ══════════════════════════════════════════════════════════════════
    ("Buddleia",                "Buddleja davidii",            "arbres_arbustes"),
    ("Callicarpa",              "Callicarpa bodinieri",        "arbres_arbustes"),
    ("Calluna",                 "Calluna vulgaris",            "arbres_arbustes"),
    ("Choisya",                 "Choisya ternata",             "arbres_arbustes"),
    ("Corylopsis",              "Corylopsis spicata",          "arbres_arbustes"),
    ("Cryptomeria",             "Cryptomeria japonica",        "arbres_arbustes"),
    ("Cytisus",                 "Cytisus scoparius",           "arbres_arbustes"),
    ("Daboecia",                "Daboecia cantabrica",         "arbres_arbustes"),
    ("Diervilla",               "Diervilla lonicera",          "arbres_arbustes"),
    ("Exochorda",               "Exochorda macrantha",         "arbres_arbustes"),
    ("Fothergilla",             "Fothergilla major",           "arbres_arbustes"),
    ("Frêne",                   "Fraxinus excelsior",          "arbres_arbustes"),
    ("Garrya",                  "Garrya elliptica",            "arbres_arbustes"),
    ("Genêt",                   "Genista lydia",               "arbres_arbustes"),
    ("Hamamelis",               "Hamamelis × intermedia",      "arbres_arbustes"),
    ("Hippophae",               "Hippophae rhamnoides",        "arbres_arbustes"),
    ("Kerria",                  "Kerria japonica",             "arbres_arbustes"),
    ("Koelreuteria",            "Koelreuteria paniculata",     "arbres_arbustes"),
    ("Lagerstroemia",           "Lagerstroemia indica",        "arbres_arbustes"),
    ("Liriodendron",            "Liriodendron tulipifera",     "arbres_arbustes"),
    ("Metasequoia",             "Metasequoia glyptostroboides","arbres_arbustes"),
    ("Parrotia",                "Parrotia persica",            "arbres_arbustes"),
    ("Pieris",                  "Pieris japonica",             "arbres_arbustes"),
    ("Platane",                 "Platanus × acerifolia",       "arbres_arbustes"),
    ("Potentilla arbuste",      "Potentilla fruticosa",        "arbres_arbustes"),
    ("Rhododendron",            "Rhododendron hybridum",       "arbres_arbustes"),
    ("Sorbaria",                "Sorbaria sorbifolia",         "arbres_arbustes"),
    ("Spiraea",                 "Spiraea japonica",            "arbres_arbustes"),
    ("Symphoricarpos",          "Symphoricarpos albus",        "arbres_arbustes"),
    ("Taxodium",                "Taxodium distichum",          "arbres_arbustes"),
    ("Ulmus",                   "Ulmus minor",                 "arbres_arbustes"),
    ("Weigela",                 "Weigela florida",             "arbres_arbustes"),
    ("Zelkova",                 "Zelkova serrata",             "arbres_arbustes"),
    ("Caroubier",               "Ceratonia siliqua",           "arbres_arbustes"),
    ("Pistachier",              "Pistacia lentiscus",          "arbres_arbustes"),
    ("Pin parasol",             "Pinus pinea",                 "arbres_arbustes"),
    ("Cyprès de Provence",      "Cupressus sempervirens",      "arbres_arbustes"),
    ("Palmier dattier",         "Phoenix dactylifera",         "arbres_arbustes"),
    ("Chêne vert",              "Quercus ilex",                "arbres_arbustes"),
    ("Micocoulier",             "Celtis australis",            "arbres_arbustes"),
    ("Arbousier",               "Arbutus unedo",               "arbres_arbustes"),
    ("Genêt d'Espagne",         "Spartium junceum",            "arbres_arbustes"),
    ("Acer negundo",            "Acer negundo",                "arbres_arbustes"),
    ("Acer platanoides",        "Acer platanoides",            "arbres_arbustes"),
    ("Frêne pleureur",          "Fraxinus excelsior pendula",  "arbres_arbustes"),
    ("Mûrier blanc",            "Morus alba",                  "arbres_arbustes"),
    ("Salix purpurea",          "Salix purpurea",              "arbres_arbustes"),

    # ══════════════════════════════════════════════════════════════════
    # ANNUELLES COMPLÉMENTAIRES
    # ══════════════════════════════════════════════════════════════════
    ("Arctotis",                "Arctotis acaulis",            "plantes_annuelles"),
    ("Bassia",                  "Bassia scoparia",             "plantes_annuelles"),
    ("Bidens",                  "Bidens ferulifolia",          "plantes_annuelles"),
    ("Bracteantha",             "Xerochrysum bracteatum",      "plantes_annuelles"),
    ("Callistephus",            "Callistephus chinensis",      "plantes_annuelles"),
    ("Dichondra",               "Dichondra argentea",          "plantes_annuelles"),
    ("Dimorphotheca",           "Dimorphotheca pluvialis",     "plantes_annuelles"),
    ("Gomphrena",               "Gomphrena globosa",           "plantes_annuelles"),
    ("Helichrysum annuel",      "Helichrysum bracteatum",      "plantes_annuelles"),
    ("Lavatera annuelle",       "Lavatera trimestris",         "plantes_annuelles"),
    ("Limonium annuel",         "Limonium sinuatum",           "plantes_annuelles"),
    ("Lisianthus",              "Eustoma grandiflorum",        "plantes_annuelles"),
    ("Malope",                  "Malope trifida",              "plantes_annuelles"),
    ("Moluccella",              "Moluccella laevis",           "plantes_annuelles"),
    ("Nemophila",               "Nemophila menziesii",         "plantes_annuelles"),
    ("Nolana",                  "Nolana paradoxa",             "plantes_annuelles"),
    ("Portulaca grande fleur",  "Portulaca grandiflora",       "plantes_annuelles"),
    ("Reseda",                  "Reseda odorata",              "plantes_annuelles"),
    ("Salpiglossis",            "Salpiglossis sinuata",        "plantes_annuelles"),
    ("Schizanthus",             "Schizanthus pinnatus",        "plantes_annuelles"),
    ("Sutera",                  "Sutera cordata",              "plantes_annuelles"),
    ("Tithonia",                "Tithonia rotundifolia",       "plantes_annuelles"),
    ("Torenia",                 "Torenia fournieri",           "plantes_annuelles"),
    ("Viscaria",                "Silene coeli-rosa",           "plantes_annuelles"),

    # ══════════════════════════════════════════════════════════════════
    # AROMATIQUES & MÉDICINALES COMPLÉMENTAIRES
    # ══════════════════════════════════════════════════════════════════
    ("Angélique",               "Angelica archangelica",       "plantes_aromatiques"),
    ("Carvi",                   "Carum carvi",                 "plantes_aromatiques"),
    ("Cerfeuil",                "Anthriscus cerefolium",       "plantes_aromatiques"),
    ("Cumin",                   "Cuminum cyminum",             "plantes_aromatiques"),
    ("Glycyrrhiza",             "Glycyrrhiza glabra",          "plantes_aromatiques"),
    ("Mélilot",                 "Melilotus officinalis",       "plantes_aromatiques"),
    ("Menthe poléium",          "Mentha pulegium",             "plantes_aromatiques"),
    ("Myrte",                   "Myrtus communis",             "plantes_aromatiques"),
    ("Nigelle de Damas",        "Nigella sativa",              "plantes_aromatiques"),
    ("Oseille",                 "Rumex acetosa",               "plantes_aromatiques"),
    ("Pimprenelle",             "Sanguisorba minor",           "plantes_aromatiques"),
    ("Ruta",                    "Ruta graveolens",             "plantes_aromatiques"),
    ("Sarriette d'été",         "Satureja hortensis",          "plantes_aromatiques"),
    ("Shiso",                   "Perilla frutescens",          "plantes_aromatiques"),
    ("Stevia",                  "Stevia rebaudiana",           "plantes_aromatiques"),

    # ══════════════════════════════════════════════════════════════════
    # POTAGÈRES COMPLÉMENTAIRES
    # ══════════════════════════════════════════════════════════════════
    ("Artichaut de Jérusalem",  "Helianthus tuberosus",        "potageres"),
    ("Céleri branche",          "Apium graveolens dulce",      "potageres"),
    ("Chou-fleur",              "Brassica oleracea botrytis",  "potageres"),
    ("Chou de Bruxelles",       "Brassica oleracea gemmifera", "potageres"),
    ("Chou kale",               "Brassica oleracea sabellica", "potageres"),
    ("Chou-rave",               "Brassica oleracea gongylodes","potageres"),
    ("Fenouil bulbe",           "Foeniculum vulgare dulce",    "potageres"),
    ("Fève",                    "Vicia faba",                  "potageres"),
    ("Haricot grimpant",        "Phaseolus coccineus",         "potageres"),
    ("Pak choi",                "Brassica rapa chinensis",     "potageres"),
    ("Panais",                  "Pastinaca sativa",            "potageres"),
    ("Pois",                    "Pisum sativum",               "potageres"),
    ("Pomme de terre",          "Solanum tuberosum",           "potageres"),
    ("Rhubarbe",                "Rheum × hybridum",            "potageres"),
    ("Scorsonère",              "Scorzonera hispanica",        "potageres"),
    ("Soja",                    "Glycine max",                 "potageres"),

    # ══════════════════════════════════════════════════════════════════
    # PLANTES VERTES COMPLÉMENTAIRES
    # ══════════════════════════════════════════════════════════════════
    ("Anthurium",               "Anthurium andraeanum",        "plantes_vertes"),
    ("Begonia rex",             "Begonia rex",                 "plantes_vertes"),
    ("Begonia maculata",        "Begonia maculata",            "plantes_vertes"),
    ("Beaucarnea",              "Beaucarnea recurvata",        "plantes_vertes"),
    ("Caladium",                "Caladium bicolor",            "plantes_vertes"),
    ("Ctenanthe",               "Ctenanthe setosa",            "plantes_vertes"),
    ("Cycas",                   "Cycas revoluta",              "plantes_vertes"),
    ("Cyperus",                 "Cyperus alternifolius",       "plantes_vertes"),
    ("Fatsia",                  "Fatsia japonica",             "plantes_vertes"),
    ("Guzmania",                "Guzmania lingulata",          "plantes_vertes"),
    ("Hoya carnosa",            "Hoya carnosa",                "plantes_vertes"),
    ("Hoya kerrii",             "Hoya kerrii",                 "plantes_vertes"),
    ("Iresine",                 "Iresine herbstii",            "plantes_vertes"),
    ("Maranta",                 "Maranta leuconeura",          "plantes_vertes"),
    ("Medinilla",               "Medinilla magnifica",         "plantes_vertes"),
    ("Neoregelia",              "Neoregelia carolinae",        "plantes_vertes"),
    ("Pachira",                 "Pachira aquatica",            "plantes_vertes"),
    ("Philodendron gloriosum",  "Philodendron gloriosum",      "plantes_vertes"),
    ("Philodendron micans",     "Philodendron micans",         "plantes_vertes"),
    ("Rhipsalis baccifera",     "Rhipsalis baccifera",         "plantes_vertes"),
    ("Senecio rowleyanus",      "Senecio rowleyanus",          "plantes_vertes"),
    ("Tillandsia",              "Tillandsia usneoides",        "plantes_vertes"),
    ("Tillandsia ionantha",     "Tillandsia ionantha",         "plantes_vertes"),
    ("Vriesea",                 "Vriesea splendens",           "plantes_vertes"),
    ("Xanthosoma",              "Xanthosoma sagittifolium",    "plantes_vertes"),

    # ══════════════════════════════════════════════════════════════════
    # PLANTES GRASSES COMPLÉMENTAIRES
    # ══════════════════════════════════════════════════════════════════
    ("Aeonium",                 "Aeonium arboreum",            "plantes_grasses"),
    ("Astrophytum",             "Astrophytum myriostigma",     "plantes_grasses"),
    ("Cereus",                  "Cereus peruvianus",           "plantes_grasses"),
    ("Crassula perforata",      "Crassula perforata",          "plantes_grasses"),
    ("Dudleya",                 "Dudleya brittonii",           "plantes_grasses"),
    ("Echinopsis",              "Echinopsis eyriesii",         "plantes_grasses"),
    ("Euphorbia milii",         "Euphorbia milii",             "plantes_grasses"),
    ("Euphorbia obesa",         "Euphorbia obesa",             "plantes_grasses"),
    ("Ferocactus",              "Ferocactus wislizeni",        "plantes_grasses"),
    ("Graptopetalum",           "Graptopetalum paraguayense",  "plantes_grasses"),
    ("Gymnocalycium",           "Gymnocalycium mihanovichii",  "plantes_grasses"),
    ("Jovibarba",               "Jovibarba heuffelii",         "plantes_grasses"),
    ("Lithops",                 "Lithops lesliei",             "plantes_grasses"),
    ("Mammillaria",             "Mammillaria hahniana",        "plantes_grasses"),
    ("Pachyphytum",             "Pachyphytum oviferum",        "plantes_grasses"),
    ("Parodia",                 "Parodia magnifica",           "plantes_grasses"),
    ("Portulacaria",            "Portulacaria afra",           "plantes_grasses"),
    ("Rebutia",                 "Rebutia minuscula",           "plantes_grasses"),
    ("Schlumbergera",           "Schlumbergera truncata",      "plantes_grasses"),
    ("Stapelia",                "Stapelia grandiflora",        "plantes_grasses"),

    # ══════════════════════════════════════════════════════════════════
    # GRAMINÉES COMPLÉMENTAIRES
    # ══════════════════════════════════════════════════════════════════
    ("Ammophila",               "Ammophila arenaria",          "graminees"),
    ("Andropogon",              "Andropogon gerardii",         "graminees"),
    ("Arundo",                  "Arundo donax",                "graminees"),
    ("Bambou noir",             "Phyllostachys nigra",         "graminees"),
    ("Chasmanthium",            "Chasmanthium latifolium",     "graminees"),
    ("Holcus",                  "Holcus mollis",               "graminees"),
    ("Hordeum jubatum",         "Hordeum jubatum",             "graminees"),
    ("Leymus",                  "Leymus arenarius",            "graminees"),
    ("Nassella",                "Nassella tenuissima",         "graminees"),
    ("Pleioblastus",            "Pleioblastus auricomus",      "graminees"),
    ("Schizachyrium",           "Schizachyrium scoparium",     "graminees"),
    ("Spodiopogon",             "Spodiopogon sibiricus",       "graminees"),

    # ══════════════════════════════════════════════════════════════════
    # FOUGÈRES COMPLÉMENTAIRES
    # ══════════════════════════════════════════════════════════════════
    ("Blechnum",                "Blechnum spicant",            "fougeres"),
    ("Cyrtomium",               "Cyrtomium falcatum",          "fougeres"),
    ("Davallia",                "Davallia canariensis",        "fougeres"),
    ("Gymnocarpium",            "Gymnocarpium dryopteris",     "fougeres"),
    ("Onoclea",                 "Onoclea sensibilis",          "fougeres"),
    ("Platycerium",             "Platycerium bifurcatum",      "fougeres"),
    ("Selaginella",             "Selaginella uncinata",        "fougeres"),
    ("Woodsia",                 "Woodsia ilvensis",            "fougeres"),
    ("Woodwardia",              "Woodwardia radicans",         "fougeres"),

    # ══════════════════════════════════════════════════════════════════
    # AQUATIQUES COMPLÉMENTAIRES
    # ══════════════════════════════════════════════════════════════════
    ("Aponogeton",              "Aponogeton distachyos",       "plantes_aquatiques"),
    ("Azolla",                  "Azolla filiculoides",         "plantes_aquatiques"),
    ("Glyceria",                "Glyceria maxima",             "plantes_aquatiques"),
    ("Hottonia",                "Hottonia palustris",          "plantes_aquatiques"),
    ("Hydrocharis",             "Hydrocharis morsus-ranae",    "plantes_aquatiques"),
    ("Lemna",                   "Lemna minor",                 "plantes_aquatiques"),
    ("Lotus sacré",             "Nelumbo nucifera",            "plantes_aquatiques"),
    ("Menyanthes",              "Menyanthes trifoliata",       "plantes_aquatiques"),
    ("Myriophyllum aqua",       "Myriophyllum spicatum",       "plantes_aquatiques"),
    ("Nuphar",                  "Nuphar lutea",                "plantes_aquatiques"),
    ("Orontium",                "Orontium aquaticum",          "plantes_aquatiques"),
    ("Stratiotes",              "Stratiotes aloides",          "plantes_aquatiques"),
    ("Zizania",                 "Zizania aquatica",            "plantes_aquatiques"),

    # ══════════════════════════════════════════════════════════════════
    # COMPLÉMENT VIVACES — vers les 1000
    # ══════════════════════════════════════════════════════════════════
    ("Acinos",            "Clinopodium acinos",          "plantes_vivaces"),
    ("Agrimonia",         "Agrimonia eupatoria",         "plantes_vivaces"),
    ("Alyssum",           "Alyssum montanum",            "plantes_vivaces"),
    ("Amorpha",           "Amorpha fruticosa",           "plantes_vivaces"),
    ("Buphthalmum",       "Buphthalmum salicifolium",    "plantes_vivaces"),
    ("Calceolaria vivace","Calceolaria integrifolia",    "plantes_vivaces"),
    ("Catananche",        "Catananche caerulea",         "plantes_vivaces"),
    ("Caulophyllum",      "Caulophyllum thalictroides",  "plantes_vivaces"),
    ("Chrysogonum",       "Chrysogonum virginianum",     "plantes_vivaces"),
    ("Cimicifuga",        "Actaea racemosa",             "plantes_vivaces"),
    ("Clematis integrifolia","Clematis integrifolia",    "plantes_vivaces"),
    ("Cynara cardunculus","Cynara cardunculus",          "plantes_vivaces"),
    ("Darmera",           "Darmera peltata",             "plantes_vivaces"),
    ("Datisca",           "Datisca cannabina",           "plantes_vivaces"),
    ("Dianthus deltoides","Dianthus deltoides",          "plantes_vivaces"),
    ("Dictamnus",         "Dictamnus albus",             "plantes_vivaces"),
    ("Digitalis ferruginea","Digitalis ferruginea",      "plantes_vivaces"),
    ("Doronicum caucasicum","Doronicum caucasicum",      "plantes_vivaces"),
    ("Erigeron annuus",   "Erigeron annuus",             "plantes_vivaces"),
    ("Eryngium alpinum",  "Eryngium alpinum",            "plantes_vivaces"),
    ("Eupatorium",        "Eupatorium cannabinum",       "plantes_vivaces"),
    ("Ferula",            "Ferula communis",             "plantes_vivaces"),
    ("Filipendula hexapetala","Filipendula vulgaris",    "plantes_vivaces"),
    ("Francoa",           "Francoa sonchifolia",         "plantes_vivaces"),
    ("Geranium maderense","Geranium maderense",          "plantes_vivaces"),
    ("Geranium nodosum",  "Geranium nodosum",            "plantes_vivaces"),
    ("Geranium × oxonianum","Geranium × oxonianum",      "plantes_vivaces"),
    ("Geranium sylvaticum","Geranium sylvaticum",        "plantes_vivaces"),
    ("Gunnera",           "Gunnera manicata",            "plantes_vivaces"),
    ("Hacquetia",         "Hacquetia epipactis",         "plantes_vivaces"),
    ("Helianthus decapetalus","Helianthus decapetalus",  "plantes_vivaces"),
    ("Helleborus foetidus","Helleborus foetidus",        "plantes_vivaces"),
    ("Helleborus orientalis","Helleborus orientalis",    "plantes_vivaces"),
    ("Houttuynia cordata","Houttuynia cordata",          "plantes_vivaces"),
    ("Inula hookeri",     "Inula hookeri",               "plantes_vivaces"),
    ("Ipheion uniflorum", "Ipheion uniflorum",           "plantes_vivaces"),
    ("Iris foetidissima", "Iris foetidissima",           "plantes_vivaces"),
    ("Knautia macedonica","Knautia macedonica",          "plantes_vivaces"),
    ("Ligularia stenocephala","Ligularia stenocephala",  "plantes_vivaces"),
    ("Lysimachia clethroides","Lysimachia clethroides",  "plantes_vivaces"),
    ("Maianthemum",       "Maianthemum bifolium",        "plantes_vivaces"),
    ("Melianthus",        "Melianthus major",            "plantes_vivaces"),
    ("Mimulus cardinalis","Mimulus cardinalis",          "plantes_vivaces"),
    ("Origanum laevigatum","Origanum laevigatum",        "plantes_vivaces"),
    ("Persicaria amplexicaulis","Persicaria amplexicaulis","plantes_vivaces"),
    ("Petasites japonicus","Petasites japonicus",        "plantes_vivaces"),
    ("Phlomis russeliana","Phlomis russeliana",          "plantes_vivaces"),
    ("Physostegia vivace","Physostegia virginiana",      "plantes_vivaces"),
    ("Potentilla nepalensis","Potentilla nepalensis",    "plantes_vivaces"),

]
# ─────────────────────────────────────────────────────────────────────────────

def main():
    total    = len(PLANTES)
    crees    = 0
    caches   = 0
    erreurs  = 0

    print(f"\n{'='*60}")
    print(f"  SLOTHIA — Peuplement DB — {total} plantes à traiter")
    print(f"{'='*60}\n")

    for i, (nom_commun, nom_latin, categorie) in enumerate(PLANTES, 1):
        print(f"[{i:03}/{total}] {nom_commun} ({nom_latin})...", end=" ", flush=True)
        try:
            fiche, was_cached = get_or_create_fiche(nom_commun, nom_latin)

            # Forcer la catégorie quelle que soit detect_category
            if fiche.get("categorie") != categorie:
                fiche["categorie"] = categorie
                save_to_db(fiche)

            if was_cached:
                print("✅ (déjà en cache)")
                caches += 1
            else:
                print(f"🌿 créée → {categorie}")
                crees += 1
                # Pause entre créations pour ménager les API
                time.sleep(2)

        except Exception as e:
            print(f"❌ erreur : {e}")
            erreurs += 1
            time.sleep(5)  # Pause plus longue en cas d'erreur

    print(f"\n{'='*60}")
    print(f"  Terminé ! Créées : {crees} | Déjà en cache : {caches} | Erreurs : {erreurs}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
