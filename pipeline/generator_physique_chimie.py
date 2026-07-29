"""
Générateur d'exercices de Physique-Chimie — même principe que generator_math.py :
on choisit d'abord le résultat "propre", puis on en dérive les données de
l'énoncé, plutôt que de générer des données aléatoires et espérer une
division exacte. Ça évite complètement les résultats du type "3,333... A"
qui n'ont aucun sens dans un exercice de niveau collège/lycée.

Réutilise le même format `_verif` (type + paramètres) et le même validateur
`expression_numerique` de validation.py — ce validateur utilise sympify(),
qui traite une division entière comme une fraction exacte (Rational), donc
aucun problème de précision flottante ici (contrairement au piège rencontré
sur les décimaux en maths).
"""

import random
import uuid

CONTEXTES_TRANSPORT = [
    "Un bus effectue le trajet Douala–Yaoundé",
    "Un taxi effectue le trajet Bafoussam–Bamenda",
    "Un camion effectue le trajet Garoua–Maroua",
]

SUBSTANCES_CHIMIE = [
    ("d'eau", 18), ("de dioxyde de carbone (CO₂)", 44), ("de méthane (CH₄)", 16),
    ("de dioxygène (O₂)", 32), ("d'hydroxyde de sodium (NaOH)", 40), ("d'ammoniac (NH₃)", 17),
]


def _squelette(niveau, theme, sous_theme, difficulte, enonce, corrige, etapes,
                contexte, tags, verif) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "niveau": niveau,
        "matiere": "Physique-Chimie",
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
# 5ème — mécanique de base
# ---------------------------------------------------------------------------

def template_vitesse_moyenne(niveau: str = "5ème") -> dict:
    t = random.randint(1, 6)          # heures
    v = random.randint(40, 120)       # km/h — on choisit v d'abord
    d = v * t                          # distance dérivée (exacte)
    return _squelette(
        niveau, "Mécanique", "Vitesse moyenne", "facile",
        f"{random.choice(CONTEXTES_TRANSPORT)} de {d} km en {t} h. Calcule sa vitesse moyenne.",
        f"{v} km/h",
        ["Vitesse moyenne = distance / temps", f"v = {d} / {t} = {v} km/h"],
        "Cameroun", ["mécanique", "vitesse", niveau.lower()],
        {"type": "expression_numerique", "expression": f"{d}/{t}", "attendu": v},
    )


def template_masse_volumique(niveau: str = "5ème") -> dict:
    volume = random.randint(10, 200)    # cm³
    rho = random.randint(1, 12)          # g/cm³ — on choisit rho d'abord
    masse = rho * volume                  # dérivée (exacte)
    return _squelette(
        niveau, "Matière", "Masse volumique", "moyen",
        f"Un objet a une masse de {masse} g pour un volume de {volume} cm³. "
        f"Calcule sa masse volumique.",
        f"{rho} g/cm³",
        ["Masse volumique = masse / volume", f"ρ = {masse} / {volume} = {rho} g/cm³"],
        None, ["matière", "masse volumique", niveau.lower()],
        {"type": "expression_numerique", "expression": f"{masse}/{volume}", "attendu": rho},
    )


def template_poids(niveau: str = "5ème") -> dict:
    masse = random.randint(1, 100)   # kg
    g = 10                             # simplification usuelle du programme (g = 10 N/kg)
    poids = masse * g
    return _squelette(
        niveau, "Mécanique", "Poids et masse", "facile",
        f"Un sac de cacao a une masse de {masse} kg. Calcule son poids "
        f"(on prendra g = {g} N/kg).",
        f"{poids} N",
        ["Poids = masse × g", f"P = {masse} × {g} = {poids} N"],
        "Cameroun", ["mécanique", "poids", niveau.lower()],
        {"type": "expression_numerique", "expression": f"{masse}*{g}", "attendu": poids},
    )


# ---------------------------------------------------------------------------
# 4ème — électricité
# ---------------------------------------------------------------------------

def template_loi_ohm(niveau: str = "4ème") -> dict:
    r = random.randint(5, 100)   # ohms
    i = random.randint(1, 10)    # ampères
    u = r * i
    return _squelette(
        niveau, "Électricité", "Loi d'Ohm", "moyen",
        f"Un conducteur ohmique de résistance {r} Ω est parcouru par un courant "
        f"d'intensité {i} A. Calcule la tension à ses bornes.",
        f"{u} V",
        ["Loi d'Ohm : U = R × I", f"U = {r} × {i} = {u} V"],
        None, ["électricité", "loi d'ohm", niveau.lower()],
        {"type": "expression_numerique", "expression": f"{r}*{i}", "attendu": u},
    )


def template_puissance_electrique(niveau: str = "4ème") -> dict:
    u = random.randint(5, 220)   # volts
    i = random.randint(1, 15)    # ampères
    p = u * i
    return _squelette(
        niveau, "Électricité", "Puissance électrique", "moyen",
        f"Une lampe fonctionne sous une tension de {u} V et est traversée par un "
        f"courant de {i} A. Calcule la puissance électrique consommée.",
        f"{p} W",
        ["Puissance = U × I", f"P = {u} × {i} = {p} W"],
        None, ["électricité", "puissance", niveau.lower()],
        {"type": "expression_numerique", "expression": f"{u}*{i}", "attendu": p},
    )


