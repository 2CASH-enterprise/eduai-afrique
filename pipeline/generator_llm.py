"""
Génération d'exercices via Mistral AI — pour les matières où un template
Python déterministe n'a pas de sens (Français, SVT, Histoire-Géo).

Contrairement au générateur maths, ces exercices sortent TOUJOURS avec
validation_ia=False et statut='en_validation' : un LLM peut produire une
erreur factuelle plausible (une date fausse en histoire, une règle de
grammaire mal formulée) sans qu'aucun contrôle automatique ne la détecte.
La relecture humaine n'est pas optionnelle ici — c'est le vrai goulot
d'étranglement du projet, et le pipeline le reflète honnêtement plutôt
que de le masquer.
"""

from __future__ import annotations
import os
import re
import json
import uuid
from dataclasses import dataclass

from mistralai.client import Mistral

MODELE = "mistral-small-latest"

# Coût indicatif (à vérifier sur mistral.ai/pricing — évolue régulièrement)
COUT_PAR_1K_TOKENS_USD = 0.002


SYSTEM_PROMPT = """Tu es un expert en pédagogie pour le Cameroun. Tu génères des \
exercices scolaires conformes aux programmes officiels camerounais. \
Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ou après, \
sans balises markdown. Le JSON doit avoir exactement ces clés : \
niveau, matiere, theme, sous_theme, enonce, corrige, etapes (liste), \
contexte, tags (liste de 2-4 mots-clés)."""


# Plan de génération par matière/niveau — reflète la structure de la table
# `calendrier_pedagogique` du schéma (chapitre par mois). En V1, ces thèmes
# servent à cadrer les appels au LLM plutôt que de le laisser inventer un
# thème arbitraire à chaque fois, ce qui améliore la reproductibilité et
# facilite le contrôle de couverture du programme.
THEMES_PAR_MATIERE_NIVEAU = {
    ("SVT", "6ème"): [
        "Les êtres vivants dans leur milieu",
        "La cellule, unité du vivant",
        "Alimentation et digestion",
    ],
    ("SVT", "5ème"): [
        "Respiration et occupation des milieux",
        "Reproduction chez les êtres vivants",
    ],
    ("SVT", "4ème"): [
        "Le système nerveux",
        "La transmission de la vie chez l'être humain",
    ],
    ("SVT", "3ème"): [
        "Système immunitaire et maladies infectieuses",
        "Génétique et hérédité",
    ],
    ("Histoire-Géographie", "6ème"): [
        "La Préhistoire",
        "Les grandes civilisations antiques",
        "La Terre, planète habitée",
    ],
    ("Histoire-Géographie", "5ème"): [
        "Le Cameroun précolonial",
        "Le Moyen Âge en Afrique et en Europe",
    ],
    ("Histoire-Géographie", "4ème"): [
        "La traite négrière et ses conséquences",
        "La colonisation de l'Afrique",
    ],
    ("Histoire-Géographie", "3ème"): [
        "La Première Guerre mondiale",
        "Le Cameroun sous mandat et tutelle",
        "L'indépendance et la réunification du Cameroun",
    ],
}


@dataclass
class ResultatGeneration:
    exercice: dict | None
    tokens_utilises: int
    cout_estime_usd: float
    erreur: str | None = None


def _construire_prompt_utilisateur(matiere: str, niveau: str, theme: str) -> str:
    return f"""Génère UN exercice de {matiere} pour la classe de {niveau}, \
sur le thème "{theme}".

Contraintes :
1. Conforme au programme officiel camerounais.
2. Énoncé clair, corrigé détaillé avec étapes de raisonnement.
3. Utilise si possible un contexte local (agriculture, marché, vie \
quotidienne au Cameroun) — sans le forcer si le thème ne s'y prête pas.
4. Le champ "etapes" doit contenir 2 à 4 étapes de correction, pas juste \
la réponse finale.

Réponds uniquement avec le JSON, rien d'autre."""


