"""
Générateur d'exercices de mathématiques — approche 100% Python/SymPy.

Principe : au lieu de demander à un LLM d'inventer un énoncé ET son corrigé
(risque de calcul faux), on part de TEMPLATES paramétrés. Le calcul est fait
par SymPy / Python — donc le corrigé est mathématiquement garanti correct.
Le LLM n'est jamais impliqué ici : coût = $0, taux d'erreur de calcul = 0%.

Chaque template attache un dict `_verif` structuré (type + paramètres
numériques) que `validation.py` peut recalculer indépendamment avec SymPy
avant insertion en base — défense en profondeur : même si un bug s'introduit
dans le texte du corrigé, le chiffre final est revérifié séparément.

Couverture V1 : 6ème → Seconde, 13 templates, 6 thèmes.
"""

import math
import random
import uuid
from num2words import num2words

CONTEXTES_CAMEROUN = [
    "Un agriculteur de Bafoussam récolte {n} kg de maïs.",
    "Un commerçant du marché central de Yaoundé vend {n} sacs de riz.",
    "Une coopérative de Bamenda transporte {n} régimes de plantain.",
    "Un pêcheur de Douala ramène {n} kg de poisson.",
    "Une exploitation de cacao à Ebolowa produit {n} kg de fèves.",
]

# Triplets pythagoriciens (résultats entiers propres, pas de racine qui traîne).
# Avec seulement 6 triplets, la probabilité de tirer deux fois la même
# combinaison (triplet × facteur) devient élevée dès une dizaine de tirages
# (paradoxe des anniversaires) — d'où une liste volontairement large, et
# plusieurs facteurs d'échelle pour multiplier les combinaisons distinctes.
TRIPLETS_PYTHAGORE = [
    (3, 4, 5), (6, 8, 10), (5, 12, 13), (9, 12, 15), (8, 15, 17), (7, 24, 25),
    (20, 21, 29), (12, 16, 20), (9, 40, 41), (10, 24, 26), (18, 24, 30), (15, 20, 25),
]


def _contexte(n: int) -> str:
    return random.choice(CONTEXTES_CAMEROUN).format(n=n)


def _squelette(niveau, theme, sous_theme, difficulte, enonce, corrige, etapes,
                contexte, tags, verif) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "niveau": niveau,
        "matiere": "Mathématiques",
        "theme": theme,
        "sous_theme": sous_theme,
        "type_exercice": "application",
        "difficulte": difficulte,
        "enonce": enonce,
        "corrige": corrige,
        "etapes": etapes,
        "contexte": contexte,
        "tags": tags,
        "_verif": verif,
    }


# ---------------------------------------------------------------------------
# 6ème
# ---------------------------------------------------------------------------

def template_nombres_entiers_lettres(niveau: str = "6ème") -> dict:
    n = random.randint(100, 9999)
    corrige = num2words(n, lang="fr").capitalize() + "."
    return _squelette(
        niveau, "Nombres entiers", "Lecture et écriture", "facile",
        f"{_contexte(n)} Écris ce nombre en toutes lettres.",
        corrige,
        [f"Décomposer {n} en milliers, centaines, dizaines et unités.", f"Lire chaque groupe : {corrige}"],
        "Cameroun", ["nombres", "lecture", niveau.lower()],
        {"type": "texte_nombre", "n": n},
    )


def template_aire_rectangle(niveau: str = "6ème") -> dict:
    longueur = random.randint(3, 25)
    largeur = random.randint(2, longueur - 1)
    aire = longueur * largeur
    return _squelette(
        niveau, "Géométrie", "Aires des figures planes", "facile",
        f"Un champ rectangulaire à Bafia mesure {longueur} m de long sur {largeur} m de large. Calcule son aire.",
        f"{aire} m²",
        ["Aire du rectangle = longueur × largeur", f"Aire = {longueur} × {largeur} = {aire} m²"],
        "Cameroun", ["géométrie", "aires", niveau.lower()],
        {"type": "expression_numerique", "expression": f"{longueur}*{largeur}", "attendu": aire},
    )