def template_resistance_serie(niveau: str = "4ème") -> dict:
    r1 = random.randint(5, 100)
    r2 = random.randint(5, 100)
    r_eq = r1 + r2
    return _squelette(
        niveau, "Électricité", "Association de résistances", "moyen",
        f"Deux résistances de {r1} Ω et {r2} Ω sont montées en série. "
        f"Calcule la résistance équivalente du circuit.",
        f"{r_eq} Ω",
        ["En série, les résistances s'additionnent : Réq = R1 + R2",
         f"Réq = {r1} + {r2} = {r_eq} Ω"],
        None, ["électricité", "résistances", niveau.lower()],
        {"type": "expression_numerique", "expression": f"{r1}+{r2}", "attendu": r_eq},
    )


# ---------------------------------------------------------------------------
# 3ème — chimie des solutions
# ---------------------------------------------------------------------------

def template_concentration_massique(niveau: str = "3ème") -> dict:
    volume = random.randint(1, 10)     # L
    c = random.randint(1, 50)           # g/L — on choisit c d'abord
    masse = c * volume                    # dérivée (exacte)
    return _squelette(
        niveau, "Chimie", "Concentration massique", "moyen",
        f"On dissout {masse} g de sel dans {volume} L d'eau. "
        f"Calcule la concentration massique de la solution obtenue.",
        f"{c} g/L",
        ["Concentration massique = masse dissoute / volume de solution",
         f"c = {masse} / {volume} = {c} g/L"],
        None, ["chimie", "concentration", niveau.lower()],
        {"type": "expression_numerique", "expression": f"{masse}/{volume}", "attendu": c},
    )


# ---------------------------------------------------------------------------
# Seconde — chimie quantitative
# ---------------------------------------------------------------------------

def template_quantite_matiere(niveau: str = "Seconde") -> dict:
    nom_substance, m_molaire = random.choice(SUBSTANCES_CHIMIE)
    n = random.randint(1, 5)           # mol — on choisit n d'abord
    masse = n * m_molaire                # dérivée (exacte, car m_molaire entière)
    return _squelette(
        niveau, "Chimie", "Quantité de matière", "moyen",
        f"On dispose de {masse} g {nom_substance} (masse molaire M = {m_molaire} g/mol). "
        f"Calcule la quantité de matière correspondante.",
        f"{n} mol",
        ["Quantité de matière : n = m / M", f"n = {masse} / {m_molaire} = {n} mol"],
        None, ["chimie", "quantité de matière", niveau.lower()],
        {"type": "expression_numerique", "expression": f"{masse}/{m_molaire}", "attendu": n},
    )


def template_dilution(niveau: str = "Seconde") -> dict:
    facteur = random.randint(2, 10)
    c2 = random.randint(1, 20)          # concentration diluée (mol/L)
    c1 = c2 * facteur                    # concentration mère (dérivée, exacte)
    v1 = random.randint(1, 10)          # volume prélevé (mL)
    v2 = v1 * facteur                    # volume final (dérivé, exacte, car C1V1 = C2V2)
    return _squelette(
        niveau, "Chimie", "Dilution", "difficile",
        f"On prélève {v1} mL d'une solution mère de concentration {c1} mol/L, "
        f"puis on complète avec de l'eau distillée pour obtenir {v2} mL de solution diluée. "
        f"Calcule la concentration de la solution diluée.",
        f"{c2} mol/L",
        ["Conservation de la quantité de matière lors d'une dilution : C₁V₁ = C₂V₂",
         f"C₂ = (C₁ × V₁) / V₂ = ({c1} × {v1}) / {v2} = {c2} mol/L"],
        None, ["chimie", "dilution", niveau.lower()],
        {"type": "expression_numerique", "expression": f"({c1}*{v1})/{v2}", "attendu": c2},
    )


TEMPLATES = {
    "vitesse_moyenne": template_vitesse_moyenne,
    "masse_volumique": template_masse_volumique,
    "poids": template_poids,
    "loi_ohm": template_loi_ohm,
    "puissance_electrique": template_puissance_electrique,
    "resistance_serie": template_resistance_serie,
    "concentration_massique": template_concentration_massique,
    "quantite_matiere": template_quantite_matiere,
    "dilution": template_dilution,
}

NIVEAU_PAR_DEFAUT = {
    "vitesse_moyenne": "5ème", "masse_volumique": "5ème", "poids": "5ème",
    "loi_ohm": "4ème", "puissance_electrique": "4ème", "resistance_serie": "4ème",
    "concentration_massique": "3ème",
    "quantite_matiere": "Seconde", "dilution": "Seconde",
}


def generer_lot(template_nom: str, niveau: str, quantite: int) -> list[dict]:
    fn = TEMPLATES[template_nom]
    return [fn(niveau) for _ in range(quantite)]


if __name__ == "__main__":
    for nom in TEMPLATES:
        ex = TEMPLATES[nom](NIVEAU_PAR_DEFAUT[nom])
        print(f"--- {nom} ({ex['niveau']}) ---")
        print(ex["enonce"])
        print("→", ex["corrige"])
        print()