def _extraire_json(contenu_brut: str) -> str:
    """Certains modèles enveloppent le JSON dans des balises markdown malgré
    la consigne explicite de ne pas le faire (```json ... ```). On les retire
    avant de parser plutôt que de rejeter tout l'appel — c'est un problème
    de formatage trivial et fréquent, pas une vraie erreur de génération, et
    chaque appel rejeté à tort est un appel Mistral payé pour rien.
    """
    contenu = contenu_brut.strip()
    if contenu.startswith("```"):
        contenu = re.sub(r"^```[a-zA-Z]*\n?", "", contenu)
        contenu = re.sub(r"\n?```$", "", contenu)
    return contenu.strip()


def generer_exercice_llm(matiere: str, niveau: str, theme: str,
                          client: Mistral | None = None) -> ResultatGeneration:
    """Appelle Mistral pour générer un exercice. Isole les erreurs réseau/
    parsing pour que le pipeline puisse continuer sur le reste du lot
    même si une génération individuelle échoue.
    """
    if client is None:
        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            return ResultatGeneration(None, 0, 0.0, erreur="MISTRAL_API_KEY absente")
        client = Mistral(api_key=api_key)

    try:
        reponse = client.chat.complete(
            model=MODELE,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _construire_prompt_utilisateur(matiere, niveau, theme)},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
    except Exception as e:
        return ResultatGeneration(None, 0, 0.0, erreur=f"Erreur API Mistral : {e}")

    tokens = reponse.usage.total_tokens if reponse.usage else 0
    cout = (tokens / 1000) * COUT_PAR_1K_TOKENS_USD

    contenu_brut = _extraire_json(reponse.choices[0].message.content)
    try:
        donnees = json.loads(contenu_brut)
    except json.JSONDecodeError as e:
        return ResultatGeneration(None, tokens, cout, erreur=f"JSON invalide renvoyé par le LLM : {e}")

    exercice = {
        "id": str(uuid.uuid4()),
        "niveau": niveau,
        "matiere": matiere,
        "theme": theme,
        "sous_theme": donnees.get("sous_theme"),
        "type_exercice": "application",
        "difficulte": "moyen",
        "enonce": donnees.get("enonce", ""),
        "corrige": donnees.get("corrige", ""),
        "etapes": donnees.get("etapes", []),
        "contexte": donnees.get("contexte"),
        "tags": donnees.get("tags", []),
        "source": "mistral_ai",
    }

    return ResultatGeneration(exercice, tokens, cout, erreur=None)


def generer_lot_llm(matiere: str, niveau: str, themes: list[str],
                     client: Mistral | None = None) -> list[ResultatGeneration]:
    """Génère un exercice par thème donné. Utilisé pour produire un lot
    couvrant plusieurs sous-thèmes d'un chapitre en un seul appel de pipeline.

    Le client n'est construit qu'une seule fois ici (pas dans la boucle),
    et propagé tel quel à chaque appel — important pour l'injection d'un
    client de test, et pour éviter de recréer une connexion HTTP par thème.
    """
    if client is None and os.environ.get("MISTRAL_API_KEY"):
        client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    return [generer_exercice_llm(matiere, niveau, theme, client) for theme in themes]


def generer_lot_depuis_plan(matiere: str, niveau: str,
                              client: Mistral | None = None) -> list[ResultatGeneration]:
    """Génère un lot en s'appuyant sur THEMES_PAR_MATIERE_NIVEAU plutôt que
    sur une liste de thèmes fournie à la main — pratique pour couvrir un
    niveau entier en un seul appel de pipeline."""
    themes = THEMES_PAR_MATIERE_NIVEAU.get((matiere, niveau))
    if not themes:
        raise ValueError(f"Aucun thème défini pour {matiere} / {niveau} dans THEMES_PAR_MATIERE_NIVEAU")
    return generer_lot_llm(matiere, niveau, themes, client)


if __name__ == "__main__":
    # Sans clé API, ce test confirme juste que l'échec est propre (pas de crash).
    resultat = generer_exercice_llm("Français", "5ème", "Accords sujet-verbe")
    if resultat.erreur:
        print(f"Pas de génération réelle (attendu sans clé API) : {resultat.erreur}")
    else:
        print(json.dumps(resultat.exercice, ensure_ascii=False, indent=2))
