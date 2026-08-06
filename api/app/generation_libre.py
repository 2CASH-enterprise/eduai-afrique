"""Génération d'exercice à la demande, pour le mode libre (enseignant sans
classe réelle — indépendant ou simple pratique personnelle).

Adapté de pipeline/generator_llm.py plutôt qu'importé directement : le
pipeline est un outil de génération par lot exécuté hors-ligne (pas par le
process API en production), alors que ce module est appelé en direct,
en synchrone, à chaque requête. Les deux partagent la même logique de
prompt mais vivent dans des contextes d'exécution différents.
"""
import os
import json
import re

from fastapi import HTTPException, status
from mistralai.client import Mistral

MODELE = "mistral-small-latest"

def _system_prompt(pays: str | None) -> str:
    pays_texte = pays or "le pays de l'enseignant"
    return (
        f"Tu es un expert en pédagogie pour {pays_texte}. Tu génères des "
        f"exercices scolaires conformes aux programmes officiels de {pays_texte}. "
        "Rédige TOUJOURS en français (consignes, énoncé, corrigé) — y compris pour "
        "les exercices de langue étrangère (anglais, allemand, espagnol...), où seuls "
        "les mots ou phrases dans la langue étudiée doivent apparaître dans cette langue, "
        "jamais les consignes ni les explications. "
        "Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ou après, "
        "sans balises markdown. Le JSON doit avoir exactement ces clés : "
        "sous_theme, enonce, corrige, etapes (liste), contexte, tags (liste de 2-4 mots-clés)."
    )


LABELS_DIFFICULTE = {
    "facile": "plutôt facile, accessible, avec des étapes bien guidées",
    "moyen": "de difficulté moyenne, standard pour ce niveau",
    "difficile": "exigeant, pour des élèves à l'aise avec la matière",
}


def _construire_prompt(matiere: str, niveau: str, theme: str, pays: str | None, difficulte: str = "moyen") -> str:
    pays_texte = pays or "le pays de l'enseignant"
    return f"""Génère UN exercice de {matiere} pour la classe de {niveau}, \
sur le thème "{theme}".

Contraintes :
1. Conforme au programme officiel de {pays_texte}.
2. Niveau de difficulté souhaité : {LABELS_DIFFICULTE.get(difficulte, LABELS_DIFFICULTE['moyen'])}.
3. Énoncé clair, corrigé détaillé avec étapes de raisonnement.
4. Utilise si possible un contexte local (agriculture, marché, vie \
quotidienne en {pays_texte}) — sans le forcer si le thème ne s'y prête pas."""


def generer_exercice_a_la_demande(matiere: str, niveau: str, theme: str, passages_contexte: list[str] | None = None,
                                    pays: str | None = None, difficulte: str = "moyen") -> dict:
    """Appelle Mistral directement et retourne le JSON parsé. Lève une
    HTTPException explicite en cas d'échec — contrairement au pipeline par
    lot, ici il y a un utilisateur en attente d'une réponse immédiate, donc
    pas de sens à avaler l'erreur silencieusement.

    Le pays est désormais un paramètre explicite (corrigé le 03/08) — avant
    ça, le prompt mentionnait le Cameroun en dur, quel que soit le pays réel
    de l'enseignant, ce qui produisait du contenu incohérent (ex : un
    enseignant ivoirien recevait des exercices parlant du Cameroun)."""
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="MISTRAL_API_KEY absente sur le serveur")

    prompt = _construire_prompt(matiere, niveau, theme, pays, difficulte)
    if passages_contexte:
        prompt += (
            "\n\nExtraits de référence disponibles (programme officiel et/ou notes de cours) — "
            "à utiliser s'ils sont pertinents, sans t'y limiter :\n" + "\n---\n".join(passages_contexte)
        )

    client = Mistral(api_key=api_key)
    try:
        reponse = client.chat.complete(
            model=MODELE,
            messages=[
                {"role": "system", "content": _system_prompt(pays)},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
    except Exception as e:
        from . import erreurs
        erreurs.enregistrer_erreur("generation_ia", str(e), {
            "endpoint": "generation_libre", "matiere": matiere, "niveau": niveau, "theme": theme,
        })
        raise HTTPException(status_code=502, detail=f"Erreur lors de l'appel à l'IA : {e}")

    brut = reponse.choices[0].message.content
    try:
        donnees = json.loads(re.sub(r"^```json\s*|\s*```$", "", brut.strip()))
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Réponse de l'IA illisible — réessayez")

    return donnees
