"""
Validation automatique des exercices générés.

Deux couches, correspondant aux deux colonnes de la table `exercices` :
  1. validation_ia   → vérifications automatiques (structure, calcul, doublons)
  2. validation_humaine → jamais mise à True ici : un enseignant doit toujours
     valider manuellement, sauf pour les exercices générés par template maths
     où le calcul est garanti par construction (voir pipeline.py).

IMPORTANT : contrairement au script du document initial, on n'utilise JAMAIS
`eval()` sur du texte généré (risque d'injection de code). SymPy fournit
`sympify()` avec une liste blanche de fonctions autorisées.
"""

from __future__ import annotations
import re
import math
from fractions import Fraction
from sympy import symbols, Eq, solve, sympify
from sympy.core.sympify import SympifyError
from num2words import num2words


class ErreurValidation(Exception):
    pass


def valider_structure(exercice: dict) -> list[str]:
    """Vérifie que les champs obligatoires sont présents et non vides.
    Retourne la liste des erreurs (vide = OK)."""
    erreurs = []
    champs_obligatoires = ["niveau", "matiere", "theme", "enonce", "corrige"]
    for champ in champs_obligatoires:
        valeur = exercice.get(champ)
        if not valeur or not str(valeur).strip():
            erreurs.append(f"Champ obligatoire manquant ou vide : '{champ}'")

    enonce = exercice.get("enonce", "")
    if len(enonce) < 15:
        erreurs.append("Énoncé trop court (< 15 caractères) — probable réponse tronquée")
    if len(enonce) > 2000:
        erreurs.append("Énoncé anormalement long (> 2000 caractères) — probable dérive du LLM")

    return erreurs


def valider_equation_lineaire(a: int, b: int, c: int, solution_annoncee) -> bool:
    """Vérifie qu'une équation ax + b = c a bien `solution_annoncee` comme
    solution, en utilisant SymPy de façon sûre (pas d'eval sur texte libre).
    """
    x = symbols("x")
    try:
        equation = Eq(a * x + b, c)
        solutions = solve(equation, x)
        if not solutions:
            return False
        return solutions[0] == sympify(solution_annoncee)
    except (SympifyError, TypeError, IndexError):
        return False


def valider_expression_numerique(expression_texte: str, valeur_attendue) -> bool:
    """Valide un résultat numérique (ex: une aire, un produit) en parsant
    l'expression avec sympify plutôt qu'eval. sympify() n'exécute pas de
    code arbitraire — il construit un arbre d'expression mathématique.
    """
    # On ne garde que les caractères mathématiques légitimes avant de parser,
    # en défense supplémentaire contre toute tentative d'injection.
    if not re.fullmatch(r"[0-9\s\+\-\*/\.\(\)]+", str(expression_texte)):
        return False
    try:
        resultat = sympify(expression_texte)
        return resultat == sympify(valeur_attendue)
    except (SympifyError, TypeError):
        return False


def valider_texte_nombre(n: int, texte_annonce: str) -> bool:
    """Recalcule indépendamment l'écriture en lettres d'un nombre entier
    et compare (insensible à la casse et à la ponctuation finale)."""
    attendu = num2words(n, lang="fr").strip().lower()
    obtenu = texte_annonce.strip().lower().rstrip(".")
    return attendu == obtenu


def valider_fraction_somme(num1: int, den1: int, num2: int, den2: int,
                             num_resultat: int, den_resultat: int) -> bool:
    """Vérifie une addition de fractions via Fraction (arithmétique exacte,
    pas de flottants) — recalcule indépendamment du texte du corrigé."""
    try:
        somme_attendue = Fraction(num1, den1) + Fraction(num2, den2)
        somme_annoncee = Fraction(num_resultat, den_resultat)
        return somme_attendue == somme_annoncee
    except (ZeroDivisionError, ValueError):
        return False


def valider_proportionnalite(a: int, b: int, c: int, x_solution) -> bool:
    """Vérifie a/b = c/x, c'est-à-dire x = (c × b) / a."""
    try:
        x_calcule = sympify(f"({c}*{b})/{a}")
        return x_calcule == sympify(x_solution)
    except (SympifyError, TypeError, ZeroDivisionError):
        return False


def valider_puissance(base: int, exposant: int, resultat_annonce) -> bool:
    try:
        return (base ** exposant) == int(resultat_annonce)
    except (TypeError, ValueError):
        return False


def valider_pgcd(a: int, b: int, resultat_annonce) -> bool:
    try:
        return math.gcd(a, b) == int(resultat_annonce)
    except (TypeError, ValueError):
        return False


def valider_pythagore(cote1: int, cote2: int, hypotenuse_annoncee) -> bool:
    """Vérifie cote1² + cote2² = hypoténuse² sans jamais passer par une
    racine carrée flottante (qui introduirait une imprécision) — on compare
    les carrés entiers directement."""
    try:
        return cote1 ** 2 + cote2 ** 2 == int(hypotenuse_annoncee) ** 2
    except (TypeError, ValueError):
        return False