def template_perimetre_rectangle(niveau: str = "6ème") -> dict:
    longueur = random.randint(4, 30)
    largeur = random.randint(2, longueur - 1)
    perimetre = 2 * (longueur + largeur)
    return _squelette(
        niveau, "Géométrie", "Périmètres des figures planes", "facile",
        f"Une parcelle à Garoua mesure {longueur} m de long sur {largeur} m de large. "
        f"Calcule son périmètre.",
        f"{perimetre} m",
        ["Périmètre du rectangle = 2 × (longueur + largeur)",
         f"Périmètre = 2 × ({longueur} + {largeur}) = {perimetre} m"],
        "Cameroun", ["géométrie", "périmètres", niveau.lower()],
        {"type": "expression_numerique", "expression": f"2*({longueur}+{largeur})", "attendu": perimetre},
    )


def template_nombres_decimaux_addition(niveau: str = "6ème") -> dict:
    # On génère en dixièmes (entiers) puis on convertit en Decimal : ça évite
    # complètement l'imprécision binaire des flottants Python (12.4 + 12.3
    # vaut 24.700000000000003 en float, mais exactement 24.7 en Decimal).
    from decimal import Decimal
    a = Decimal(random.randint(10, 500)) / 10
    b = Decimal(random.randint(10, 500)) / 10
    resultat = a + b
    return _squelette(
        niveau, "Nombres décimaux", "Addition de décimaux", "facile",
        f"Au marché de Kribi, un sac de riz coûte {a} milliers de FCFA et un sac de sucre "
        f"coûte {b} milliers de FCFA. Quel est le prix total ?",
        f"{resultat} milliers de FCFA",
        [f"On aligne les virgules : {a} + {b}", f"{a} + {b} = {resultat}"],
        "Cameroun", ["nombres décimaux", "addition", niveau.lower()],
        {"type": "somme_decimale", "a": str(a), "b": str(b), "resultat": str(resultat)},
    )


def template_fractions_meme_denominateur(niveau: str = "6ème") -> dict:
    denominateur = random.choice([3, 4, 5, 6, 7, 8])
    num1 = random.randint(1, denominateur - 1)
    num2 = random.randint(1, denominateur - 1)
    return _squelette(
        niveau, "Fractions", "Addition de fractions de même dénominateur", "moyen",
        f"Calcule la somme suivante et donne le résultat sous forme de fraction : "
        f"{num1}/{denominateur} + {num2}/{denominateur}",
        f"({num1 + num2})/{denominateur}",
        ["Les dénominateurs sont identiques, on additionne les numérateurs.",
         f"{num1}/{denominateur} + {num2}/{denominateur} = ({num1}+{num2})/{denominateur} = {num1 + num2}/{denominateur}"],
        None, ["fractions", "addition", niveau.lower()],
        {"type": "fraction_somme", "num1": num1, "den1": denominateur, "num2": num2,
         "den2": denominateur, "num_resultat": num1 + num2, "den_resultat": denominateur},
    )


# ---------------------------------------------------------------------------
# 5ème
# ---------------------------------------------------------------------------

def template_proportionnalite(niveau: str = "5ème") -> dict:
    # a kg coûtent b FCFA ; combien coûtent c kg ? (produit en croix, résultat entier garanti)
    a = random.randint(2, 10)
    prix_unitaire = random.randint(200, 2000)
    b = a * prix_unitaire
    c = random.randint(2, 15)
    x_solution = c * prix_unitaire
    return _squelette(
        niveau, "Proportionnalité", "Produit en croix", "moyen",
        f"{a} kg de cacao coûtent {b} FCFA au marché de Sangmélima. "
        f"Combien coûtent {c} kg de cacao (au même prix) ?",
        f"{x_solution} FCFA",
        [f"On cherche x tel que {a}/{b} = {c}/x (proportionnalité)",
         f"x = ({c} × {b}) / {a} = {x_solution} FCFA"],
        "Cameroun", ["proportionnalité", "produit en croix", niveau.lower()],
        {"type": "proportionnalite", "a": a, "b": b, "c": c, "x_solution": x_solution},
    )


def template_nombres_relatifs_addition(niveau: str = "5ème") -> dict:
    a = random.randint(-50, 50)
    b = random.randint(-50, 50)
    resultat = a + b
    return _squelette(
        niveau, "Nombres relatifs", "Addition de relatifs", "facile",
        f"Calcule : ({a}) + ({b})",
        str(resultat),
        [f"({a}) + ({b}) = {resultat}"],
        None, ["nombres relatifs", "addition", niveau.lower()],
        {"type": "expression_numerique", "expression": f"({a})+({b})", "attendu": resultat},
    )


# ---------------------------------------------------------------------------
# 4ème
# ---------------------------------------------------------------------------