def valider_equation_produit_nul(a: int, b: int, corrige_texte: str) -> bool:
    """Vérifie que le texte du corrigé mentionne bien les deux racines a et b
    de (x-a)(x-b)=0, recalculées via SymPy plutôt que supposées correctes."""
    x = symbols("x")
    try:
        solutions = set(solve(Eq((x - a) * (x - b), 0), x))
        solutions_attendues = {sympify(a), sympify(b)}
        if solutions != solutions_attendues:
            return False
        # Les deux valeurs doivent apparaître littéralement dans le corrigé
        return str(a) in corrige_texte and str(b) in corrige_texte
    except (SympifyError, TypeError):
        return False


def valider_moyenne(valeurs: list, moyenne_attendue) -> bool:
    try:
        moyenne_calculee = round(sum(valeurs) / len(valeurs), 2)
        return abs(moyenne_calculee - float(moyenne_attendue)) < 0.005
    except (TypeError, ZeroDivisionError):
        return False


def valider_somme_decimale(a: str, b: str, resultat_annonce: str) -> bool:
    """Vérifie une addition de décimaux avec Decimal plutôt que float, pour
    éviter les faux rejets dus à l'imprécision binaire (12.4 + 12.3 vaut
    24.700000000000003 en float natif, mais exactement 24.7 en Decimal)."""
    from decimal import Decimal, InvalidOperation
    try:
        return Decimal(a) + Decimal(b) == Decimal(resultat_annonce)
    except InvalidOperation:
        return False


def valider_fonction_affine(a: int, b: int, x0: int, resultat_annonce) -> bool:
    try:
        return (a * x0 + b) == int(resultat_annonce)
    except (TypeError, ValueError):
        return False


# Dispatcher générique : chaque template maths attache un dict `_verif` avec
# une clé "type" ; on route vers le bon validateur plutôt que de multiplier
# les `if "_xxx" in exercice` comme dans la première version de ce fichier.
_VALIDATEURS_PAR_TYPE = {
    "equation_lineaire": lambda v, ex: valider_equation_lineaire(v["a"], v["b"], v["c"], v["solution"]),
    "expression_numerique": lambda v, ex: valider_expression_numerique(v["expression"], v["attendu"]),
    "texte_nombre": lambda v, ex: valider_texte_nombre(v["n"], ex["corrige"]),
    "fraction_somme": lambda v, ex: valider_fraction_somme(
        v["num1"], v["den1"], v["num2"], v["den2"], v["num_resultat"], v["den_resultat"]),
    "somme_decimale": lambda v, ex: valider_somme_decimale(v["a"], v["b"], v["resultat"]),
    "proportionnalite": lambda v, ex: valider_proportionnalite(v["a"], v["b"], v["c"], v["x_solution"]),
    "puissance": lambda v, ex: valider_puissance(v["base"], v["exposant"], v["resultat"]),
    "pgcd": lambda v, ex: valider_pgcd(v["a"], v["b"], v["resultat"]),
    "pythagore": lambda v, ex: valider_pythagore(v["cote1"], v["cote2"], v["hypotenuse"]),
    "equation_produit_nul": lambda v, ex: valider_equation_produit_nul(v["a"], v["b"], ex["corrige"]),
    "moyenne": lambda v, ex: valider_moyenne(v["valeurs"], v["moyenne_attendue"]),
    "fonction_affine": lambda v, ex: valider_fonction_affine(v["a"], v["b"], v["x0"], v["resultat"]),
}


def valider_contenu_suspect(exercice: dict) -> list[str]:
    """Détecte les signaux de dérive d'un LLM qu'aucune vérification de
    calcul ne peut attraper (puisqu'il n'y a pas de calcul à revérifier en
    Français/SVT/Histoire-Géo). Ne prouve jamais que le contenu est correct
    — seulement qu'il ne présente pas de défaut structurel évident. La
    justesse factuelle reste entièrement à la charge du relecteur humain.
    """
    erreurs = []
    texte_complet = f"{exercice.get('enonce', '')} {exercice.get('corrige', '')}"

    # Résidu de balisage markdown ou JSON qui aurait fui malgré la consigne
    if re.search(r"```|^\s*[\{\[]|\"sous_theme\"|\"enonce\"", texte_complet):
        erreurs.append("Résidu de balisage JSON/Markdown détecté dans le texte — le LLM n'a probablement "
                        "pas respecté le format demandé")

    # Répétition dégénérée (le LLM boucle sur le même segment) — signe classique
    # de dérive de génération, indépendant du sujet traité
    mots = texte_complet.split()
    if len(mots) >= 12:
        bigrammes = [tuple(mots[i:i + 3]) for i in range(len(mots) - 2)]
        if len(bigrammes) > 0 and len(set(bigrammes)) / len(bigrammes) < 0.5:
            erreurs.append("Répétition anormale détectée — possible dérive de génération du LLM")

    # URL ou balise HTML : n'a rien à faire dans un énoncé scolaire généré
    if re.search(r"https?://|<[a-z]+>", texte_complet, re.IGNORECASE):
        erreurs.append("URL ou balise HTML détectée dans le contenu généré")

    # Corrigé qui ne fait que répéter l'énoncé sans rien ajouter (LLM qui
    # "abandonne" et recopie la question au lieu d'y répondre)
    enonce_norm = exercice.get("enonce", "").strip().lower()
    corrige_norm = exercice.get("corrige", "").strip().lower()
    if enonce_norm and corrige_norm and enonce_norm == corrige_norm:
        erreurs.append("Le corrigé est identique à l'énoncé — le LLM n'a probablement pas répondu")

    return erreurs