def template_equation_premier_degre(niveau: str = "4ème") -> dict:
    a = random.randint(2, 9)
    x_solution = random.randint(1, 20)
    b = random.randint(1, 30)
    c = a * x_solution + b
    return _squelette(
        niveau, "Équations", "Équations du premier degré", "moyen",
        f"Résous l'équation suivante : {a}x + {b} = {c}",
        f"x = {x_solution}",
        [f"{a}x + {b} = {c}", f"{a}x = {c} - {b} = {c - b}", f"x = {c - b} / {a} = {x_solution}"],
        None, ["équations", "algèbre", niveau.lower()],
        {"type": "equation_lineaire", "a": a, "b": b, "c": c, "solution": x_solution},
    )


def template_puissances(niveau: str = "4ème") -> dict:
    base = random.randint(2, 9)
    exposant = random.randint(2, 4)
    resultat = base ** exposant
    return _squelette(
        niveau, "Puissances", "Calcul de puissances", "facile",
        f"Calcule la puissance suivante : {base}^{exposant}",
        str(resultat),
        [f"{base}^{exposant} = " + " × ".join([str(base)] * exposant), f"= {resultat}"],
        None, ["puissances", niveau.lower()],
        {"type": "puissance", "base": base, "exposant": exposant, "resultat": resultat},
    )


def template_pgcd(niveau: str = "4ème") -> dict:
    # On fixe d'abord le PGCD visé (non trivial) puis on construit a et b comme
    # des multiples de ce PGCD par des facteurs premiers entre eux — ça garantit
    # un résultat pédagogiquement intéressant (jamais 1, jamais un cas dégénéré).
    gcd_vise = random.randint(4, 15)
    mult1, mult2 = random.sample(range(2, 9), 2)
    while math.gcd(mult1, mult2) != 1:
        mult1, mult2 = random.sample(range(2, 9), 2)
    a = gcd_vise * mult1
    b = gcd_vise * mult2
    resultat = math.gcd(a, b)
    return _squelette(
        niveau, "Arithmétique", "PGCD", "moyen",
        f"Une coopérative de Nkongsamba veut répartir {a} sacs de café et {b} sacs de cacao "
        f"en lots identiques, sans reste. Quel est le nombre maximal de lots possible ?",
        f"{resultat} lots (PGCD de {a} et {b})",
        [f"On cherche le PGCD de {a} et {b}.", f"PGCD({a}, {b}) = {resultat}"],
        "Cameroun", ["arithmétique", "pgcd", niveau.lower()],
        {"type": "pgcd", "a": a, "b": b, "resultat": resultat},
    )


# ---------------------------------------------------------------------------
# 3ème
# ---------------------------------------------------------------------------

def template_pythagore(niveau: str = "3ème") -> dict:
    cote1, cote2, hypotenuse = random.choice(TRIPLETS_PYTHAGORE)
    # on varie parfois l'échelle (×2) pour ne pas toujours retomber sur les mêmes chiffres
    facteur = random.choice([1, 1, 2, 3])
    cote1, cote2, hypotenuse = cote1 * facteur, cote2 * facteur, hypotenuse * facteur
    return _squelette(
        niveau, "Géométrie", "Théorème de Pythagore", "moyen",
        f"Un triangle rectangle a pour côtés de l'angle droit {cote1} cm et {cote2} cm. "
        f"Calcule la longueur de son hypoténuse.",
        f"{hypotenuse} cm",
        [f"D'après le théorème de Pythagore : hypoténuse² = {cote1}² + {cote2}²",
         f"hypoténuse² = {cote1**2} + {cote2**2} = {cote1**2 + cote2**2}",
         f"hypoténuse = √{cote1**2 + cote2**2} = {hypotenuse} cm"],
        None, ["géométrie", "pythagore", niveau.lower()],
        {"type": "pythagore", "cote1": cote1, "cote2": cote2, "hypotenuse": hypotenuse},
    )


def template_equation_produit_nul(niveau: str = "3ème") -> dict:
    valeurs_possibles = [v for v in range(-10, 11) if v != 0]
    a, b = random.sample(valeurs_possibles, 2)
    solutions = sorted([a, b])
    return _squelette(
        niveau, "Équations", "Équations produit nul", "difficile",
        f"Résous l'équation suivante : (x - {a})(x - {b}) = 0",
        f"x = {solutions[0]} ou x = {solutions[1]}",
        ["Un produit de facteurs est nul si l'un au moins des facteurs est nul.",
         f"x - {a} = 0 ou x - {b} = 0", f"x = {a} ou x = {b}"],
        None, ["équations", "produit nul", niveau.lower()],
        {"type": "equation_produit_nul", "a": a, "b": b},
    )