def valider_exercice_llm_genere(exercice: dict) -> tuple[bool, list[str]]:
    """Validation d'un exercice généré par LLM (Français, SVT, Histoire-Géo).
    Contrairement à valider_exercice_math_genere, il n'y a ici AUCUNE
    vérification de justesse — seulement des contrôles structurels. Le champ
    validation_ia doit rester False après ce contrôle : passer ces tests ne
    signifie pas que le contenu est pédagogiquement ou factuellement correct.
    """
    erreurs = valider_structure(exercice)
    erreurs += valider_contenu_suspect(exercice)
    if not exercice.get("etapes"):
        erreurs.append("Aucune étape de correction fournie — corrigé probablement trop laconique")
    return (len(erreurs) == 0, erreurs)


def detecter_doublon_probable(nouvel_exercice: dict, exercices_existants: list[dict],
                                seuil_similarite: float = 0.85) -> bool:
    """Détection de doublon simple par recouvrement de mots (Jaccard).
    Utile pour les exercices générés par LLM (paraphrase). Pour les
    exercices de template maths, préférer la comparaison exacte de l'énoncé
    (voir pipeline.py) — la similarité Jaccard produit des faux positifs
    sur des phrases-modèles qui partagent volontairement leur structure.
    """
    def normaliser(texte: str) -> set[str]:
        mots = re.findall(r"\w+", texte.lower())
        return set(mots) - {"le", "la", "les", "un", "une", "de", "du", "des", "et", "à"}

    mots_nouveau = normaliser(nouvel_exercice.get("enonce", ""))
    if not mots_nouveau:
        return False

    for existant in exercices_existants:
        mots_existant = normaliser(existant.get("enonce", ""))
        if not mots_existant:
            continue
        intersection = mots_nouveau & mots_existant
        union = mots_nouveau | mots_existant
        similarite = len(intersection) / len(union) if union else 0
        if similarite >= seuil_similarite:
            return True
    return False


def valider_exercice_math_genere(exercice: dict) -> tuple[bool, list[str]]:
    """Validation complète d'un exercice de maths généré par template.
    Recalcule le résultat attendu de façon indépendante via le dispatcher
    `_VALIDATEURS_PAR_TYPE`, plutôt que de faire confiance au corrigé
    produit par le générateur. Retourne (est_valide, erreurs).
    """
    erreurs = valider_structure(exercice)

    verif = exercice.get("_verif")
    if verif is not None:
        type_verif = verif.get("type")
        validateur = _VALIDATEURS_PAR_TYPE.get(type_verif)
        if validateur is None:
            erreurs.append(f"Type de vérification inconnu : '{type_verif}' — exercice non validable automatiquement")
        else:
            try:
                if not validateur(verif, exercice):
                    erreurs.append(f"Le corrigé ne correspond pas au recalcul indépendant (type: {type_verif})")
            except (KeyError, ZeroDivisionError) as e:
                erreurs.append(f"Paramètres de vérification incomplets ou invalides : {e}")

    return (len(erreurs) == 0, erreurs)


if __name__ == "__main__":
    from generator_math import TEMPLATES, NIVEAU_PAR_DEFAUT

    print("=== Test : chaque template passe la validation indépendante ===")
    for nom, fn in TEMPLATES.items():
        ex = fn(NIVEAU_PAR_DEFAUT[nom])
        ok, erreurs = valider_exercice_math_genere(ex)
        statut = "OK" if ok else f"ÉCHEC → {erreurs}"
        print(f"{nom:32s} : {statut}")

    print("\n=== Test : corrigé volontairement corrompu (doit échouer) ===")
    from generator_math import template_equation_premier_degre
    ex_corrompu = template_equation_premier_degre()
    ex_corrompu["_verif"]["solution"] += 1  # on casse volontairement
    ok, erreurs = valider_exercice_math_genere(ex_corrompu)
    print(f"Valide : {ok}, erreurs : {erreurs}")

    print("\n=== Test : détection de doublon (LLM) ===")
    ex1 = {"enonce": "Corrige les phrases suivantes concernant l'accord du verbe avec le sujet."}
    ex2 = {"enonce": "Corrige les phrases suivantes concernant l'accord du verbe avec le sujet."}
    print(f"Doublon détecté : {detecter_doublon_probable(ex2, [ex1])}")

    print("\n=== Test : tentative d'injection dans valider_expression_numerique ===")
    resultat = valider_expression_numerique("__import__('os').system('echo hacked')", 56)
    print(f"Injection bloquée (résultat=False attendu) : {resultat}")