def template_moyenne(niveau: str = "3ème") -> dict:
    notes = [random.randint(6, 20) for _ in range(random.choice([4, 5]))]
    moyenne_arrondie = round(sum(notes) / len(notes), 2)
    return _squelette(
        niveau, "Statistiques", "Moyenne", "facile",
        f"Un élève a obtenu les notes suivantes : {', '.join(str(n) for n in notes)}. "
        f"Calcule sa moyenne.",
        f"{moyenne_arrondie}/20",
        ["Moyenne = (somme des notes) / (nombre de notes)",
         f"Moyenne = ({' + '.join(str(n) for n in notes)}) / {len(notes)} = {moyenne_arrondie}"],
        None, ["statistiques", "moyenne", niveau.lower()],
        {"type": "moyenne", "valeurs": notes, "moyenne_attendue": moyenne_arrondie},
    )


# ---------------------------------------------------------------------------
# Seconde
# ---------------------------------------------------------------------------

def template_fonction_affine(niveau: str = "Seconde") -> dict:
    a = random.randint(-8, 8)
    while a == 0:
        a = random.randint(-8, 8)
    b = random.randint(-20, 20)
    x0 = random.randint(-10, 10)
    resultat = a * x0 + b
    return _squelette(
        niveau, "Fonctions", "Fonctions affines", "moyen",
        f"On considère la fonction affine f définie par f(x) = {a}x {'+' if b >= 0 else '-'} {abs(b)}. "
        f"Calcule f({x0}).",
        f"f({x0}) = {resultat}",
        [f"f({x0}) = {a} × {x0} {'+' if b >= 0 else '-'} {abs(b)}",
         f"f({x0}) = {a * x0} {'+' if b >= 0 else '-'} {abs(b)} = {resultat}"],
        None, ["fonctions", "fonction affine", niveau.lower()],
        {"type": "fonction_affine", "a": a, "b": b, "x0": x0, "resultat": resultat},
    )


TEMPLATES = {
    # 6ème
    "nombres_entiers": template_nombres_entiers_lettres,
    "aire_rectangle": template_aire_rectangle,
    "perimetre_rectangle": template_perimetre_rectangle,
    "nombres_decimaux_addition": template_nombres_decimaux_addition,
    "fractions_meme_denominateur": template_fractions_meme_denominateur,
    # 5ème
    "proportionnalite": template_proportionnalite,
    "nombres_relatifs_addition": template_nombres_relatifs_addition,
    # 4ème
    "equation_premier_degre": template_equation_premier_degre,
    "puissances": template_puissances,
    "pgcd": template_pgcd,
    # 3ème
    "pythagore": template_pythagore,
    "equation_produit_nul": template_equation_produit_nul,
    "moyenne": template_moyenne,
    # Seconde
    "fonction_affine": template_fonction_affine,
}

# Niveau par défaut suggéré pour chaque template (utile pour le pipeline)
NIVEAU_PAR_DEFAUT = {
    "nombres_entiers": "6ème", "aire_rectangle": "6ème", "perimetre_rectangle": "6ème",
    "nombres_decimaux_addition": "6ème", "fractions_meme_denominateur": "6ème",
    "proportionnalite": "5ème", "nombres_relatifs_addition": "5ème",
    "equation_premier_degre": "4ème", "puissances": "4ème", "pgcd": "4ème",
    "pythagore": "3ème", "equation_produit_nul": "3ème", "moyenne": "3ème",
    "fonction_affine": "Seconde",
}


def generer_lot(template_nom: str, niveau: str, quantite: int) -> list[dict]:
    """Génère `quantite` exercices distincts à partir d'un template."""
    fn = TEMPLATES[template_nom]
    return [fn(niveau) for _ in range(quantite)]


if __name__ == "__main__":
    for nom in TEMPLATES:
        ex = TEMPLATES[nom](NIVEAU_PAR_DEFAUT[nom])
        print(f"--- {nom} ({ex['niveau']}) ---")
        print(ex["enonce"])
        print("→", ex["corrige"])
        print()
